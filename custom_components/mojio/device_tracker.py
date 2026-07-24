"""Device tracker for the Mojio integration."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MojioConfigEntry
from .entity import MojioEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MojioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Mojio device trackers."""
    coordinator = entry.runtime_data
    async_add_entities(
        MojioDeviceTracker(coordinator, vehicle_id)
        for vehicle_id in coordinator.data.vehicles
    )


class MojioDeviceTracker(MojioEntity, TrackerEntity):
    """Track a vehicle's GPS position."""

    _attr_name = None
    _attr_icon = "mdi:car"

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return the latitude of the vehicle."""
        if (vehicle := self.vehicle) is None:
            return None
        return vehicle.location.getattribute("latitude", None)

    @property
    def longitude(self) -> float | None:
        """Return the longitude of the vehicle."""
        if (vehicle := self.vehicle) is None:
            return None
        return vehicle.location.getattribute("longitude", None)

    @property
    def location_accuracy(self) -> float:
        """Return the GPS accuracy of the vehicle, in meters."""
        if (vehicle := self.vehicle) is None:
            return 0
        accuracy = (vehicle.location.raw_json or {}).get("Accuracy") or {}
        return accuracy.get("Value") or 0
