"""Tests for the Mojio entities."""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.mojio.mojio_sdk.polyline import path_distance_meters


@pytest.fixture(autouse=True)
async def setup_integration(hass: HomeAssistant, mock_config_entry, mock_api):
    """Load the integration for every test in this module."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_device_tracker_reports_position(hass: HomeAssistant):
    """The tracker exposes the vehicle's GPS position and accuracy."""
    state = hass.states.get("device_tracker.audi_q7")
    assert state is not None
    assert state.attributes["latitude"] == 0.0
    assert state.attributes["longitude"] == 0.0
    assert state.attributes["gps_accuracy"] == 18.2
    assert state.attributes["source_type"] == "gps"


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.audi_q7_fuel_level", "38.82"),
        ("sensor.audi_q7_battery_voltage", "12.2"),
        # suggested_display_precision only rounds the display, not the state.
        ("sensor.audi_q7_odometer", "100737000.0"),
        ("sensor.audi_q7_distance_since_install", "1216212.0"),
        ("sensor.audi_q7_diagnostic_codes", "0"),
        ("sensor.audi_q7_vehicle_status", "Stopped"),
        ("sensor.audi_q7_engine_oil_temperature", "0.0"),
        # Ignition is off in the fixture, so the SDK reports no live speed/RPM.
        ("sensor.audi_q7_speed", "unknown"),
        ("sensor.audi_q7_engine_rpm", "unknown"),
    ],
)
async def test_sensor_states(hass: HomeAssistant, entity_id: str, expected: str):
    """Sensors report the values parsed out of the API payload."""
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} was not created"
    assert state.state == expected


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("binary_sensor.audi_q7_ignition", "off"),
        ("binary_sensor.audi_q7_parked", "on"),
        ("binary_sensor.audi_q7_idling", "off"),
        ("binary_sensor.audi_q7_tow_detected", "off"),
        ("binary_sensor.audi_q7_disturbance", "off"),
        ("binary_sensor.audi_q7_accident_detected", "off"),
        ("binary_sensor.audi_q7_check_engine", "off"),
        ("binary_sensor.audi_q7_battery_connected", "on"),
    ],
)
async def test_binary_sensor_states(hass: HomeAssistant, entity_id: str, expected: str):
    """Binary sensors reflect the vehicle's reported flags."""
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} was not created"
    assert state.state == expected


async def test_last_trip_duration(hass: HomeAssistant):
    """The trip's HH:MM:SS duration is exposed in seconds."""
    state = hass.states.get("sensor.audi_q7_last_trip_duration")
    assert state is not None
    assert float(state.state) == 170.0  # 00:02:50


async def test_last_trip_distance_is_derived_from_polyline(hass: HomeAssistant):
    """The Audi tenant reports 0 distance, so it comes from the GPS path."""
    state = hass.states.get("sensor.audi_q7_last_trip_distance")
    assert state is not None

    expected_km = path_distance_meters("_p~iF~ps|U_ulLnnqC_mqNvxq`@") / 1000
    assert float(state.state) == pytest.approx(expected_km, rel=1e-6)
    assert state.attributes["derived_from_gps_path"] is True


async def test_tire_pressure_sensor_absent_from_payload(hass: HomeAssistant):
    """The Audi payload has no TirePressure block, so the state is unknown."""
    state = hass.states.get("binary_sensor.audi_q7_tire_pressure_warning")
    assert state is not None
    assert state.state == "unknown"
