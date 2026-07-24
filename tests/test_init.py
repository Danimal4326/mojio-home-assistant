"""Tests for setting up and unloading the Mojio integration."""

from __future__ import annotations

from unittest.mock import patch

import requests

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.mojio.const import DOMAIN

from .conftest import VEHICLE_ID


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_and_unload(hass: HomeAssistant, mock_config_entry, mock_api):
    """The entry loads, creates entities, and unloads cleanly."""
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("device_tracker.audi_q7") is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_device_registered_with_vin(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """The vehicle is registered as a device with details from VinDetails."""
    await _setup(hass, mock_config_entry)

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, VEHICLE_ID)})
    assert device is not None
    assert device.name == "Audi Q7"
    assert device.manufacturer == "Audi"
    assert device.model == "Q7"
    assert device.hw_version == "2017"
    assert device.serial_number == "WA1AAAAA0AA000001"


async def test_connection_error_sets_retry(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """A network failure during setup leaves the entry retrying, not failed."""
    mock_api.get_vehicles.side_effect = (
        requests.exceptions.ConnectionError("boom")
    )
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_auth_error_starts_reauth(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """A 401 from the API puts the entry into reauth rather than retrying."""
    response = requests.Response()
    response.status_code = 401
    mock_api.get_vehicles.side_effect = requests.exceptions.HTTPError(
        response=response
    )
    await _setup(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


async def test_options_change_reloads_entry(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """Changing the scan interval reloads the entry."""
    await _setup(hass, mock_config_entry)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload"
    ) as mock_reload:
        hass.config_entries.async_update_entry(
            mock_config_entry, options={"scan_interval": 600}
        )
        await hass.async_block_till_done()

    assert mock_reload.called
