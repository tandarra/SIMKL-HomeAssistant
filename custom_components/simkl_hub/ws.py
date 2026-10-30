"""WebSocket API used by the SIMKL card."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.core import HomeAssistant, callback

from .api import SimklError, SimklPermission
from .const import CONF_NOTIFY, CONF_PLAYERS, DOMAIN
from .coordinator import SimklCoordinator
from .play import async_open, configured_players, stremio_link


_LOGGER = logging.getLogger(__name__)


def _coordinator(hass: HomeAssistant, entry_id: str | None) -> SimklCoordinator | None:
    coords: dict[str, SimklCoordinator] = hass.data.get(DOMAIN, {})
    if entry_id and entry_id in coords:
        return coords[entry_id]
    return next(iter(coords.values()), None)


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_state)
    websocket_api.async_register_command(hass, ws_detail)
    websocket_api.async_register_command(hass, ws_calendar)
    websocket_api.async_register_command(hass, ws_completed)
    websocket_api.async_register_command(hass, ws_refresh)
    websocket_api.async_register_command(hass, ws_players)
    websocket_api.async_register_command(hass, ws_open)
    websocket_api.async_register_command(hass, ws_search)
    websocket_api.async_register_command(hass, ws_trending)
    websocket_api.async_register_command(hass, ws_mark)
    websocket_api.async_register_command(hass, ws_set_list)


@websocket_api.websocket_command({vol.Required("type"): "simkl_hub/state"})
@websocket_api.async_response
async def ws_state(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_result(msg["id"], {"connected": False})
        return
    d = c.data or {}
    connection.send_result(
        msg["id"],
        {
            "connected": True,
            "user": c.config_entry.title,
            "updated": d.get("updated"),
            "watching": d.get("watching", []),
            "plan": d.get("plan", []),
            "completed": d.get("completed", {}),
            "done": [f"{x['kind']}|{x['id']}" for x in d.get("done_items", [])],
            "ok": c.last_update_success,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/detail",
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Required("simkl_id"): vol.Coerce(str),
    }
)
@websocket_api.async_response
async def ws_detail(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    _LOGGER.debug("detail %s %s", msg["kind"], msg["simkl_id"])
    try:
        async with asyncio.timeout(45):
            result = await c.async_detail(msg["kind"], msg["simkl_id"])
        connection.send_result(msg["id"], result)
    except TimeoutError:
        _LOGGER.warning("SIMKL detail %s/%s timed out", msg["kind"], msg["simkl_id"])
        connection.send_error(msg["id"], "timeout", "SIMKL did not answer in time")
    except SimklError as err:
        _LOGGER.warning("SIMKL detail %s/%s failed: %s", msg["kind"], msg["simkl_id"], err)
        connection.send_error(msg["id"], "simkl_error", str(err))


@websocket_api.websocket_command({vol.Required("type"): "simkl_hub/completed"})
@callback
def ws_completed(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    connection.send_result(msg["id"], (c.data or {}).get("done_items", []) if c else [])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/calendar",
        vol.Required("year"): vol.All(int, vol.Range(min=2024, max=2100)),
        vol.Required("month"): vol.All(int, vol.Range(min=1, max=12)),
        vol.Optional("scope", default="major"): vol.In(["mine", "major", "all"]),
    }
)
@websocket_api.async_response
async def ws_calendar(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    items = await c.async_calendar(msg["year"], msg["month"], msg["scope"])
    connection.send_result(msg["id"], items)


@websocket_api.websocket_command({vol.Required("type"): "simkl_hub/refresh"})
@websocket_api.async_response
async def ws_refresh(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is not None:
        c._activity_stamp = None  # force a full re-sync
        await c.async_request_refresh()
    connection.send_result(msg["id"], {"ok": c is not None})


@websocket_api.websocket_command({vol.Required("type"): "simkl_hub/players"})
@callback
def ws_players(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Only devices the user picked in Configure. Nothing is auto-discovered."""
    c = _coordinator(hass, None)
    if c is None:
        connection.send_result(msg["id"], [])
        return
    chosen = c.config_entry.options.get(CONF_PLAYERS) or []
    phones = c.config_entry.options.get(CONF_NOTIFY) or []
    connection.send_result(msg["id"], configured_players(hass, chosen, phones))


