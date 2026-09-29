"""Tests for BSC payload normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
DATA_FILE = ROOT / "custom_components" / "brewers_social_club" / "data.py"
spec = importlib.util.spec_from_file_location("bsc_data", DATA_FILE)
data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data)


class DataNormalizationTests(unittest.TestCase):
    def test_archived_batches_are_hidden_case_insensitively(self) -> None:
        batches = [
            {"id": "1", "status": "Fermenting"},
            {"id": "2", "status": "Archived"},
            {"id": "3", "status": "archived"},
        ]
        self.assertEqual([item["id"] for item in data.active_items(batches)], ["1"])

    def test_items_discards_non_dictionary_values(self) -> None:
        payload = {"rapt": {"controllers": [{"id": "ok"}, None, "bad"]}}
        self.assertEqual(data.items(payload, "rapt", "controllers"), [{"id": "ok"}])

    def test_first_number_supports_nested_telemetry(self) -> None:
        payload = {"temperature": "bad", "latestTelemetry": {"temperature": "19.75"}}
        self.assertEqual(
            data.first_number(payload, (("temperature",), ("latestTelemetry", "temperature"))),
            19.75,
        )

    def test_connectivity_normalization(self) -> None:
        self.assertTrue(data.controller_connected({"isConnected": True}))
        self.assertTrue(data.controller_connected({"status": "ONLINE"}))
        self.assertFalse(data.controller_connected({"status": "offline"}))


if __name__ == "__main__":
    unittest.main()

