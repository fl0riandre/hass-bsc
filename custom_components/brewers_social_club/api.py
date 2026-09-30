"""Asynchronous client for the BSC HTTP API.

The module intentionally avoids importing Home Assistant or aiohttp so its
normalization and error handling can be unit-tested with the Python standard
library. Home Assistant injects its shared aiohttp session at runtime.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .const import MODULE_ENDPOINTS


class BscApiError(Exception):
    """Base BSC API error."""


class BscApiAuthError(BscApiError):
    """Authentication or authorization failed."""


class BscApiConnectionError(BscApiError):
    """The BSC API could not be reached."""


@dataclass(slots=True)
class BscApiData:
    """One complete coordinator refresh."""

    modules: dict[str, dict[str, Any]]
    errors: dict[str, str]


def normalize_base_url(value: str) -> str:
    """Normalize and validate the configured API base URL."""

    url = str(value or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ValueError("The API URL must start with http:// or https://")
    return url


class BscApiClient:
    """Small BSC API client using Home Assistant's shared HTTP session."""

    def __init__(self, session: Any, base_url: str, api_key: str) -> None:
        self._session = session
        self.base_url = normalize_base_url(base_url)
        self._api_key = str(api_key or "").strip()

    @property
    def headers(self) -> dict[str, str]:
        """Return request headers without ever logging them."""

        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    async def async_get(self, path: str) -> dict[str, Any]:
        """Fetch one JSON endpoint."""

        url = f"{self.base_url}/{str(path).lstrip('/')}"
        try:
            async with asyncio.timeout(30):
                response = await self._session.get(url, headers=self.headers)
                async with response:
                    if response.status in (401, 403):
                        raise BscApiAuthError("BSC API key rejected")
                    if response.status >= 400:
                        raise BscApiError(f"BSC API returned HTTP {response.status}")
                    payload = await response.json(content_type=None)
        except (BscApiError, BscApiAuthError):
            raise
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise BscApiConnectionError("BSC API request timed out") from err
        except Exception as err:
            raise BscApiConnectionError("Unable to reach the BSC API") from err

        if not isinstance(payload, dict):
            raise BscApiError("BSC API returned an invalid JSON object")
        return payload

    async def async_validate(self) -> dict[str, Any]:
        """Validate connectivity and credentials."""

        await self.async_get("/health")
        return await self.async_get("/api/me")

    async def async_fetch_modules(
        self,
        modules: Iterable[str],
        endpoint_overrides: Mapping[str, str] | None = None,
    ) -> BscApiData:
        """Fetch enabled modules concurrently and isolate optional failures."""

        endpoints = {**MODULE_ENDPOINTS, **dict(endpoint_overrides or {})}
        selected = [module for module in modules if module in endpoints]
        results = await asyncio.gather(
            *(self.async_get(endpoints[module]) for module in selected),
            return_exceptions=True,
        )

        data: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        for module, result in zip(selected, results, strict=True):
            if isinstance(result, BscApiAuthError):
                raise result
            if isinstance(result, Exception):
                errors[module] = str(result)
                continue
            data[module] = result
        return BscApiData(modules=data, errors=errors)
