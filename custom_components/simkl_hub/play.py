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


def friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    """Best default label for a chosen device."""
    state = hass.states.get(entity_id)
    if state is not None and state.name:
        return state.name
    ent = er.async_get(hass).async_get(entity_id)
    return (ent and (ent.name or ent.original_name)) or entity_id


def normalise_players(raw: list | None) -> list[dict[str, str]]:
    """Accept both the old list-of-ids and the new list-of-{id,name} formats."""
    out: list[dict[str, str]] = []
    for item in raw or []:
        if isinstance(item, str):
            out.append({"id": item, "name": ""})
        elif isinstance(item, dict) and item.get("id"):
            out.append({"id": item["id"], "name": item.get("name") or ""})
    return out


def configured_players(hass: HomeAssistant, players: list, notify: list) -> list[dict[str, str]]:
    """Only the devices the user chose, with the names they gave them."""
    out: list[dict[str, str]] = []
    for item in normalise_players(players) + normalise_players(notify):
        eid = item["id"]
        is_phone = eid.startswith("notify.")
        name = item["name"] or (
            eid.split("mobile_app_", 1)[-1].replace("_", " ").title() + " (phone)"
            if is_phone
            else friendly_name(hass, eid)
        )
        out.append({"id": eid, "name": name, "type": "phone" if is_phone else "chosen"})
    return out
