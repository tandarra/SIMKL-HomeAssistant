"""WebSocket API used by the SIMKL card."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.core import HomeAssistant, callback

from .api import SimklError
from .const import DOMAIN
from .coordinator import SimklCoordinator
from .play import async_open, discover_players, stremio_link


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
    websocket_api.async_register_command(hass, ws_refresh)
    websocket_api.async_register_command(hass, ws_players)
    websocket_api.async_register_command(hass, ws_open)


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
            "ok": c.last_update_success,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "simkl_hub/detail",
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Required("id"): vol.Coerce(str),
    }
)
@websocket_api.async_response
async def ws_detail(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    c = _coordinator(hass, None)
    if c is None:
        connection.send_error(msg["id"], "not_connected", "SIMKL is not set up")
        return
    try:
        connection.send_result(msg["id"], await c.async_detail(msg["kind"], msg["id"]))
    except SimklError as err:
        connection.send_error(msg["id"], "simkl_error", str(err))


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
    connection.send_result(msg["id"], discover_players(hass))


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
