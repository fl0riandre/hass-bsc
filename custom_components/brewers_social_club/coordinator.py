"""Update coordinator for Brewers Social Club."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BscApiAuthError, BscApiClient, BscApiData, BscApiError
from .const import CONF_MODULES, CONF_SCAN_INTERVAL, DEFAULT_MODULES, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BscDataUpdateCoordinator(DataUpdateCoordinator[BscApiData]):
    """Coordinate all BSC API requests."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: BscApiClient,
    ) -> None:
        self.entry = entry
        self.client = client
        seconds = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=seconds),
            always_update=False,
        )

    async def _async_update_data(self) -> BscApiData:
        modules = self.entry.options.get(CONF_MODULES, DEFAULT_MODULES)
        try:
            return await self.client.async_fetch_modules(modules)
        except BscApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except BscApiError as err:
            raise UpdateFailed(str(err)) from err

