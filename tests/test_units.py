"""Unit-system handling for the Mojio distance sensors.

Home Assistant maps a metres-based distance sensor onto feet for US customary
users, and only a kilometres-based one onto miles. These tests pin that down so
the odometers can't silently regress to feet.
"""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM

DISTANCE_SENSORS = [
    "sensor.audi_q7_odometer",
    "sensor.audi_q7_distance_since_install",
    "sensor.audi_q7_last_trip_distance",
]


async def _setup(hass: HomeAssistant, mock_config_entry) -> None:
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize("entity_id", DISTANCE_SENSORS)
async def test_distances_display_in_miles_for_us_customary(
    hass: HomeAssistant, mock_config_entry, mock_api, entity_id: str
):
    """US customary users see miles, not feet."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, mock_config_entry)

    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} was not created"
    assert state.attributes["unit_of_measurement"] == "mi"


@pytest.mark.parametrize("entity_id", DISTANCE_SENSORS)
async def test_distances_display_in_kilometers_for_metric(
    hass: HomeAssistant, mock_config_entry, mock_api, entity_id: str
):
    """Metric users keep kilometers."""
    hass.config.units = METRIC_SYSTEM
    await _setup(hass, mock_config_entry)

    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} was not created"
    assert state.attributes["unit_of_measurement"] == "km"


async def test_odometer_converts_to_miles(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """The odometer's value is converted, not just relabelled."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    await _setup(hass, mock_config_entry)

    state = hass.states.get("sensor.audi_q7_odometer")
    # 100737000 m -> 100737 km -> ~62595 mi
    assert float(state.state) == pytest.approx(62594.9, abs=1.0)
