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
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SimklAuthError, SimklClient, SimklError, SimklPermission
from .const import (
    CALENDAR_TTL,
    CONF_ACCESS_TOKEN,
    CONF_EXPIRES_AT,
    CONF_OMDB_KEY,
    CONF_POPULAR_MOVIES,
    CONF_POPULAR_TV,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_MINUTES,
    DEFAULT_POPULAR_MOVIES,
    DEFAULT_POPULAR_TV,
    DEFAULT_SCAN_MINUTES,
    DETAIL_TTL,
    DOMAIN,
    TREND_TTL,
)

_LOGGER = logging.getLogger(__name__)

SINGULAR = {"shows": "show", "anime": "anime", "movies": "movie"}


def _kind_of(raw: str | None) -> str:
    raw = (raw or "").lower()
    if raw.startswith("movie"):
        return "movie"
    if raw.startswith("anime"):
        return "anime"
    return "show"


def _rate(ratings: Any, which: str) -> float | None:
    if isinstance(ratings, dict):
        block = ratings.get(which)
        if isinstance(block, dict):
            val = block.get("rating")
            return float(val) if isinstance(val, (int, float)) and val else None
    return None


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
        self._store = Store[dict[str, Any]](hass, 1, f"{DOMAIN}_{entry.entry_id}_prefs")
        self.prefs: dict[str, Any] = {"kinds": {"show": True, "anime": True, "movie": True}, "hidden": []}

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
            done_items: list[dict[str, Any]] = []
            for kind in ("shows", "anime", "movies"):
                single = SINGULAR[kind]
                if kind != "movies":
                    for it in await self.client.all_items(
                        kind, "watching", {"next_watch_info": "yes"}
                    ):
                        watching.append(_tidy(it, single, "watching"))
                for it in await self.client.all_items(kind, "plantowatch"):
                    plan.append(_tidy(it, single, "plantowatch"))
                finished = await self.client.all_items(kind, "completed")
                completed[kind] = len(finished)
                for it in finished:
                    done_items.append(_tidy(it, single, "completed"))
        except SimklAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SimklError as err:
            raise UpdateFailed(str(err)) from err

        self._activity_stamp = stamp
        watching.sort(key=lambda x: x.get("last") or "", reverse=True)
        plan.sort(key=lambda x: x.get("added") or "", reverse=True)
        done_items.sort(key=lambda x: x.get("last") or x.get("added") or "", reverse=True)
        return {
            "watching": watching,
            "plan": plan,
            "completed": completed,
            "done_items": done_items,
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
            "imdb_rating": _rate(info.get("ratings"), "imdb"),
            "imdb_votes": ((info.get("ratings") or {}).get("imdb") or {}).get("votes"),
            "certification": info.get("certification"),
            "country": info.get("country"),
            "first_aired": info.get("first_aired") or info.get("released"),
            "total_episodes": info.get("total_episodes"),
            "trailers": [t.get("youtube") for t in (info.get("trailers") or []) if isinstance(t, dict) and t.get("youtube")][:3],
            "list": self._list_status(kind, sid),
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
        key_omdb = (self.config_entry.options.get(CONF_OMDB_KEY) or "").strip()
        if key_omdb and not out["imdb"]:
            out["omdb_error"] = "SIMKL has no IMDb id for this title"
        elif key_omdb:
            try:
                extra = await self.client.omdb(key_omdb, out["imdb"])
            except SimklError as err:
                _LOGGER.warning("OMDb lookup for %s failed: %s", out["imdb"], err)
                extra = {"Error": "invalid key or not activated yet (check your email)" if "401" in str(err) else str(err)}
            if str(extra.get("Response")).lower() == "false" or extra.get("Error"):
                out["omdb_error"] = str(extra.get("Error") or "no data")
            for r in extra.get("Ratings") or []:
                if r.get("Source") == "Rotten Tomatoes":
                    out["rotten"] = r.get("Value")
            if extra.get("Metascore") not in (None, "N/A"):
                out["metascore"] = extra.get("Metascore")
            if extra.get("imdbRating") not in (None, "N/A"):
                try:
                    out["imdb_rating"] = float(extra["imdbRating"])
                except ValueError:
                    pass
            if not out.get("rotten") and not out.get("omdb_error"):
                out["omdb_error"] = "OMDb has no Rotten Tomatoes score for this title"
            if out.get("omdb_error") and "has no" not in out["omdb_error"]:
                self._detail_cache[key] = (time.time() - DETAIL_TTL + 60, out)
                return out
        self._detail_cache[key] = (time.time(), out)
        return out

    def _list_status(self, kind: str, sid: str) -> str | None:
        d = self.data or {}
        for name, key in (("completed", "done_items"), ("watching", "watching"), ("plantowatch", "plan")):
            for it in d.get(key, []):
                if it.get("kind") == kind and str(it.get("id")) == str(sid):
                    return name
        return None

    async def async_search(self, q: str, kind: str) -> list[dict[str, Any]]:
        raw = await self._guard(self.client.search(q, kind))
        out = []
        for it in raw:
            ids = it.get("ids") or {}
            if not ids.get("simkl_id") and not ids.get("simkl"):
                continue
            out.append(
                {
                    "id": ids.get("simkl_id") or ids.get("simkl"),
                    "kind": _kind_of(it.get("endpoint_type") or it.get("type")),
                    "title": it.get("title"),
                    "year": it.get("year"),
                    "poster": it.get("poster"),
                    "imdb": ids.get("imdb"),
                    "rating": _rate(it.get("ratings"), "simkl"),
                }
            )
        return out

    async def async_trending(self, kind: str, period: str) -> list[dict[str, Any]]:
        key = ("trend", kind, period)
        hit = self._detail_cache.get(key)  # type: ignore[arg-type]
        if hit and time.time() - hit[0] < TREND_TTL:
            return hit[1]  # type: ignore[return-value]
        feed = {"show": "tv", "movie": "movies", "anime": "anime"}[kind]
        raw = await self._guard(self.client.trending(feed, period))
        out = []
        for i, it in enumerate(raw):
            ids = it.get("ids") or {}
            sid = ids.get("simkl_id") or ids.get("simkl")
            if not sid:
                continue
            year = None
            if isinstance(it.get("release_date"), str) and it["release_date"][:4].isdigit():
                year = int(it["release_date"][:4])
            out.append(
                {
                    "id": sid,
                    "kind": kind,
                    "rank": i + 1,
                    "title": it.get("title"),
                    "year": year or it.get("year"),
                    "poster": it.get("poster"),
                    "imdb": ids.get("imdb"),
                    "rating": _rate(it.get("ratings"), "simkl") or _rate(it.get("ratings"), "imdb"),
                }
            )
        self._detail_cache[key] = (time.time(), out)  # type: ignore[index,assignment]
        return out

    async def _guard(self, coro: Any) -> Any:
        try:
            if await self.client.ensure_token():
                await self._persist_tokens()
            return await coro
        except SimklAuthError:
            self.config_entry.async_start_reauth(self.hass)
            raise

    async def async_mark(
        self, kind: str, sid: str, *, season: int | None, episode: int | None, watched: bool
    ) -> None:
        await self._write(
            self.client.history(kind, sid, season=season, episode=episode, remove=not watched), kind, sid
        )

    async def async_set_list(self, kind: str, sid: str, to: str) -> None:
        if kind == "movie" and to == "completed":
            await self._write(self.client.history(kind, sid), kind, sid)
        else:
            await self._write(self.client.add_to_list(kind, sid, to), kind, sid)

    async def _write(self, coro: Any, kind: str, sid: str) -> None:
        try:
            await self._guard(coro)
        except SimklPermission:
            self.config_entry.async_start_reauth(self.hass)
            raise
        self._detail_cache.pop((kind, str(sid)), None)
        self._activity_stamp = None
        await self.async_request_refresh()

    # ----------------------------------------------------------------- prefs
    async def async_load_prefs(self) -> None:
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            self.prefs["kinds"].update({k: bool(v) for k, v in (saved.get("kinds") or {}).items() if k in self.prefs["kinds"]})
            self.prefs["hidden"] = [str(x) for x in saved.get("hidden") or []]

    async def async_set_prefs(self, kinds: dict[str, bool], hidden: list[str]) -> dict[str, Any]:
        self.prefs["kinds"].update({k: bool(v) for k, v in kinds.items() if k in self.prefs["kinds"]})
        self.prefs["hidden"] = sorted({str(x) for x in hidden})
        await self._store.async_save(self.prefs)
        return self.prefs

    # -------------------------------------------------------------- calendar
    def _mine(self) -> dict[tuple[str, int], str]:
        mine: dict[tuple[str, int], str] = {}
        for it in (self.data or {}).get("watching", []) + (self.data or {}).get("plan", []):
            if it.get("id"):
                mine[(it["kind"], int(it["id"]))] = it["status"]
        return mine

    def _active(self) -> set[tuple[str, int]]:
        """Plan-to-watch titles plus shows watched in the last 90 days (for alerts)."""
        cutoff = dt_util.utcnow() - timedelta(days=90)
        out: set[tuple[str, int]] = set()
        d = self.data or {}
        for it in d.get("plan", []):
            if it.get("id"):
                out.add((it["kind"], int(it["id"])))
        for it in d.get("watching", []):
            last = dt_util.parse_datetime(it.get("last") or "") if it.get("last") else None
            if it.get("id") and last is not None and last >= cutoff:
                out.add((it["kind"], int(it["id"])))
        return out

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
        active = self._active() if scope == "alerts" else set()
        hidden = set(self.prefs["hidden"])
        results: list[dict[str, Any]] = []
        for file_kind, kind in (("tv", "show"), ("anime", "anime"), ("movie_release", "movie")):
            kind_on = self.prefs["kinds"].get(kind, True)
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
                if f"{kind}|{sid}" in hidden:
                    continue
                is_mine = (kind, int(sid)) in mine
                if not kind_on and not is_mine:
                    continue  # the type filter only trims popular extras; titles on your list stay
                is_pop = str(sid) in popular and m.get("pop", 0) > 0
                if scope == "mine" and not is_mine:
                    continue
                if scope == "alerts" and (kind, int(sid)) not in active:
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
