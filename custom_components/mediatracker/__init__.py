"""The MediaTracker integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp.client_exceptions import ClientResponseError
from pymediatracker import MediaTracker
from pymediatracker.exceptions import MediaTrackerException
from pymediatracker.objects.config import MediaTrackerConfig

import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_TOKEN): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.CALENDAR]

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MediaTracker from a config entry."""

    client = MediaTracker(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_TOKEN],
    )

    coordinator = MediaTrackerDataUpdateCoordinator(hass, client=client)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class MediaTrackerDataUpdateCoordinator(DataUpdateCoordinator[MediaTracker]):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, client: MediaTracker) -> None:
        """Initialize."""
        self.mediatracker = client

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.entities: list[MediaTrackerEntity] = []

    async def _async_update_data(self) -> MediaTracker:
        """Update data via library."""
        try:
            await self.mediatracker.fetch()
        except MediaTrackerException as exception:
            raise UpdateFailed() from exception

        return self.mediatracker


class MediaTrackerEntity(CoordinatorEntity):
    """Representation of a MediaTracker entity."""

    def __init__(self, coordinator: MediaTrackerDataUpdateCoordinator) -> None:
        """Initialize MediaTracker entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "mediatracker_unique_id")},
            manufacturer="mediatracker",
            model="Media Tracker",
            name="Media Tracker",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://github.com/jonkristian/mediatracker-ha",
        )
