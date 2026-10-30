"""Small async client for the SIMKL API (AUTH V2 device flow)."""
from __future__ import annotations

import time
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    API_BASE,
    APP_NAME,
    CDN_BASE,
    DEVICE_GRANT,
    USER_AGENT,
    VERSION,
)

TIMEOUT = ClientTimeout(total=40)


class SimklError(Exception):
    """Generic API failure."""


class SimklAuthError(SimklError):
    """The token was rejected (needs re-authentication)."""


class SimklRateLimit(SimklError):
    """HTTP 429."""


class SimklClient:
    """SIMKL client. Token handling stays inside this class."""

    def __init__(
        self,
        session: ClientSession,
        client_id: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        expires_at: float = 0,
    ) -> None:
        self._s = session
        self.client_id = client_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at

    # ------------------------------------------------------------------ http
    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, str]:
        p = {"client_id": self.client_id, "app-name": APP_NAME, "app-version": VERSION}
        if extra:
            p.update({k: str(v) for k, v in extra.items()})
        return p

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        form: dict[str, Any] | None = None,
        auth: bool = False,
    ) -> Any:
        headers = {"User-Agent": USER_AGENT}
        if auth:
            if not self.access_token:
                raise SimklAuthError("not signed in")
            headers["Authorization"] = f"Bearer {self.access_token}"
        try:
            async with self._s.request(
                method,
                url,
                params=self._params(params),
                data=form,
                headers=headers,
                timeout=TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    raise SimklAuthError("401")
                if resp.status == 429:
                    raise SimklRateLimit("429")
                try:
                    body = await resp.json(content_type=None)
                except ValueError:
                    body = None
                if resp.status >= 400:
                    err = body.get("error") if isinstance(body, dict) else None
                    raise SimklError(f"HTTP {resp.status} {err or ''}".strip())
                return body
        except ClientError as err:
            raise SimklError(str(err)) from err
        except TimeoutError as err:
            raise SimklError("timeout") from err

    # ------------------------------------------------------------ device flow
    async def start_device_flow(self) -> dict[str, Any]:
        """Begin the PIN flow. Returns user_code, verification_uri, device_code..."""
        data = await self._request(
            "POST",
            f"{API_BASE}/oauth2/device",
            form={"client_id": self.client_id, "scope": "media:read"},
        )
        if not isinstance(data, dict) or "device_code" not in data:
            raise SimklError("no device code returned")
        return data

    async def poll_device_flow(self, device_code: str) -> dict[str, Any] | None:
        """Return the token payload once approved, None while pending."""
        try:
            data = await self._request(
                "POST",
                f"{API_BASE}/oauth2/token",
                form={
                    "grant_type": DEVICE_GRANT,
                    "client_id": self.client_id,
                    "device_code": device_code,
                },
            )
        except SimklAuthError:
            return None
        except SimklError as err:
            # authorization_pending / slow_down come back as 4xx with an error key
            msg = str(err)
            if "denied" in msg or "expired" in msg:
                raise
            return None
        if isinstance(data, dict) and data.get("access_token"):
            self._store(data)
            return data
        return None

    def _store(self, data: dict[str, Any]) -> None:
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token") or self.refresh_token
        self.expires_at = time.time() + int(data.get("expires_in") or 7 * 86400)

    async def ensure_token(self) -> bool:
        """Refresh the token if it is within a day of expiry. True if changed."""
        if not self.access_token:
            raise SimklAuthError("not signed in")
        if time.time() < self.expires_at - 86400:
            return False
        if not self.refresh_token:
            if time.time() >= self.expires_at:
                raise SimklAuthError("expired")
            return False
        try:
            data = await self._request(
                "POST",
                f"{API_BASE}/oauth2/token",
                form={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "refresh_token": self.refresh_token,
                },
            )
        except SimklAuthError:
            raise
        except SimklError as err:
            if time.time() >= self.expires_at:
                raise SimklAuthError("refresh failed") from err
            return False
        if isinstance(data, dict) and data.get("access_token"):
            self._store(data)
            return True
        return False

    # ---------------------------------------------------------------- user API
    async def user_settings(self) -> dict[str, Any]:
        data = await self._request("POST", f"{API_BASE}/users/settings", auth=True)
        return data if isinstance(data, dict) else {}

    async def activities(self) -> dict[str, Any]:
        data = await self._request("GET", f"{API_BASE}/sync/activities", auth=True)
        return data if isinstance(data, dict) else {}

    async def all_items(
        self, kind: str, status: str, extra: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"{API_BASE}/sync/all-items/{kind}/{status}", params=extra, auth=True
        )
        if isinstance(data, dict):
            return data.get(kind) or []
        return []

    async def detail(self, kind: str, sid: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        path = {"show": "tv", "anime": "anime", "movie": "movies"}[kind]
        info = await self._request(
            "GET", f"{API_BASE}/{path}/{sid}", params={"extended": "full"}, auth=True
        )
        eps: list[dict[str, Any]] = []
        if kind != "movie":
            got = await self._request(
                "GET",
                f"{API_BASE}/{path}/episodes/{sid}",
                params={"extended": "full"},
                auth=True,
            )
            if isinstance(got, list):
                eps = got
        return (info if isinstance(info, dict) else {}), eps

    # ------------------------------------------------------------- public CDN
    async def calendar_month(self, year: int, month: int, kind: str) -> dict[str, Any]:
        """kind: tv | anime | movie_release. Month is NOT zero padded."""
        data = await self._request("GET", f"{CDN_BASE}/{year}/{month}/{kind}.json")
        return data if isinstance(data, dict) else {}
