"""Planning helpers kept independent from Home Assistant imports."""

from __future__ import annotations

from datetime import datetime, time, timezone, timedelta
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .const import PLANNING_TIMEZONE


def planning_day_window(
    now: datetime | None = None,
    timezone_name: str = PLANNING_TIMEZONE,
) -> tuple[datetime, datetime, str]:
    """Return the current BSC civil day as an exclusive UTC interval."""

    zone = ZoneInfo(timezone_name)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local_now = current.astimezone(zone)
    start_local = datetime.combine(local_now.date(), time.min, tzinfo=zone)
    end_local = datetime.combine(local_now.date() + timedelta(days=1), time.min, tzinfo=zone)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), local_now.date().isoformat()


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def planning_day_path(now: datetime | None = None) -> tuple[str, dict[str, str]]:
    """Build the dated planning endpoint and matching window metadata."""

    start, end, local_date = planning_day_window(now)
    values = {"from": _iso_utc(start), "to": _iso_utc(end)}
    return f"/api/admin/planning?{urlencode(values)}", {
        **values,
        "date": local_date,
        "timezone": PLANNING_TIMEZONE,
    }


def normalized_planning(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a recorder-friendly view of one planning payload."""

    planning = payload.get("planning") if isinstance(payload.get("planning"), dict) else {}
    resources = {
        str(item.get("id")): item
        for item in planning.get("resources", [])
        if isinstance(item, dict) and item.get("id")
    }
    plans = {
        str(item.get("id")): item
        for item in planning.get("plans", [])
        if isinstance(item, dict) and item.get("id")
    }
    locations = {
        str(item.get("id")): item
        for item in planning.get("locations", [])
        if isinstance(item, dict) and item.get("id")
    }

    grouped: dict[str, dict[str, Any]] = {}
    bookings = planning.get("bookings", [])
    if not isinstance(bookings, list):
        bookings = []
    booking_count = 0
    for booking in bookings:
        if not isinstance(booking, dict) or str(booking.get("status", "")).lower() == "cancelled":
            continue
        plan = plans.get(str(booking.get("planId")), {})
        if str(plan.get("status", "")).lower() == "cancelled":
            continue
        booking_count += 1
        resource = resources.get(str(booking.get("resourceId")), {})
        location = locations.get(str(plan.get("locationId")), {})
        plan_id = str(booking.get("planId") or booking.get("id") or "")
        event = grouped.setdefault(
            plan_id,
            {
                "id": plan_id,
                "title": plan.get("title") or resource.get("name") or "Réservation",
                "kind": plan.get("kind"),
                "status": plan.get("status") or booking.get("status"),
                "start": booking.get("startAt"),
                "end": booking.get("endAt"),
                "location": location.get("name"),
                "resources": [],
                "phases": [],
            },
        )
        start = booking.get("startAt")
        end = booking.get("endAt")
        if start and (not event.get("start") or str(start) < str(event["start"])):
            event["start"] = start
        if end and (not event.get("end") or str(end) > str(event["end"])):
            event["end"] = end
        resource_name = resource.get("name")
        if resource_name and resource_name not in event["resources"]:
            event["resources"].append(resource_name)
        phase = booking.get("phase")
        if phase and phase not in event["phases"]:
            event["phases"].append(phase)
    events = list(grouped.values())
    events.sort(key=lambda item: str(item.get("start") or ""))
    raw_allocations = planning.get("containerAllocations", [])
    allocations = [item for item in raw_allocations if isinstance(item, dict)] if isinstance(raw_allocations, list) else []
    return {
        "count": len(events),
        "booking_count": booking_count,
        "events": events[:50],
        "truncated": len(events) > 50,
        "plans": len(events),
        "resources": len(resources),
        "container_allocations": len(allocations),
        "timezone": planning.get("timezone") or PLANNING_TIMEZONE,
    }
