"""Smoke tests: sign-in flow, sync, calendar filtering, websocket, open-in-Stremio."""
import re
from datetime import datetime, timezone

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.simkl_hub.const import DOMAIN
from custom_components.simkl_hub.play import stremio_link


def _month_file(sid_mine, sid_big, sid_small):
    return {
        "calendar": [
            {"simkl_id": sid_mine, "date": "2026-11-03T08:00:00Z", "finale_type": None, "episode": {"season": 2, "episode": 5, "title": "Mine"}},
            {"simkl_id": sid_big, "date": "2026-11-03T09:00:00Z", "finale_type": "season", "episode": {"season": 1, "episode": 8, "title": "Big"}},
            {"simkl_id": sid_small, "date": "2026-11-04T09:00:00Z", "finale_type": None, "episode": {"season": 1, "episode": 1, "title": "Small"}},
        ],
        "metadata": {
            str(sid_mine): {"title": "My Show", "ids": {"imdb": "tt1"}, "watching": 5, "plan_to_watch": 1},
            str(sid_big): {"title": "Big Show", "ids": {"imdb": "tt2"}, "watching": 9000, "plan_to_watch": 100},
            str(sid_small): {"title": "Small Show", "ids": {"imdb": "tt3"}, "watching": 0, "plan_to_watch": 0},
        },
    }


@pytest.fixture
async def entry(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get("https://api.simkl.com/sync/activities", json={"all": "stamp1"})
    item = {"show": {"title": "My Show", "year": 2020, "poster": "p/1", "ids": {"simkl": 11, "imdb": "tt1"}},
            "watched_episodes_count": 3, "total_episodes_count": 10,
            "next_to_watch_info": {"title": "x", "season": 2, "episode": 5, "date": "2026-11-03"}}
    for kind in ("shows", "anime", "movies"):
        for status in ("watching", "plantowatch", "completed"):
            body = {kind: [item]} if kind == "shows" and status == "watching" else {kind: []}
            aioclient_mock.get(re.compile(rf"https://api\.simkl\.com/sync/all-items/{kind}/{status}.*"), json=body)
    aioclient_mock.get(re.compile(r"https://data\.simkl\.in/calendar/v2/2026/11/tv\.json.*"), json=_month_file(11, 22, 33))
    aioclient_mock.get(re.compile(r"https://data\.simkl\.in/calendar/v2/.*"), json={"calendar": [], "metadata": {}})
    e = MockConfigEntry(domain=DOMAIN, unique_id="u1", title="tester",
                        data={"client_id": "cid", "access_token": "a", "refresh_token": "r", "expires_at": 9999999999})
    e.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e.entry_id)
    await hass.async_block_till_done()
    return e


async def test_completed_listing(hass, entry, hass_ws_client):
    c = hass.data[DOMAIN][entry.entry_id]
    c.data["done_items"] = [{"id": 7, "kind": "movie", "title": "Seen It", "poster": None}]
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "simkl_hub/state"})
    assert "movie|7" in (await ws.receive_json())["result"]["done"]
    await ws.send_json({"id": 2, "type": "simkl_hub/completed"})
    assert (await ws.receive_json())["result"][0]["title"] == "Seen It"


async def test_sync_and_sensors(hass, entry):
    assert hass.states.get("sensor.simkl_tester_watching").state == "1"
    assert hass.states.get("sensor.simkl_tester_episodes_waiting").state == "1"


async def test_calendar_scopes(hass, entry):
    c = hass.data[DOMAIN][entry.entry_id]
    mine = await c.async_calendar(2026, 11, "mine")
    assert [i["title"] for i in mine] == ["My Show"] and mine[0]["mine"]
    major = await c.async_calendar(2026, 11, "major")
    assert {i["title"] for i in major} == {"My Show", "Big Show"}
    every = await c.async_calendar(2026, 11, "all")
    assert len(every) == 3


async def test_websocket(hass, entry, hass_ws_client):
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "simkl_hub/state"})
    r = await ws.receive_json()
    assert r["success"] and r["result"]["watching"][0]["title"] == "My Show"
    await ws.send_json({"id": 2, "type": "simkl_hub/calendar", "year": 2026, "month": 11, "scope": "major"})
    r = await ws.receive_json()
    assert r["success"] and len(r["result"]) == 2


async def test_open_service(hass, entry):
    calls = async_mock_service(hass, "remote", "turn_on")
    await hass.services.async_call(DOMAIN, "open_in_stremio",
        {"target": "remote.tv", "kind": "show", "imdb": "tt1", "season": 2, "episode": 5}, blocking=True)
    assert calls[0].data["activity"] == "stremio:///detail/series/tt1/tt1:2:5"


def test_links():
    assert stremio_link("tt9", "movie") == "stremio:///detail/movie/tt9/tt9"
    assert stremio_link("tt9", "show") == "stremio:///detail/series/tt9"
    assert stremio_link(None, "show", "A B") == "stremio:///search?search=A%20B"


