"""Simple count sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SimklCoordinator

SENSORS = [
    ("watching", "Watching", "mdi:play-circle"),
    ("plan", "Plan to watch", "mdi:bookmark-multiple"),
    ("up_next", "Episodes waiting", "mdi:television-play"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord: SimklCoordinator = hass.data[DOMAIN][entry.entry_id]
    add(SimklCount(coord, entry, *s) for s in SENSORS)


class SimklCount(CoordinatorEntity[SimklCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coord: SimklCoordinator, entry: ConfigEntry, key: str, name: str, icon: str) -> None:
        super().__init__(coord)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=f"SIMKL {entry.title}", manufacturer="SIMKL"
        )

    @property
    def native_value(self) -> int | None:
        d = self.coordinator.data or {}
        if self._key == "up_next":
            return sum(1 for x in d.get("watching", []) if (x.get("next") or {}).get("episode") is not None)
        return len(d.get(self._key, []))

    @property
    def extra_state_attributes(self) -> dict:
        d = self.coordinator.data or {}
        if self._key == "watching":
            return {"completed": d.get("completed", {}), "titles": [x["title"] for x in d.get("watching", [])[:15]]}
        return {}
