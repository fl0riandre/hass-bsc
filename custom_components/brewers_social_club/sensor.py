"""Sensors for Brewers Social Club."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    MODULE_BENEFITS,
    MODULE_BREWFATHER,
    MODULE_GROUP_ORDERS,
    MODULE_MEMBERS,
    MODULE_OVERVIEW,
    MODULE_PARTNERS,
    MODULE_PAYMENTS,
    MODULE_RAPT,
    MODULE_STORAGE,
)
from .coordinator import BscDataUpdateCoordinator
from .data import active_items as _active
from .data import controller_connected as _controller_connected
from .data import first_number as _first_number
from .data import items as _items
from .data import nested as _nested
from .entity import BscCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class BscSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[BscSensorDescription, ...] = (
    BscSensorDescription(
        key="members_total",
        translation_key="members_total",
        icon="mdi:account-group",
        value_fn=lambda d: _nested(d, MODULE_OVERVIEW, "overview", "totalMembers"),
    ),
    BscSensorDescription(
        key="members_active",
        translation_key="members_active",
        icon="mdi:account-check",
        value_fn=lambda d: _nested(d, MODULE_OVERVIEW, "overview", "activeMembers"),
    ),
    BscSensorDescription(
        key="profiles_pending",
        translation_key="profiles_pending",
        icon="mdi:account-alert",
        value_fn=lambda d: _nested(d, MODULE_OVERVIEW, "overview", "pendingProfiles"),
    ),
    BscSensorDescription(
        key="invitations_pending",
        translation_key="invitations_pending",
        icon="mdi:email-clock",
        value_fn=lambda d: _nested(d, MODULE_OVERVIEW, "overview", "invitationsPending"),
    ),
    BscSensorDescription(
        key="partners_total",
        translation_key="partners_total",
        icon="mdi:store",
        value_fn=lambda d: len(_items(d, MODULE_PARTNERS, "partners")),
        attributes_fn=lambda d: {
            "active": sum(1 for item in _items(d, MODULE_PARTNERS, "partners") if item.get("active", True)),
            "offers": len(_items(d, MODULE_PARTNERS, "partnerOffers")),
        },
    ),
    BscSensorDescription(
        key="benefits_active",
        translation_key="benefits_active",
        icon="mdi:gift",
        value_fn=lambda d: len(_active(_items(d, MODULE_BENEFITS, "benefits"))),
    ),
    BscSensorDescription(
        key="group_orders_active",
        translation_key="group_orders_active",
        icon="mdi:cart-variant",
        value_fn=lambda d: len(_active(_items(d, MODULE_GROUP_ORDERS, "groupOrders"))),
        attributes_fn=lambda d: {
            "titles": [str(item.get("title") or item.get("name") or "") for item in _active(_items(d, MODULE_GROUP_ORDERS, "groupOrders"))[:20]],
        },
    ),
    BscSensorDescription(
        key="brewfather_active",
        translation_key="brewfather_active",
        icon="mdi:barley",
        value_fn=lambda d: len(_active(_items(d, MODULE_BREWFATHER, "batches"))),
        attributes_fn=lambda d: {
            "stale": bool(_nested(d, MODULE_BREWFATHER, "refresh", "stale", default=False)),
            "fetched_at": _nested(d, MODULE_BREWFATHER, "refresh", "fetchedAt"),
        },
    ),
    BscSensorDescription(
        key="rapt_controllers",
        translation_key="rapt_controllers",
        icon="mdi:thermometer-lines",
        value_fn=lambda d: len(_items(d, MODULE_RAPT, "controllers")),
        attributes_fn=lambda d: {
            "connected": sum(1 for item in _items(d, MODULE_RAPT, "controllers") if _controller_connected(item)),
            "stale": bool(_nested(d, MODULE_RAPT, "refresh", "stale", default=False)),
        },
    ),
    BscSensorDescription(
        key="payments_total",
        translation_key="payments_total",
        icon="mdi:cash-register",
        value_fn=lambda d: len(_items(d, MODULE_PAYMENTS, "encaissements")),
    ),
    BscSensorDescription(
        key="storage_members",
        translation_key="storage_members",
        icon="mdi:database",
        value_fn=lambda d: _nested(d, MODULE_STORAGE, "storage", "counts", "members"),
        attributes_fn=lambda d: _nested(d, MODULE_STORAGE, "storage", "counts", default={}),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BSC sensors and discover dynamic production entities."""

    coordinator: BscDataUpdateCoordinator = entry.runtime_data
    async_add_entities(BscSummarySensor(coordinator, description) for description in SENSORS)

    known: set[str] = set()

    @callback
    def discover_dynamic_entities() -> None:
        entities: list[SensorEntity] = []
        modules = coordinator.data.modules
        for batch in _active(_items(modules, MODULE_BREWFATHER, "batches")):
            batch_id = str(batch.get("id") or batch.get("_id") or "").strip()
            if batch_id and f"batch:{batch_id}" not in known:
                known.add(f"batch:{batch_id}")
                entities.append(BscBatchSensor(coordinator, batch_id))
        for controller in _items(modules, MODULE_RAPT, "controllers"):
            controller_id = str(controller.get("id") or "").strip()
            if not controller_id:
                continue
            for kind in ("temperature", "target_temperature", "gravity"):
                unique = f"rapt:{controller_id}:{kind}"
                if unique not in known:
                    known.add(unique)
                    entities.append(BscRaptSensor(coordinator, controller_id, kind))
        if entities:
            async_add_entities(entities)

    discover_dynamic_entities()
    entry.async_on_unload(coordinator.async_add_listener(discover_dynamic_entities))


