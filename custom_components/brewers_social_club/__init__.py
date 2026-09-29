"""Brewers Social Club integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BscApiClient
from .const import CONF_API_KEY, DOMAIN, PLATFORMS, SERVICE_GET_API_DATA
from .coordinator import BscDataUpdateCoordinator

BscConfigEntry = ConfigEntry[BscDataUpdateCoordinator]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up integration-level services."""

    async def async_get_api_data(call: ServiceCall) -> dict:
        path = str(call.data["path"]).strip()
        if not path.startswith("/api/") or ".." in path:
            raise vol.Invalid("path must start with /api/ and cannot contain ..")
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries or entries[0].runtime_data is None:
            raise RuntimeError("Brewers Social Club is not configured")
        return await entries[0].runtime_data.client.async_get(path)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_API_DATA,
        async_get_api_data,
        schema=vol.Schema({vol.Required("path"): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BscConfigEntry) -> bool:
    """Set up BSC from a config entry."""

    client = BscApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        entry.data[CONF_API_KEY],
    )
    coordinator = BscDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BscConfigEntry) -> bool:
    """Unload a BSC config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: BscConfigEntry) -> None:
    """Reload after options change."""

    await hass.config_entries.async_reload(entry.entry_id)
