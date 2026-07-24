"""Config flow for the Mojio integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    ConfigEntry,
)
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_TENANT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TENANT,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import AUTH_ERROR_STATUSES
from .mojio_sdk.api import API

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TENANT, default=DEFAULT_TENANT): TextSelector(),
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_CLIENT_ID): TextSelector(),
        vol.Required(CONF_CLIENT_SECRET): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


def _validate(data: Mapping[str, Any]) -> int:
    """Log in and fetch vehicles. Blocking - run in the executor.

    Returns the number of vehicles found.
    """
    api = API(
        data[CONF_TENANT],
        data[CONF_CLIENT_ID],
        data[CONF_CLIENT_SECRET],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )
    if not api.login():
        raise InvalidAuth
    return len(api.get_vehicles())


class InvalidAuth(Exception):
    """Credentials were rejected."""


class MojioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Mojio config flow."""

    VERSION = 1

    async def _async_validate(
        self, user_input: Mapping[str, Any]
    ) -> tuple[dict[str, str], int | None]:
        """Validate credentials, returning (errors, vehicle_count)."""
        errors: dict[str, str] = {}
        try:
            count = await self.hass.async_add_executor_job(_validate, user_input)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except requests.exceptions.HTTPError as err:
            status = err.response.status_code if err.response is not None else None
            if status in AUTH_ERROR_STATUSES:
                errors["base"] = "invalid_auth"
            else:
                LOGGER.debug("Mojio returned HTTP %s during setup", status)
                errors["base"] = "cannot_connect"
        except requests.exceptions.RequestException as err:
            LOGGER.debug("Could not reach Mojio during setup: %s", err)
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001 - surfaced as 'unknown' to the user
            LOGGER.exception("Unexpected error validating Mojio credentials")
            errors["base"] = "unknown"
        else:
            return errors, count
        return errors, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_TENANT]}:{user_input[CONF_USERNAME]}".lower()
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            errors, _count = await self._async_validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=dict(user_input)
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication after the stored credentials stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for a new password, reusing the rest of the existing config."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            candidate = {**entry.data, **user_input}
            errors, _count = await self._async_validate(candidate)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=candidate)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MojioOptionsFlow:
        """Return the options flow."""
        return MojioOptionsFlow()


class MojioOptionsFlow(OptionsFlow):
    """Handle Mojio options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the polling interval."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=30,
                            unit_of_measurement="seconds",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