class BscSummarySensor(BscCoordinatorEntity, SensorEntity):
    """A stable summary sensor."""

    entity_description: BscSensorDescription

    def __init__(self, coordinator: BscDataUpdateCoordinator, description: BscSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data.modules)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data.modules)


def _batch_by_id(coordinator: BscDataUpdateCoordinator, batch_id: str) -> dict[str, Any]:
    return next(
        (
            item
            for item in _items(coordinator.data.modules, MODULE_BREWFATHER, "batches")
            if str(item.get("id") or item.get("_id") or "") == batch_id
        ),
        {},
    )


class BscBatchSensor(BscCoordinatorEntity, SensorEntity):
    """One Brewfather batch."""

    _attr_icon = "mdi:barley"

    def __init__(self, coordinator: BscDataUpdateCoordinator, batch_id: str) -> None:
        super().__init__(coordinator, f"brewfather_batch_{batch_id}")
        self._batch_id = batch_id
        self._attr_name = self._display_name

    @property
    def _display_name(self) -> str:
        batch = _batch_by_id(self.coordinator, self._batch_id)
        name = batch.get("name") or _nested(batch, "recipe", "name") or self._batch_id
        number = batch.get("batchNo") or batch.get("batchNumber") or batch.get("number")
        return f"Brassin {number} · {name}" if number else f"Brassin · {name}"

    @property
    def native_value(self) -> str | None:
        return _batch_by_id(self.coordinator, self._batch_id).get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        batch = _batch_by_id(self.coordinator, self._batch_id)
        allowed = (
            "batchNo", "batchNumber", "brewingDate", "brewDate", "fermentationStartDate",
            "conditioningDate", "bottlingDate", "volume", "estimatedFg", "measuredFg",
            "measuredAbv", "updatedAt",
        )
        return {key: batch.get(key) for key in allowed if batch.get(key) is not None}


def _controller_by_id(coordinator: BscDataUpdateCoordinator, controller_id: str) -> dict[str, Any]:
    return next(
        (item for item in _items(coordinator.data.modules, MODULE_RAPT, "controllers") if str(item.get("id") or "") == controller_id),
        {},
    )


class BscRaptSensor(BscCoordinatorEntity, SensorEntity):
    """One RAPT metric."""

    def __init__(self, coordinator: BscDataUpdateCoordinator, controller_id: str, kind: str) -> None:
        super().__init__(coordinator, f"rapt_{controller_id}_{kind}")
        self._controller_id = controller_id
        self._kind = kind
        controller = _controller_by_id(coordinator, controller_id)
        name = controller.get("name") or controller.get("deviceName") or controller_id
        labels = {
            "temperature": "Température",
            "target_temperature": "Consigne",
            "gravity": "Densité",
        }
        self._attr_name = f"RAPT {name} · {labels[kind]}"
        self._attr_icon = "mdi:thermometer" if kind != "gravity" else "mdi:hydrometer"
        if kind in {"temperature", "target_temperature"}:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        controller = _controller_by_id(self.coordinator, self._controller_id)
        paths = {
            "temperature": (("temperature",), ("currentTemperature",), ("latestTelemetry", "temperature")),
            "target_temperature": (("targetTemperature",), ("setPoint",), ("temperatureSetting",)),
            "gravity": (("gravity",), ("specificGravity",), ("hydrometer", "gravity"), ("latestTelemetry", "gravity")),
        }
        return _first_number(controller, paths[self._kind])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        controller = _controller_by_id(self.coordinator, self._controller_id)
        linked = controller.get("linkedBatch") if isinstance(controller.get("linkedBatch"), dict) else {}
        return {
            "connected": _controller_connected(controller),
            "signal": controller.get("rssi") or controller.get("signalStrength"),
            "linked_batch": linked.get("name") or linked.get("id"),
        }
