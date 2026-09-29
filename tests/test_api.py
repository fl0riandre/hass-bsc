"""Tests for the dependency-free BSC API client."""

from __future__ import annotations

import asyncio
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
for module_name in ("const", "api"):
    spec = importlib.util.spec_from_file_location(
        f"brewers_social_club.{module_name}", PACKAGE / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

from brewers_social_club.api import (  # noqa: E402
    BscApiAuthError,
    BscApiClient,
    normalize_base_url,
)


class FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def json(self, **_kwargs):
        return self._payload


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, headers: dict[str, str]):
        self.requests.append((url, headers))
        return self.responses[url]


class ApiClientTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_base_url(self) -> None:
        self.assertEqual(normalize_base_url(" https://api.example.test/// "), "https://api.example.test")
        with self.assertRaises(ValueError):
            normalize_base_url("api.example.test")

    async def test_validate_uses_bearer_header(self) -> None:
        session = FakeSession(
            {
                "https://api.example.test/health": FakeResponse(200, {"success": True}),
                "https://api.example.test/api/me": FakeResponse(200, {"apiKey": {"id": "ha"}}),
            }
        )
        client = BscApiClient(session, "https://api.example.test", "bsc_api_secret")
        identity = await client.async_validate()
        self.assertEqual(identity["apiKey"]["id"], "ha")
        self.assertEqual(session.requests[0][1]["Authorization"], "Bearer bsc_api_secret")

    async def test_auth_error_is_raised(self) -> None:
        session = FakeSession(
            {"https://api.example.test/api/me": FakeResponse(401, {"success": False})}
        )
        client = BscApiClient(session, "https://api.example.test", "bad")
        with self.assertRaises(BscApiAuthError):
            await client.async_get("/api/me")

    async def test_partial_module_failure_is_isolated(self) -> None:
        session = FakeSession(
            {
                "https://api.example.test/api/admin/overview": FakeResponse(
                    200, {"success": True, "overview": {"totalMembers": 12}}
                ),
                "https://api.example.test/api/admin/partners": FakeResponse(502, {}),
            }
        )
        client = BscApiClient(session, "https://api.example.test", "key")
        result = await client.async_fetch_modules(["overview", "partners"])
        self.assertEqual(result.modules["overview"]["overview"]["totalMembers"], 12)
        self.assertIn("partners", result.errors)


if __name__ == "__main__":
    unittest.main()

