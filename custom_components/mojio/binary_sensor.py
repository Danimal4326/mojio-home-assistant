"""Binary sensors for the Mojio integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MojioConfigEntry
from .entity import MojioEntity
from .mojio_sdk.vehicle import Vehicle


def _raw_flag(vehicle: Vehicle, key: str) -> bool | None:
    """Read Value out of one of the API's {Value, Timestamp} blocks."""
    block = (vehicle.raw_json or {}).get(key)
    if not isinstance(block, dict):
        return None
    return block.get("Value")


@dataclass(frozen=True, kw_only=True)
class MojioBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Mojio binary sensor."""

    value_fn: Callable[[Vehicle], bool | None]


BINARY_SENSORS: tuple[MojioBinarySensorEntityDescription, ...] = (
    MojioBinarySensorEntityDescription(
        key="ignition",
        translation_key="ignition",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda vehicle: vehicle.getattribute("ignition_state", None),
    ),
    MojioBinarySensorEntityDescription(
        key="parked",
        translation_key="parked",
        icon="mdi:car-brake-parking",
        value_fn=lambda vehicle: (
            value if isinstance(value := vehicle.getattribute("parked", None), bool)
            else None
        ),
    ),
    MojioBinarySensorEntityDescription(
        key="idle",
        translation_key="idle",
        icon="mdi:car-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle: vehicle.getattribute("idle", None),
    ),
    MojioBinarySensorEntityDescription(
        key="tow",
        translation_key="tow",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda vehicle: vehicle.getattribute("tow_state", None),
    ),
    MojioBinarySensorEntityDescription(
        key="disturbance",
        translation_key="disturbance",
        device_class=BinarySensorDeviceClass.TAMPER,
        value_fn=lambda vehicle: vehicle.getattribute("disturbance_state", None),
    ),
    MojioBinarySensorEntityDescription(
        key="accident",
        translation_key="accident",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=lambda vehicle: _raw_flag(vehicle, "AccidentState"),
    ),
    MojioBinarySensorEntityDescription(
        key="check_engine",
        translation_key="check_engine",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle: (vehicle.raw_json or {}).get("MilStatus"),
    ),
    MojioBinarySensorEntityDescription(
        key="battery_connected",
        translation_key="battery_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle: vehicle.battery.getattribute("connected", None),
    ),
    MojioBinarySensorEntityDescription(
        key="tire_pressure_warning",
        translation_key="tire_pressure_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda vehicle: vehicle.tires.getattribute("pressure_warning", None),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MojioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Mojio binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        MojioBinarySensor(coordinator, vehicle_id, description)
        for vehicle_id in coordinator.data.vehicles
        for description in BINARY_SENSORS
    )


class MojioBinarySensor(MojioEntity, BinarySensorEntity):
    """An on/off state reported by a Mojio-tracked vehicle."""

    entity_description: MojioBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if (vehicle := self.vehicle) is None:
            return None
        return self.entity_description.value_fn(vehicle)
