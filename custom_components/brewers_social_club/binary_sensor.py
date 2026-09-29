"""Binary sensors for Brewers Social Club."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import BscDataUpdateCoordinator
from .entity import BscCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BSC binary sensors."""

    async_add_entities([BscApiConnectedBinarySensor(entry.runtime_data)])


class BscApiConnectedBinarySensor(BscCoordinatorEntity, BinarySensorEntity):
    """Show whether the latest BSC refresh succeeded."""

    _attr_translation_key = "api_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: BscDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "api_connected")

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "partial_errors": dict(self.coordinator.data.errors),
            "modules_loaded": sorted(self.coordinator.data.modules),
        }

