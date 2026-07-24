"""Data update coordinator for the Mojio integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER
from .mojio_sdk.api import API
from .mojio_sdk.trip import Trip
from .mojio_sdk.vehicle import Vehicle

# The token endpoint answers bad credentials with 400 rather than 401, so both
# are treated as an auth problem and routed into the reauth flow.
AUTH_ERROR_STATUSES = (400, 401, 403)


@dataclass
class MojioData:
    """Vehicles and their most recent completed trip, keyed by vehicle id."""

    vehicles: dict[str, Vehicle] = field(default_factory=dict)
    last_trips: dict[str, Trip] = field(default_factory=dict)


class MojioDataUpdateCoordinator(DataUpdateCoordinator[MojioData]):
    """Fetch vehicle and trip data from the Mojio API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: API,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> MojioData:
        """Fetch the latest data, off the event loop."""
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except requests.exceptions.HTTPError as err:
            status = err.response.status_code if err.response is not None else None
            if status in AUTH_ERROR_STATUSES:
                raise ConfigEntryAuthFailed(
                    "Mojio rejected the stored credentials"
                ) from err
            raise UpdateFailed(f"Mojio API returned HTTP {status}") from err
        except requests.exceptions.RequestException as err:
            raise UpdateFailed(f"Could not reach Mojio: {err}") from err

    def _fetch(self) -> MojioData:
        """Blocking fetch, run in the executor."""
        vehicles = self.api.get_vehicles()
        trips = self.api.get_trips()

        data = MojioData()
        for vehicle in vehicles:
            if not vehicle.has_data or vehicle.mojio_id is None:
                continue
            data.vehicles[vehicle.mojio_id] = vehicle

            # Trips are keyed against the vehicle's Id. The trips list only
            # covers a recent window, so fall back to fetching the vehicle's
            # last trip directly when it isn't in there.
            last_trip = Trip.get_last_trip(trips, vehicle.mojio_id, True)
            if not last_trip.has_data and vehicle.last_trip_id:
                try:
                    last_trip = self.api.get_trip(vehicle.last_trip_id)
                except requests.exceptions.RequestException as err:
                    # A missing last trip shouldn't fail the whole update.
                    LOGGER.debug(
                        "Could not fetch last trip %s for vehicle %s: %s",
                        vehicle.last_trip_id,
                        vehicle.mojio_id,
                        err,
                    )
                    last_trip = Trip({})
            data.last_trips[vehicle.mojio_id] = last_trip

        return data
