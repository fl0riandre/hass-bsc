"""Tests for today's BSC planning window and normalization."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "custom_components" / "brewers_social_club"

package = types.ModuleType("brewers_social_club")
package.__path__ = [str(PACKAGE)]
sys.modules["brewers_social_club"] = package
for module_name in ("const", "planning"):
    spec = importlib.util.spec_from_file_location(
        f"brewers_social_club.{module_name}", PACKAGE / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from brewers_social_club.planning import normalized_planning, planning_day_path, planning_day_window  # noqa: E402


class PlanningTests(unittest.TestCase):
    def test_summer_day_uses_paris_midnights(self) -> None:
        start, end, local_date = planning_day_window(datetime(2026, 9, 30, 10, tzinfo=timezone.utc))
        self.assertEqual(local_date, "2026-09-30")
        self.assertEqual(start.isoformat(), "2026-09-29T22:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-09-30T22:00:00+00:00")

    def test_dst_days_keep_civil_midnights(self) -> None:
        spring_start, spring_end, _ = planning_day_window(datetime(2026, 3, 29, 12, tzinfo=timezone.utc))
        autumn_start, autumn_end, _ = planning_day_window(datetime(2026, 10, 25, 12, tzinfo=timezone.utc))
        self.assertEqual((spring_end - spring_start).total_seconds(), 23 * 3600)
        self.assertEqual((autumn_end - autumn_start).total_seconds(), 25 * 3600)

    def test_path_is_encoded_for_api(self) -> None:
        path, window = planning_day_path(datetime(2026, 9, 30, 10, tzinfo=timezone.utc))
        self.assertIn("from=2026-09-29T22%3A00%3A00.000Z", path)
        self.assertEqual(window["date"], "2026-09-30")

    def test_bookings_are_grouped_by_plan_and_cancelled_are_hidden(self) -> None:
        payload = {
            "planning": {
                "timezone": "Europe/Paris",
                "locations": [{"id": "loc", "name": "Brasserie"}],
                "resources": [
                    {"id": "room", "name": "Salle", "type": "brew_room"},
                    {"id": "fermenter", "name": "Fermenteur 1", "type": "fermenter"},
                ],
                "plans": [
                    {"id": "p1", "title": "Brassin test", "kind": "brew", "status": "confirmed", "locationId": "loc"},
                    {"id": "draft", "title": "Brouillon", "status": "draft"},
                ],
                "bookings": [
                    {"id": "b1", "planId": "p1", "resourceId": "room", "startAt": "2026-09-30T08:00:00Z", "endAt": "2026-09-30T12:00:00Z", "status": "confirmed", "phase": "brewing"},
                    {"id": "b2", "planId": "p1", "resourceId": "fermenter", "startAt": "2026-09-30T10:00:00Z", "endAt": "2026-10-07T10:00:00Z", "status": "confirmed", "phase": "fermentation"},
                    {"id": "b3", "planId": "draft", "resourceId": "room", "status": "cancelled"},
                ],
                "containerAllocations": [{"id": "a1"}],
            }
        }
        result = normalized_planning(payload)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["booking_count"], 2)
        self.assertEqual(result["container_allocations"], 1)
        self.assertEqual(result["events"][0]["resources"], ["Salle", "Fermenteur 1"])
        self.assertEqual(result["events"][0]["end"], "2026-10-07T10:00:00Z")


if __name__ == "__main__":
    unittest.main()
