"""Data coordinator and calendar cache for SIMKL Hub."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SimklAuthError, SimklClient, SimklError
from .const import (
    CALENDAR_TTL,
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_POPULAR_MOVIES,
    CONF_POPULAR_TV,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_MINUTES,
    DEFAULT_POPULAR_MOVIES,
    DEFAULT_POPULAR_TV,
    DEFAULT_SCAN_MINUTES,
    DETAIL_TTL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SINGULAR = {"shows": "show", "anime": "anime", "movies": "movie"}


def _tidy(item: dict[str, Any], kind: str, status: str) -> dict[str, Any]:
    obj = item.get("show") or item.get("movie") or {}
    ids = obj.get("ids") or {}
    out: dict[str, Any] = {
        "id": ids.get("simkl"),
        "title": obj.get("title"),
        "year": obj.get("year"),
        "poster": obj.get("poster"),
        "kind": kind,
        "status": status,
        "watched": item.get("watched_episodes_count"),
        "total": item.get("total_episodes_count"),
        "last": item.get("last_watched_at"),
        "added": item.get("added_to_watchlist_at"),
        "imdb": ids.get("imdb"),
    }
    nx = item.get("next_to_watch_info")
    if isinstance(nx, dict):
        out["next"] = {k: nx.get(k) for k in ("title", "season", "episode", "date")}
    return out


class SimklCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Syncs the user's lists. Uses /sync/activities to skip needless fetches."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: SimklClient) -> None:
        minutes = entry.options.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=max(10, int(minutes))),
        )
        self.client = client
        self._activity_stamp: str | None = None
        self._cal_cache: dict[tuple[int, int, str], tuple[float, dict[str, Any]]] = {}
        self._detail_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
        self._cal_lock = asyncio.Lock()

    # ------------------------------------------------------------------ sync
    async def _persist_tokens(self) -> None:
        c = self.client
        data = {
            **self.config_entry.data,
            CONF_ACCESS_TOKEN: c.access_token,
            CONF_REFRESH_TOKEN: c.refresh_token,
            CONF_EXPIRES_AT: c.expires_at,
        }
        self.hass.config_entries.async_update_entry(self.config_entry, data=data)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if await self.client.ensure_token():
                await self._persist_tokens()
            act = await self.client.activities()
            stamp = str(act.get("all") or act)
            if self.data and stamp == self._activity_stamp:
                return self.data

            watching: list[dict[str, Any]] = []
            plan: list[dict[str, Any]] = []
            completed: dict[str, int] = {}
            for kind in ("shows", "anime", "movies"):
                single = SINGULAR[kind]
                if kind != "movies":
                    for it in await self.client.all_items(
                        kind, "watching", {"next_watch_info": "yes"}
                    ):
                        watching.append(_tidy(it, single, "watching"))
                for it in await self.client.all_items(kind, "plantowatch"):
                    plan.append(_tidy(it, single, "plantowatch"))
                completed[kind] = len(
                    await self.client.all_items(kind, "completed", {"extended": "simkl_ids_only"})
                )
        except SimklAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SimklError as err:
            raise UpdateFailed(str(err)) from err

        self._activity_stamp = stamp
        watching.sort(key=lambda x: x.get("last") or "", reverse=True)
        plan.sort(key=lambda x: x.get("added") or "", reverse=True)
        return {
            "watching": watching,
            "plan": plan,
            "completed": completed,
            "updated": time.time(),
        }

    # ---------------------------------------------------------------- detail
    async def async_detail(self, kind: str, sid: str) -> dict[str, Any]:
        key = (kind, str(sid))
        hit = self._detail_cache.get(key)
        if hit and time.time() - hit[0] < DETAIL_TTL:
            return hit[1]
        try:
            if await self.client.ensure_token():
                await self._persist_tokens()
            info, eps = await self.client.detail(kind, str(sid))
        except SimklAuthError:
            self.config_entry.async_start_reauth(self.hass)
            raise
        ids = info.get("ids") or {}
        rating = ((info.get("ratings") or {}).get("simkl") or {}).get("rating")
        out = {
            "id": str(sid),
            "kind": kind,
            "title": info.get("title"),
            "year": info.get("year"),
            "overview": info.get("overview"),
            "poster": info.get("poster"),
            "genres": info.get("genres") or [],
            "runtime": info.get("runtime"),
            "status": info.get("status"),
            "network": info.get("network"),
            "rating": rating,
            "imdb": ids.get("imdb"),
            "tmdb": ids.get("tmdb"),
            "eps": [
                {
                    "s": e.get("season") or 1,
                    "e": e.get("episode"),
                    "t": e.get("title"),
                    "d": e.get("description"),
                    "a": e.get("date") or e.get("aired"),
                }
                for e in eps
                if e.get("type") in (None, "episode")
            ],
        }
        self._detail_cache[key] = (time.time(), out)
        return out

    # -------------------------------------------------------------- calendar
    def _mine(self) -> dict[tuple[str, int], str]:
        mine: dict[tuple[str, int], str] = {}
        for it in (self.data or {}).get("watching", []) + (self.data or {}).get("plan", []):
            if it.get("id"):
                mine[(it["kind"], int(it["id"]))] = it["status"]
        return mine

    async def _month_file(self, year: int, month: int, kind: str) -> dict[str, Any]:
        key = (year, month, kind)
        hit = self._cal_cache.get(key)
        if hit and time.time() - hit[0] < CALENDAR_TTL:
            return hit[1]
        async with self._cal_lock:
            hit = self._cal_cache.get(key)
            if hit and time.time() - hit[0] < CALENDAR_TTL:
                return hit[1]
            try:
                raw = await self.client.calendar_month(year, month, kind)
            except SimklError as err:
                _LOGGER.debug("calendar %s %s/%s failed: %s", kind, year, month, err)
                raw = {}
            # keep memory low: store only what we need from the (multi-MB) file
            meta = raw.get("metadata") or {}
            slim_meta: dict[str, Any] = {}
            for sid, m in meta.items():
                ids = m.get("ids") or {}
                slim_meta[str(sid)] = {
                    "title": m.get("title"),
                    "poster": m.get("poster"),
                    "imdb": ids.get("imdb"),
                    "pop": int(m.get("watching") or 0) + int(m.get("plan_to_watch") or 0),
                    "rating": ((m.get("ratings") or {}).get("simkl") or {}).get("rating"),
                    "genres": (m.get("genres") or [])[:3],
                }
            slim = {"calendar": raw.get("calendar") or [], "metadata": slim_meta}
            self._cal_cache[key] = (time.time(), slim)
            return slim

    async def async_calendar(
        self, year: int, month: int, scope: str = "major"
    ) -> list[dict[str, Any]]:
        """Entries for a month. scope: mine | major (mine + popular) | all."""
        opts = self.config_entry.options
        top_tv = int(opts.get(CONF_POPULAR_TV, DEFAULT_POPULAR_TV))
        top_mv = int(opts.get(CONF_POPULAR_MOVIES, DEFAULT_POPULAR_MOVIES))
        mine = self._mine()
        results: list[dict[str, Any]] = []
        for file_kind, kind in (("tv", "show"), ("anime", "anime"), ("movie_release", "movie")):
            data = await self._month_file(year, month, file_kind)
            meta = data["metadata"]
            cal = data["calendar"]
            budget = top_mv if kind == "movie" else top_tv
            # popular shows = most-followed titles airing this month
            pops = sorted(
                {str(c["simkl_id"]) for c in cal},
                key=lambda s: meta.get(s, {}).get("pop", 0),
                reverse=True,
            )
            popular = set(pops[:budget])
            for c in cal:
                sid = c.get("simkl_id")
                m = meta.get(str(sid), {})
                is_mine = (kind, int(sid)) in mine
                is_pop = str(sid) in popular and m.get("pop", 0) > 0
                if scope == "mine" and not is_mine:
                    continue
                if scope == "major" and not (is_mine or is_pop):
                    continue
                ep = c.get("episode") or {}
                results.append(
                    {
                        "k": kind,
                        "id": sid,
                        "date": c.get("date"),
                        "title": m.get("title"),
                        "poster": m.get("poster"),
                        "imdb": m.get("imdb"),
                        "s": ep.get("season"),
                        "e": ep.get("episode"),
                        "et": ep.get("title"),
                        "fin": c.get("finale_type"),
                        "mine": is_mine,
                        "st": mine.get((kind, int(sid))),
                        "pop": m.get("pop", 0),
                        "rating": m.get("rating"),
                        "genres": m.get("genres"),
                    }
                )
        results.sort(key=lambda r: r.get("date") or "")
        return results