async def test_config_flow(hass, aioclient_mock, monkeypatch):
    from homeassistant.data_entry_flow import FlowResultType
    from custom_components.simkl_hub import config_flow

    monkeypatch.setattr(config_flow, "POLL_MIN_SECONDS", 0)
    aioclient_mock.post("https://api.simkl.com/oauth2/device", json={
        "device_code": "dc", "user_code": "ABC12", "verification_uri": "https://simkl.com/pin", "expires_in": 900, "interval": 0})
    aioclient_mock.post("https://api.simkl.com/oauth2/token", json={
        "access_token": "tok", "refresh_token": "ref", "expires_in": 604800})
    aioclient_mock.post("https://api.simkl.com/users/settings", json={"user": {"name": "kurt"}, "account": {"id": 42}})
    aioclient_mock.get("https://api.simkl.com/sync/activities", json={"all": "s"})
    aioclient_mock.get(re.compile(r"https://api\.simkl\.com/sync/all-items/.*"), json={})
    aioclient_mock.get(re.compile(r"https://data\.simkl\.in/.*"), json={})

    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert r["type"] == FlowResultType.FORM
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"client_id": "cid"})
    assert r["type"] == FlowResultType.SHOW_PROGRESS
    assert r["description_placeholders"]["code"] == "ABC12"
    await hass.async_block_till_done()
    r = await hass.config_entries.flow.async_configure(r["flow_id"])
    assert r["type"] == FlowResultType.CREATE_ENTRY
    assert r["title"] == "kurt"
    assert r["data"]["access_token"] == "tok" and r["data"]["client_id"] == "cid"


async def test_players_option(hass, entry, hass_ws_client):
    from homeassistant.data_entry_flow import FlowResultType

    hass.states.async_set("remote.lounge_tv", "off", {"friendly_name": "Lounge TV"})
    hass.states.async_set("remote.other_tv", "off", {"friendly_name": "Other TV"})
    ws = await hass_ws_client(hass)
    # Nothing is auto-discovered: until the user picks devices the list is empty.
    await ws.send_json({"id": 1, "type": "simkl_hub/players"})
    assert (await ws.receive_json())["result"] == []

    r = await hass.config_entries.options.async_init(entry.entry_id)
    assert r["type"] == FlowResultType.MENU
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"next_step_id": "players"})
    assert r["type"] == FlowResultType.FORM
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"players": ["remote.lounge_tv"], "notify_targets": []}
    )
    assert r["type"] == FlowResultType.FORM and r["step_id"] == "player_names"
    r = await hass.config_entries.options.async_configure(
        r["flow_id"], {"remote.lounge_tv": "Nvidia Shield Lounge"}
    )
    assert r["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await ws.send_json({"id": 2, "type": "simkl_hub/players"})
    res = await ws.receive_json()
    assert res["result"] == [{"id": "remote.lounge_tv", "name": "Nvidia Shield Lounge", "type": "chosen"}]


async def test_search_trending_and_writes(hass, entry, aioclient_mock, hass_ws_client):
    aioclient_mock.get(
        re.compile(r"https://api\.simkl\.com/search/all.*"),
        json=[{"title": "Dune", "year": 2021, "endpoint_type": "movies", "poster": "a/b",
               "ids": {"simkl_id": 5, "imdb": "tt1160419"}, "ratings": {"simkl": {"rating": 8.1}}}],
    )
    aioclient_mock.get(
        re.compile(r"https://data\.simkl\.in/discover/trending/tv/today_100\.json.*"),
        json=[{"title": "Hit Show", "poster": "c/d", "release_date": "2024-05-01", "ids": {"simkl_id": 9, "imdb": "tt9"}}],
    )
    aioclient_mock.post("https://api.simkl.com/sync/history", json={"added": {}})
    aioclient_mock.post("https://api.simkl.com/sync/add-to-list", json={"added": {}})
    ws = await hass_ws_client(hass)

    await ws.send_json({"id": 1, "type": "simkl_hub/search", "q": "dune"})
    res = (await ws.receive_json())["result"]
    assert res[0]["kind"] == "movie" and res[0]["id"] == 5 and res[0]["rating"] == 8.1

    await ws.send_json({"id": 2, "type": "simkl_hub/trending", "kind": "show"})
    res = (await ws.receive_json())["result"]
    assert res[0]["title"] == "Hit Show" and res[0]["year"] == 2024 and res[0]["rank"] == 1

    await ws.send_json({"id": 3, "type": "simkl_hub/mark", "kind": "show", "simkl_id": "11", "season": 2, "episode": 5})
    assert (await ws.receive_json())["success"]
    sent = [c for c in aioclient_mock.mock_calls if c[0] == "POST"][-1][2]
    assert sent == {"shows": [{"ids": {"simkl": 11}, "seasons": [{"number": 2, "episodes": [{"number": 5}]}]}]}

    await ws.send_json({"id": 4, "type": "simkl_hub/set_list", "kind": "movie", "simkl_id": "5", "to": "plantowatch"})
    assert (await ws.receive_json())["success"]
    assert [c for c in aioclient_mock.mock_calls if c[0] == "POST"][-1][2] == {"movies": [{"ids": {"simkl": 5}, "to": "plantowatch"}]}


async def test_calendar_prefs_filter(hass, entry, hass_ws_client):
    c = hass.data[DOMAIN][entry.entry_id]
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "simkl_hub/prefs_set", "kinds": {"show": True, "anime": False, "movie": True}, "hidden": ["show|22"]})
    assert (await ws.receive_json())["success"]
    every = await c.async_calendar(2026, 11, "all")
    assert "Big Show" not in {i["title"] for i in every}  # id 22 hidden
    assert "My Show" in {i["title"] for i in every}
    await ws.send_json({"id": 2, "type": "simkl_hub/prefs_set", "kinds": {"show": False}, "hidden": []})
    assert (await ws.receive_json())["success"]
    # turning a type off trims popular extras only; titles on your own list stay
    titles = {i["title"] for i in await c.async_calendar(2026, 11, "all")}
    assert "My Show" in titles
    assert "Big Show" not in titles
