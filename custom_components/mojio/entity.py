"""Base entity for the Mojio integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import MojioDataUpdateCoordinator
from .mojio_sdk.trip import Trip
from .mojio_sdk.vehicle import Vehicle


class MojioEntity(CoordinatorEntity[MojioDataUpdateCoordinator]):
    """Common behaviour for entities belonging to one vehicle."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: MojioDataUpdateCoordinator,
        vehicle_id: str,
        description: EntityDescription | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        if description is not None:
            self.entity_description = description
            self._attr_unique_id = f"{vehicle_id}_{description.key}"
        else:
            self._attr_unique_id = vehicle_id

        vehicle = coordinator.data.vehicles[vehicle_id]
        vin_details = (vehicle.raw_json or {}).get("VinDetails") or {}
        make = vin_details.get("Make")
        model = vin_details.get("Model")
        year = vin_details.get("Year")

        # Prefer "Audi Q7" over the SDK's "2017 Audi Q7" so entity ids don't
        # get prefixed with the model year; the year is carried separately.
        if make and model:
            name = f"{make} {model}"
        else:
            name = vehicle.name or vehicle.getattribute("licence_plate") or vehicle_id

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vehicle_id)},
            name=name,
            manufacturer=make,
            model=model,
            hw_version=str(year) if year else None,
            serial_number=vehicle.vin,
        )

    @property
    def vehicle(self) -> Vehicle | None:
        """Return this entity's vehicle, if it's still present."""
        return self.coordinator.data.vehicles.get(self._vehicle_id)

    @property
    def last_trip(self) -> Trip | None:
        """Return the vehicle's most recent completed trip, if any."""
        trip = self.coordinator.data.last_trips.get(self._vehicle_id)
        return trip if trip is not None and trip.has_data else None

    @property
    def available(self) -> bool:
        """Return whether the vehicle is still reported by the API."""
        return super().available and self.vehicle is not None
