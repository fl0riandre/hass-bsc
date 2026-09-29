"""Base entities for Brewers Social Club."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BscDataUpdateCoordinator


class BscCoordinatorEntity(CoordinatorEntity[BscDataUpdateCoordinator]):
    """Base coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BscDataUpdateCoordinator, unique_suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            manufacturer="Brewers Social Club",
            name="Brewers Social Club API",
            model="BSC cloud API",
            configuration_url=coordinator.client.base_url,
        )

