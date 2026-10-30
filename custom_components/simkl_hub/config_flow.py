"""Config flow: enter your SIMKL app's Client ID, then approve a PIN on simkl.com."""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SimklClient, SimklError
from .play import friendly_name, normalise_players
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_EXPIRES_AT,
    CONF_NOTIFY,
    CONF_OMDB_KEY,
    CONF_PLAYERS,
    CONF_POPULAR_MOVIES,
    CONF_POPULAR_TV,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_MINUTES,
    DEFAULT_POPULAR_MOVIES,
    DEFAULT_POPULAR_TV,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
POLL_MIN_SECONDS = 5


class SimklConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the SIMKL sign-in."""

    VERSION = 1

    def __init__(self) -> None:
        self._client: SimklClient | None = None
        self._device: dict[str, Any] = {}
        self._task: asyncio.Task | None = None
        self._error: str | None = None
        self._reauth_entry: ConfigEntry | None = None

    # ---------------------------------------------------------------- steps
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            cid = user_input[CONF_CLIENT_ID].strip()
            self._client = SimklClient(async_get_clientsession(self.hass), cid)
            try:
                self._device = await self._client.start_device_flow()
            except SimklError:
                errors["base"] = "cannot_start"
            else:
                return await self.async_step_auth()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_CLIENT_ID): str}),
            errors=errors,
            description_placeholders={"dev_url": "https://simkl.com/settings/developer/"},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._reauth_entry is not None
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        self._client = SimklClient(
            async_get_clientsession(self.hass), self._reauth_entry.data[CONF_CLIENT_ID]
        )
        try:
            self._device = await self._client.start_device_flow()
        except SimklError:
            return self.async_show_form(step_id="reauth_confirm", errors={"base": "cannot_start"})
        return await self.async_step_auth()

    async def _wait_for_approval(self) -> None:
        assert self._client is not None
        interval = max(POLL_MIN_SECONDS, int(self._device.get("interval") or 5))
        deadline = time.time() + int(self._device.get("expires_in") or 900)
        while time.time() < deadline:
            await asyncio.sleep(interval)
            try:
                if await self._client.poll_device_flow(self._device["device_code"]):
                    return
            except SimklError as err:
                self._error = str(err)
                return
        self._error = "expired"

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._task is None:
            self._task = self.hass.async_create_task(self._wait_for_approval())
        if not self._task.done():
            return self.async_show_progress(
                step_id="auth",
                progress_action="approve",
                progress_task=self._task,
                description_placeholders={
                    "code": self._device.get("user_code", ""),
                    "url": self._device.get("verification_uri") or "https://simkl.com/pin",
                },
            )
        self._task = None
        if self._error or not (self._client and self._client.access_token):
            return self.async_show_progress_done(next_step_id="failed")
        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_failed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        reason = "denied" if self._error and "denied" in self._error else "expired"
        return self.async_abort(reason=reason)

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._client is not None
        c = self._client
        name = "SIMKL"
        uid = c.client_id
        try:
            settings = await c.user_settings()
            user = settings.get("user") or {}
            acct = settings.get("account") or {}
            name = user.get("name") or name
            uid = str(acct.get("id") or user.get("name") or uid)
        except SimklError:
            _LOGGER.debug("could not read SIMKL user settings", exc_info=True)

        data = {
            CONF_CLIENT_ID: c.client_id,
            CONF_ACCESS_TOKEN: c.access_token,
            CONF_REFRESH_TOKEN: c.refresh_token,
            CONF_EXPIRES_AT: c.expires_at,
        }
        if self._reauth_entry is not None:
            self.hass.config_entries.async_update_entry(self._reauth_entry, data=data)
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        await self.async_set_unique_id(uid)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=name, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return SimklOptionsFlow()


class SimklOptionsFlow(OptionsFlow):
    """Calendar/sync tuning and the list of devices that can open Stremio."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["settings", "players"])

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={**self.config_entry.options, **user_input})
        o = self.config_entry.options
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POPULAR_TV, default=o.get(CONF_POPULAR_TV, DEFAULT_POPULAR_TV)
                    ): vol.All(int, vol.Range(min=0, max=300)),
                    vol.Required(
                        CONF_POPULAR_MOVIES,
                        default=o.get(CONF_POPULAR_MOVIES, DEFAULT_POPULAR_MOVIES),
                    ): vol.All(int, vol.Range(min=0, max=500)),
                    vol.Required(
                        CONF_SCAN_MINUTES, default=o.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)
                    ): vol.All(int, vol.Range(min=10, max=240)),
                    vol.Optional(
                        CONF_OMDB_KEY, description={"suggested_value": o.get(CONF_OMDB_KEY, "")}
                    ): str,
                }
            ),
        )

    async def async_step_players(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 1: tick the devices that should appear as 'Open on...' buttons."""
        if user_input is not None:
            self._picked = list(user_input.get(CONF_PLAYERS, [])) + list(user_input.get(CONF_NOTIFY, []))
            return await self.async_step_player_names()
        o = self.config_entry.options
        phones = sorted(
            f"notify.{s}"
            for s in self.hass.services.async_services_for_domain("notify")
            if s.startswith("mobile_app_")
        )
        current = normalise_players(o.get(CONF_PLAYERS))
        current_phones = normalise_players(o.get(CONF_NOTIFY))
        return self.async_show_form(
            step_id="players",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PLAYERS, default=[p["id"] for p in current]
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["remote", "media_player"], multiple=True)
                    ),
                    vol.Optional(
                        CONF_NOTIFY, default=[p["id"] for p in current_phones]
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=phones, multiple=True, mode=selector.SelectSelectorMode.DROPDOWN
                        )
                    ),
                }
            ),
        )

    async def async_step_player_names(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Step 2: give each chosen device the name shown on its button."""
        picked: list[str] = getattr(self, "_picked", [])
        if user_input is not None:
            players = [
                {"id": eid, "name": (user_input.get(eid) or "").strip()}
                for eid in picked
                if not eid.startswith("notify.")
            ]
            phones = [
                {"id": eid, "name": (user_input.get(eid) or "").strip()}
                for eid in picked
                if eid.startswith("notify.")
            ]
            return self.async_create_entry(
                data={**self.config_entry.options, CONF_PLAYERS: players, CONF_NOTIFY: phones}
            )
        if not picked:
            return self.async_create_entry(
                data={**self.config_entry.options, CONF_PLAYERS: [], CONF_NOTIFY: []}
            )
        o = self.config_entry.options
        saved = {p["id"]: p["name"] for p in normalise_players(o.get(CONF_PLAYERS)) + normalise_players(o.get(CONF_NOTIFY))}
        fields: dict[Any, Any] = {}
        for eid in picked:
            default = saved.get(eid) or (
                eid.split("mobile_app_", 1)[-1].replace("_", " ").title() + " (phone)"
                if eid.startswith("notify.")
                else friendly_name(self.hass, eid)
            )
            fields[vol.Optional(eid, default=default)] = str
        return self.async_show_form(step_id="player_names", data_schema=vol.Schema(fields))
