"""Tests for the Mojio config flow."""

from __future__ import annotations

import requests

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mojio.const import CONF_TENANT, DOMAIN

USER_INPUT = {
    CONF_TENANT: "audi",
    CONF_USERNAME: "test@example.com",
    CONF_PASSWORD: "hunter2",
    CONF_CLIENT_ID: "client-id",
    CONF_CLIENT_SECRET: "client-secret",
}


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_api):
    """A valid set of credentials creates an entry."""
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == "audi:test@example.com"


async def test_invalid_auth_recovers(hass: HomeAssistant, mock_api):
    """Rejected credentials show an error, then the flow can still succeed."""
    mock_api.login.return_value = False

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_api.login.return_value = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_cannot_connect_recovers(hass: HomeAssistant, mock_api):
    """A network failure shows cannot_connect, then the flow can still succeed."""
    mock_api.login.side_effect = requests.exceptions.ConnectionError()

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_api.login.side_effect = None
    mock_api.login.return_value = True
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_account_aborts(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """The same tenant + account can't be added twice."""
    mock_config_entry.add_to_hass(hass)

    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_password(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """Reauth replaces the stored password on the existing entry."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-password"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_PASSWORD] == "new-password"
    # The rest of the credentials are preserved.
    assert mock_config_entry.data[CONF_CLIENT_ID] == "client-id"


async def test_options_flow_sets_scan_interval(
    hass: HomeAssistant, mock_config_entry, mock_api
):
    """The options flow stores a new polling interval."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 900}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {"scan_interval": 900}
