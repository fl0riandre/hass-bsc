"""Config flow for Brewers Social Club."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BscApiAuthError, BscApiClient, BscApiError, normalize_base_url
from .const import (
    CONF_API_KEY,
    CONF_MODULES,
    CONF_SCAN_INTERVAL,
    DEFAULT_MODULES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MODULES,
)


class BscConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a BSC config flow."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                base_url = normalize_base_url(user_input[CONF_URL])
                client = BscApiClient(
                    async_get_clientsession(self.hass),
                    base_url,
                    user_input[CONF_API_KEY],
                )
                identity = await client.async_validate()
            except ValueError:
                errors[CONF_URL] = "invalid_url"
            except BscApiAuthError:
                errors[CONF_API_KEY] = "invalid_auth"
            except BscApiError:
                errors["base"] = "cannot_connect"
            else:
                key_id = str(identity.get("apiKey", {}).get("id") or "default")
                host = urlparse(base_url).netloc.lower()
                await self.async_set_unique_id(f"{host}:{key_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Brewers Social Club ({host})",
                    data={CONF_URL: base_url, CONF_API_KEY: user_input[CONF_API_KEY]},
                    options={
                        CONF_MODULES: DEFAULT_MODULES,
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=DEFAULT_URL): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
                vol.Required(CONF_API_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, _entry_data: dict[str, Any]) -> FlowResult:
        """Start reauthentication after an API key is rejected."""

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and replace a revoked API key."""

        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                client = BscApiClient(
                    async_get_clientsession(self.hass),
                    entry.data[CONF_URL],
                    user_input[CONF_API_KEY],
                )
                await client.async_validate()
            except BscApiAuthError:
                errors[CONF_API_KEY] = "invalid_auth"
            except BscApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> BscOptionsFlow:
        return BscOptionsFlow(config_entry)


class BscOptionsFlow(config_entries.OptionsFlow):
    """Handle BSC options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MODULES,
                        default=self._entry.options.get(CONF_MODULES, DEFAULT_MODULES),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=list(MODULES),
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key="modules",
                        )
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
                }
            ),
        )
