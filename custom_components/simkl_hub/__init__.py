"""SIMKL Hub: your SIMKL lists, a release calendar and 'open in Stremio' for Home Assistant."""
from __future__ import annotations

import logging
import hashlib
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from . import ws
from .api import SimklClient
from .const import (
    CARD_URL,
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PANEL_URL,
    VERSION,
)
from .coordinator import SimklCoordinator
from .play import async_open, stremio_link

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_OPEN = "open_in_stremio"
OPEN_SCHEMA = vol.Schema(
    {
        vol.Required("target"): cv.string,
        vol.Required("kind"): vol.In(["show", "anime", "movie"]),
        vol.Optional("imdb"): vol.Any(None, cv.string),
        vol.Optional("season"): vol.Any(None, vol.Coerce(int)),
        vol.Optional("episode"): vol.Any(None, vol.Coerce(int)),
        vol.Optional("title"): vol.Any(None, cv.string),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket API, the bundled card and the service (once)."""
    hass.data.setdefault(DOMAIN, {})
    ws.async_register(hass)

    www = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/{DOMAIN}", str(www), cache_headers=False)]
    )
    # Load the card on every dashboard automatically, no manual resource needed.
    # Cache-bust by content hash so proxies/CDNs and the phone app never serve a stale card.
    digest = await hass.async_add_executor_job(
        lambda: hashlib.md5((www / "simkl-hub-card.js").read_bytes()).hexdigest()[:10]
    )
    frontend.add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}-{digest}")

    async def _open(call: ServiceCall) -> None:
        d = call.data
        link = stremio_link(d.get("imdb"), d["kind"], d.get("title"), d.get("season"), d.get("episode"))
        try:
            await async_open(hass, d["target"], link, d.get("title") or "")
        except HomeAssistantError:
            raise
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(DOMAIN, SERVICE_OPEN, _open, schema=OPEN_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = SimklClient(
        async_get_clientsession(hass),
        entry.data[CONF_CLIENT_ID],
        entry.data.get(CONF_ACCESS_TOKEN),
        entry.data.get(CONF_REFRESH_TOKEN),
        entry.data.get(CONF_EXPIRES_AT, 0),
    )
    coordinator = SimklCoordinator(hass, entry, client)
    await coordinator.async_load_prefs()
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Sidebar page (single account assumed; the first entry owns it).
    if len(hass.data[DOMAIN]) == 1:
        try:
            await panel_custom.async_register_panel(
                hass,
                webcomponent_name="simkl-hub-panel",
                frontend_url_path=PANEL_URL,
                module_url=f"{CARD_URL}?v={VERSION}",
                sidebar_title="SIMKL",
                sidebar_icon="mdi:movie-open",
                require_admin=False,
                config={},
            )
        except ValueError:  # already registered (reload)
            pass

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    opts = dict(entry.options)

    async def _maybe_reload(hass: HomeAssistant, updated: ConfigEntry) -> None:
        # Token refreshes update entry.data; only options changes need a reload.
        if dict(updated.options) != opts:
            await hass.config_entries.async_reload(updated.entry_id)

    entry.async_on_unload(entry.add_update_listener(_maybe_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            frontend.async_remove_panel(hass, PANEL_URL)
    return ok