_FAILED = object()


async def _guarded(connection: websocket_api.ActiveConnection, msg: dict[str, Any], coro: Any) -> Any:
    try:
        async with asyncio.timeout(45):
            return await coro
    except SimklPermission:
        connection.send_error(
            msg["id"], "needs_reconnect",
            "SIMKL needs write permission. Open Settings > Devices & services > SIMKL Hub and reconnect.",
        )
    except TimeoutError:
        connection.send_error(msg["id"], "timeout", "SIMKL did not answer in time")
    except SimklError as err:
        connection.send_error(msg["id"], "simkl_error", str(err))
    return _FAILED


@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/search",
        vol.Required("q"): vol.All(str, vol.Length(min=2, max=80)),
        vol.Optional("kind", default="all"): vol.In(["all", "show", "anime", "movie"]),
    }
)
@websocket_api.async_response
async def ws_search(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    res = await _guarded(connection, msg, c.async_search(msg["q"].strip(), msg["kind"]))
    if res is not _FAILED:
        connection.send_result(msg["id"], res)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/trending",
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Optional("period", default="today"): vol.In(["today", "week", "month"]),
    }
)
@websocket_api.async_response
async def ws_trending(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    res = await _guarded(connection, msg, c.async_trending(msg["kind"], msg["period"]))
    if res is not _FAILED:
        connection.send_result(msg["id"], res)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/mark",
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Required("simkl_id"): vol.Coerce(str),
        vol.Optional("season"): vol.Any(None, int),
        vol.Optional("episode"): vol.Any(None, int),
        vol.Optional("watched", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_mark(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    coro = c.async_mark(
        msg["kind"], msg["simkl_id"], season=msg.get("season"), episode=msg.get("episode"), watched=msg["watched"]
    )
    if await _guarded(connection, msg, coro) is not _FAILED:
        connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/set_list",
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Required("simkl_id"): vol.Coerce(str),
        vol.Required("to"): vol.In(["plantowatch", "watching", "completed", "hold", "dropped"]),
    }
)
@websocket_api.async_response
async def ws_set_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    if await _guarded(connection, msg, c.async_set_list(msg["kind"], msg["simkl_id"], msg["to"])) is not _FAILED:
        connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/open",
        vol.Required("target"): str,
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Optional("imdb"): vol.Any(None, str),
        vol.Optional("season"): vol.Any(None, int),
        vol.Optional("episode"): vol.Any(None, int),
        vol.Optional("title"): vol.Any(None, str),
    }
)
@websocket_api.async_response
async def ws_open(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    target = msg["target"]
    domain = target.split(".", 1)[0]
    if domain == "notify":
        if not target.startswith("notify.mobile_app_"):
            connection.send_error(msg["id"], "not_allowed", "Only companion-app notify targets are allowed")
            return
    elif domain not in ("remote", "media_player"):
        connection.send_error(msg["id"], "not_allowed", "Unsupported target")
        return
    elif not connection.user.permissions.check_entity(target, POLICY_CONTROL):
        connection.send_error(msg["id"], "unauthorized", "You may not control this device")
        return
    link = stremio_link(msg.get("imdb"), msg["kind"], msg.get("title"), msg.get("season"), msg.get("episode"))
    try:
        await async_open(hass, msg["target"], link, msg.get("title") or "")
    except Exception as err:  # noqa: BLE001 - report any service failure to the card
        connection.send_error(msg["id"], "open_failed", str(err))
        return
    connection.send_result(msg["id"], {"link": link})
