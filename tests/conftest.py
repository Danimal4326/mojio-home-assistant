"""Fixtures for the Mojio integration tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_USERNAME,
)

from custom_components.mojio.const import CONF_TENANT, DOMAIN
from custom_components.mojio.mojio_sdk.trip import Trip
from custom_components.mojio.mojio_sdk.vehicle import Vehicle

FIXTURES = Path(__file__).parent / "fixtures"

VEHICLE_ID = "00000000-0000-0000-0000-000000000001"


def load_fixture_json(name: str) -> dict:
    """Load a JSON fixture."""
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in every test."""
    return


@pytest.fixture
def vehicles() -> list[Vehicle]:
    """Vehicles parsed by the real SDK from a sanitized Audi payload."""
    return [Vehicle(item) for item in load_fixture_json("audi_vehicles.json")["Data"]]


@pytest.fixture
def trips() -> list[Trip]:
    """Trips parsed by the real SDK from a sanitized Audi payload."""
    return [Trip(item) for item in load_fixture_json("audi_trips.json")["Data"]]


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A configured Mojio entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        unique_id="audi:test@example.com",
        data={
            CONF_TENANT: "audi",
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "hunter2",
            CONF_CLIENT_ID: "client-id",
            CONF_CLIENT_SECRET: "client-secret",
        },
    )


@pytest.fixture
def mock_api(vehicles, trips):
    """Patch the SDK client, leaving the real Vehicle/Trip parsing in place.

    Setup and the config flow construct the client from different modules, so
    both are pointed at one shared instance - that way a test can adjust the
    client's behaviour without caring which path is exercised.
    """
    instance = MagicMock()
    instance.login.return_value = True
    instance.get_vehicles.return_value = vehicles
    instance.get_trips.return_value = trips

    with (
        patch("custom_components.mojio.API", return_value=instance),
        patch("custom_components.mojio.config_flow.API", return_value=instance),
    ):
        yield instance
