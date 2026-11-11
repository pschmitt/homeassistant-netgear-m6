"""Config flow for the Netgear Nighthawk M6."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import (
    NetgearM6AuthError,
    NetgearM6Client,
    NetgearM6Error,
    create_session,
)
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TITLE,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .models import NetgearM6Data

CONF_SAVE_OFFLINE = "save_offline"

_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _schema(host: str | None = None, *, with_host: bool = True) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_host:
        fields[vol.Required(CONF_HOST, default=host or DEFAULT_HOST)] = TextSelector()
    fields[vol.Required(CONF_PASSWORD)] = _PASSWORD
    return vol.Schema(fields)


async def _async_validate(
    host: str, password: str
) -> tuple[NetgearM6Data | None, str | None]:
    """Try a login and return the parsed device document or an error key."""
    async with create_session() as session:
        try:
            model = await NetgearM6Client(session, host, password).async_login()
        except NetgearM6AuthError:
            return None, "invalid_auth"
        except NetgearM6Error:
            return None, "cannot_connect"
    return NetgearM6Data.from_model(model), None


class NetgearM6ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Nighthawk M6."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().lower()
            data: NetgearM6Data | None = None
            error = None
            if not user_input.get(CONF_SAVE_OFFLINE):
                data, error = await _async_validate(host, user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(data.serial if data else None or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={CONF_HOST: host, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        schema = _schema()
        if errors.get("base") == "cannot_connect":
            # Let the user save the entry for a device that is not online yet.
            schema = schema.extend(
                {vol.Optional(CONF_SAVE_OFFLINE, default=False): bool}
            )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the device rejected the password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new admin password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            _, error = await _async_validate(
                entry.data[CONF_HOST], user_input[CONF_PASSWORD]
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_schema(with_host=False),
            description_placeholders={"host": entry.data[CONF_HOST]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change host and/or password of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().lower()
            data, error = await _async_validate(host, user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                if data and data.serial and entry.unique_id != data.serial:
                    return self.async_abort(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(entry.data[CONF_HOST]),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return NetgearM6OptionsFlow()


class NetgearM6OptionsFlow(OptionsFlow):
    """Adjust the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
