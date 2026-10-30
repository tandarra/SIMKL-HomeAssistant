"""HA calendar entity: releases for titles you are actively following (plan to watch, or watched in the last 90 days)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=15)
from .coordinator import SimklCoordinator
from .sensor import _device_name


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([SimklCalendar(hass.data[DOMAIN][entry.entry_id], entry)])


class SimklCalendar(CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "My releases"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coord: SimklCoordinator, entry: ConfigEntry) -> None:
        self._coord = coord
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=_device_name(entry), manufacturer="SIMKL")
        self._next: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        return self._next

    async def async_update(self) -> None:
        now = dt_util.utcnow()
        evs = await self.async_get_events(self.hass, now, now + timedelta(days=14))
        def _begin(e: CalendarEvent) -> datetime:
            return e.start if isinstance(e.start, datetime) else dt_util.start_of_local_day(e.start)

        self._next = next((e for e in sorted(evs, key=_begin) if _begin(e) >= now - timedelta(hours=3)), None)

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        months = set()
        cur = start_date.replace(day=1)
        while cur <= end_date:
            months.add((cur.year, cur.month))
            cur = (cur + timedelta(days=32)).replace(day=1)
        out: list[CalendarEvent] = []
        for y, m in sorted(months):
            for it in await self._coord.async_calendar(y, m, "alerts"):
                start = dt_util.parse_datetime(it["date"] or "")
                if start is None:
                    continue
                if start.tzinfo is None:
                    start = start.replace(tzinfo=dt_util.UTC)
                if it["k"] == "movie":
                    # SIMKL stamps movie releases at midnight US time; they are release *days*,
                    # so show them as all-day events on that day rather than a bogus local time.
                    day = (start - timedelta(hours=6)).date()
                    if not (start_date.date() - timedelta(days=1) <= day <= end_date.date()):
                        continue
                    out.append(
                        CalendarEvent(
                            start=day,
                            end=day + timedelta(days=1),
                            summary=f'{it["title"]} (movie release)',
                            description=it.get("et") or "",
                        )
                    )
                    continue
                if not (start_date <= start < end_date):
                    continue
                start = dt_util.as_local(start)
                ep = f' S{it["s"]}E{it["e"]}' if it.get("s") is not None else ""
                out.append(
                    CalendarEvent(
                        start=start,
                        end=start + timedelta(hours=1),
                        summary=f'{it["title"]}{ep}',
                        description=it.get("et") or "",
                    )
                )
        return sorted(out, key=lambda e: e.start if isinstance(e.start, datetime) else dt_util.start_of_local_day(e.start))
