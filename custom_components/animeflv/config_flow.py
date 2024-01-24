"""Adds config flow for Blueprint."""
from __future__ import annotations
from collections import OrderedDict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession



from .api import (
    AnimeFlvApiClient,
    AnimeFlvApiClientAuthenticationError,
    AnimeFlvApiClientCommunicationError,
    AnimeFlvApiClientError,
)
from .const import DOMAIN, LOGGER, DEFAULT_CONF_PASSWORD, DEFAULT_CONF_USERNAME

try:
    from .secrets import DEFAULT_CONF_PASSWORD, DEFAULT_CONF_USERNAME
except:
    pass


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}
        if user_input is not None:
            try:
                profile = await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except AnimeFlvApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                self._errors["base"] = "auth"
            except AnimeFlvApiClientCommunicationError as exception:
                LOGGER.error(exception)
                self._errors["base"] = "connection"
            except AnimeFlvApiClientError as exception:
                LOGGER.exception(exception)
                self._errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=profile,data=user_input)

        return await self._show_config_form(user_input)


    async def _show_config_form(self, user_input):
        """Show the configuration form to edit location data."""
        username = DEFAULT_CONF_USERNAME
        password = DEFAULT_CONF_PASSWORD

        if user_input is not None:
            if CONF_USERNAME in user_input:
                username = user_input[CONF_USERNAME]
            if CONF_PASSWORD in user_input:
                password = user_input[CONF_PASSWORD]

        data_schema = OrderedDict()
        data_schema[vol.Required(CONF_USERNAME, default=username)] = str
        data_schema[vol.Required(CONF_PASSWORD, default=password)] = str

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self._errors
        )

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = AnimeFlvApiClient(username=username,password=password,hass = self.hass)
        return await client.async_login()
