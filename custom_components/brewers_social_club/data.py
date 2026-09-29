"""Dependency-free data helpers for BSC payloads."""

from __future__ import annotations

from typing import Any


def nested(data: dict[str, Any], *path: str, default: Any = None) -> Any:
    """Read a nested dictionary value safely."""

    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def items(data: dict[str, Any], module: str, key: str) -> list[dict[str, Any]]:
    """Return a list of dictionaries from a module payload."""

    value = nested(data, module, key, default=[])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def active_items(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter archived or otherwise inactive BSC records."""

    hidden = {"archived", "cancelled", "closed", "distributed", "inactive"}
    return [
        item
        for item in values
        if item.get("active", True) is not False
        and str(item.get("status", "")).strip().lower() not in hidden
    ]


def first_number(data: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> float | None:
    """Return the first valid numeric metric among candidate paths."""

    for path in paths:
        value = nested(data, *path)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            continue
    return None


def controller_connected(controller: dict[str, Any]) -> bool:
    """Normalize RAPT connectivity fields."""

    for key in ("connected", "isConnected", "online"):
        if key in controller:
            return bool(controller[key])
    return str(controller.get("status", "")).lower() in {"connected", "online"}

