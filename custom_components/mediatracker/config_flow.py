"""Config flow for MediaTracker."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from pymediatracker import MediaTracker
from pymediatracker.exceptions import MediaTrackerException
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str})

ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_UNKNOWN = "unknown"

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    mediatracker = MediaTracker(session, data[CONF_HOST], data[CONF_TOKEN])
    config = await mediatracker.get_config()

    # return {"title": "MediaTracker", "version": config.version}
    return {"title": "MediaTracker"}


class MediaTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a MediaTracker config flow."""

    def __init__(self):
        """Set up the instance."""
        self.discovery_info = {}
        self.data_schema = {
            vol.Required("host"): str,
            vol.Required("token"): str,
        }

    @callback
    def _show_form(self, errors: dict | None = None) -> FlowResult:
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if not user_input:
            return self._show_form()

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except MediaTrackerException:
            _LOGGER.debug("MediaTracker Error", exc_info=True)
            errors["base"] = ERROR_CANNOT_CONNECT
            return self._show_form(errors)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown error trying to connect")
            return self.async_abort(reason=ERROR_UNKNOWN)

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(self.data_schema)
            )

        return self.async_create_entry(
            title=info["title"],
            data=user_input,
        )
