"""Sensors for the Mojio integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MojioConfigEntry
from .entity import MojioEntity
from .mojio_sdk.trip import Trip
from .mojio_sdk.vehicle import Vehicle

type StateType = str | int | float | datetime | None


def _raw_value(vehicle: Vehicle, key: str) -> float | None:
    """Read Value out of one of the API's {Value, Unit} blocks."""
    block = (vehicle.raw_json or {}).get(key) or {}
    return block.get("Value")


def _duration_seconds(trip: Trip | None) -> float | None:
    """Convert a trip's HH:MM:SS duration into seconds."""
    if trip is None:
        return None
    duration = trip.getattribute("duration", None)
    if not duration:
        return None
    try:
        hours, minutes, seconds = (float(part) for part in duration.split(":"))
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _last_contact(vehicle: Vehicle) -> datetime | None:
    """Parse the vehicle's last contact timestamp."""
    if not (raw := vehicle.getattribute("last_contact", None)):
        return None
    return dt_util.parse_datetime(raw)


@dataclass(frozen=True, kw_only=True)
class MojioSensorEntityDescription(SensorEntityDescription):
    """Describes a Mojio sensor."""

    value_fn: Callable[[Vehicle, Trip | None], StateType]


SENSORS: tuple[MojioSensorEntityDescription, ...] = (
    MojioSensorEntityDescription(
        key="fuel_level",
        translation_key="fuel_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gas-station",
        value_fn=lambda vehicle, _trip: vehicle.fuel.getattribute("fuel_level", None),
    ),
    MojioSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle, _trip: vehicle.battery.getattribute("value", None),
    ),
    MojioSensorEntityDescription(
        key="speed",
        translation_key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda vehicle, _trip: vehicle.getattribute(
            "current_speed_kph", None
        ),
    ),
    MojioSensorEntityDescription(
        key="rpm",
        translation_key="rpm",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:engine",
        value_fn=lambda vehicle, _trip: vehicle.getattribute("current_rpm", None),
    ),
    MojioSensorEntityDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda vehicle, _trip: _raw_value(vehicle, "Odometer"),
    ),
    MojioSensorEntityDescription(
        key="virtual_odometer",
        translation_key="virtual_odometer",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle, _trip: _raw_value(vehicle, "VirtualOdometer"),
    ),
    MojioSensorEntityDescription(
        key="engine_oil_temperature",
        translation_key="engine_oil_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle, _trip: vehicle.engine_oil.getattribute("temp_c", None),
    ),
    MojioSensorEntityDescription(
        key="diagnostic_codes",
        translation_key="diagnostic_codes",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:car-wrench",
        value_fn=lambda vehicle, _trip: vehicle.dtc.getattribute("count", 0),
    ),
    MojioSensorEntityDescription(
        key="vehicle_status",
        translation_key="vehicle_status",
        icon="mdi:car-info",
        value_fn=lambda vehicle, _trip: vehicle.getattribute("status", None) or None,
    ),
    MojioSensorEntityDescription(
        key="last_contact",
        translation_key="last_contact",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda vehicle, _trip: _last_contact(vehicle),
    ),
    MojioSensorEntityDescription(
        key="last_trip_distance",
        translation_key="last_trip_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=2,
        value_fn=lambda _vehicle, trip: (
            trip.getattribute("distance_km", None) if trip else None
        ),
    ),
    MojioSensorEntityDescription(
        key="last_trip_duration",
        translation_key="last_trip_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        value_fn=lambda _vehicle, trip: _duration_seconds(trip),
    ),
    MojioSensorEntityDescription(
        key="last_trip_start",
        translation_key="last_trip_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _vehicle, trip: (
            dt_util.parse_datetime(trip.getattribute("start_date", "") or "")
            if trip
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MojioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Mojio sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        MojioSensor(coordinator, vehicle_id, description)
        for vehicle_id in coordinator.data.vehicles
        for description in SENSORS
    )


class MojioSensor(MojioEntity, SensorEntity):
    """A sensor reading from a Mojio-tracked vehicle."""

    entity_description: MojioSensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """Return the sensor's value."""
        if (vehicle := self.vehicle) is None:
            return None
        return self.entity_description.value_fn(vehicle, self.last_trip)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Expose supporting detail for a few sensors."""
        if self.entity_description.key == "diagnostic_codes":
            if (vehicle := self.vehicle) is None:
                return None
            return {"codes": vehicle.dtc.getattribute("details", []) or []}
        if self.entity_description.key == "last_trip_distance":
            trip = self.last_trip
            if trip is None:
                return None
            # The Audi tenant reports a flat 0 distance, in which case the SDK
            # recovers it from the trip's GPS path instead.
            return {"derived_from_gps_path": trip.distance_is_derived}
        return None
