"""Open a title in Stremio on whatever device the user picks."""
from __future__ import annotations

from urllib.parse import quote

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


def stremio_link(
    imdb: str | None,
    kind: str,
    title: str | None = None,
    season: int | None = None,
    episode: int | None = None,
) -> str:
    """Build a stremio:// deep link (falls back to a title search)."""
    if not imdb:
        return "stremio:///search?search=" + quote(title or "")
    if kind == "movie":
        return f"stremio:///detail/movie/{imdb}/{imdb}"
    if season is not None and episode is not None:
        return f"stremio:///detail/series/{imdb}/{imdb}:{season}:{episode}"
    return f"stremio:///detail/series/{imdb}"


async def async_open(hass: HomeAssistant, target: str, link: str, title: str = "") -> None:
    """Dispatch the deep link according to the target's type."""
    domain, _, name = target.partition(".")
    if domain == "notify":
        # Companion app: tapping the notification opens Stremio.
        await hass.services.async_call(
            "notify",
            name,
            {
                "title": "SIMKL",
                "message": f"Tap to open {title or 'in Stremio'}",
                "data": {"clickAction": link, "url": link, "tag": "simkl_hub"},
            },
            blocking=True,
        )
        return

    platform = None
    reg = er.async_get(hass)
    if (ent := reg.async_get(target)) is not None:
        platform = ent.platform

    if domain == "remote":
        await hass.services.async_call(
            "remote", "turn_on", {"entity_id": target, "activity": link}, blocking=True
        )
    elif domain == "media_player" and platform == "androidtv":
        # ADB based Android TV integration
        await hass.services.async_call(
            "androidtv",
            "adb_command",
            {
                "entity_id": target,
                "command": f'am start -a android.intent.action.VIEW -d "{link}"',
            },
            blocking=True,
        )
    elif domain == "media_player":
        await hass.services.async_call(
            "media_player",
            "play_media",
            {"entity_id": target, "media_content_type": "url", "media_content_id": link},
            blocking=True,
        )
    else:
        raise HomeAssistantError(f"Unsupported target {target}")


def configured_players(hass: HomeAssistant, players: list[str], notify: list[str]) -> list[dict[str, str]]:
    """Devices the user picked in the options flow."""
    reg = er.async_get(hass)
    out: list[dict[str, str]] = []
    for eid in players:
        state = hass.states.get(eid)
        ent = reg.async_get(eid)
        name = (state.name if state else None) or (ent and (ent.name or ent.original_name)) or eid
        out.append({"id": eid, "name": name, "type": "chosen"})
    for svc in notify:
        label = svc.split("mobile_app_", 1)[-1].replace("_", " ").title()
        out.append({"id": svc, "name": f"{label} (phone)", "type": "phone"})
    return out


def discover_players(hass: HomeAssistant) -> list[dict[str, str]]:
    """Android/Google TV style devices plus companion-app notify services."""
    reg = er.async_get(hass)
    out: list[dict[str, str]] = []
    have_remote_for_device: set[str | None] = set()
    for ent in reg.entities.values():
        if ent.disabled or ent.domain != "remote" or ent.platform != "androidtv_remote":
            continue
        have_remote_for_device.add(ent.device_id)
        out.append({"id": ent.entity_id, "name": ent.name or ent.original_name or ent.entity_id, "type": "android_tv"})
    for ent in reg.entities.values():
        if ent.disabled or ent.domain != "media_player" or ent.platform != "androidtv":
            continue
        out.append({"id": ent.entity_id, "name": ent.name or ent.original_name or ent.entity_id, "type": "adb"})
    for svc in hass.services.async_services_for_domain("notify"):
        if svc.startswith("mobile_app_"):
            out.append({"id": f"notify.{svc}", "name": svc[len("mobile_app_"):].replace("_", " ").title() + " (phone)", "type": "phone"})
    return out
