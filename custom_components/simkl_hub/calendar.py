"""HA calendar entity: releases from your own SIMKL list."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN

SCAN_INTERVAL = timedelta(minutes=15)
from .coordinator import SimklCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([SimklCalendar(hass.data[DOMAIN][entry.entry_id], entry)])


class SimklCalendar(CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "My releases"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coord: SimklCoordinator, entry: ConfigEntry) -> None:
        self._coord = coord
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})
        self._next: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        return self._next

    async def async_update(self) -> None:
        now = dt_util.utcnow()
        evs = await self.async_get_events(self.hass, now, now + timedelta(days=14))
        self._next = next((e for e in evs if e.start >= now - timedelta(hours=3)), None)

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        months = set()
        cur = start_date.replace(day=1)
        while cur <= end_date:
            months.add((cur.year, cur.month))
            cur = (cur + timedelta(days=32)).replace(day=1)
        out: list[CalendarEvent] = []
        for y, m in sorted(months):
            for it in await self._coord.async_calendar(y, m, "mine"):
                start = dt_util.parse_datetime(it["date"] or "")
                if start is None or not (start_date <= start < end_date):
                    continue
                if it["k"] == "movie":
                    summary = f'{it["title"]} (movie release)'
                else:
                    ep = f' S{it["s"]}E{it["e"]}' if it.get("s") is not None else ""
                    summary = f'{it["title"]}{ep}'
                out.append(
                    CalendarEvent(
                        start=start,
                        end=start + timedelta(hours=1),
                        summary=summary,
                        description=it.get("et") or "",
                    )
                )
        return sorted(out, key=lambda e: e.start)
