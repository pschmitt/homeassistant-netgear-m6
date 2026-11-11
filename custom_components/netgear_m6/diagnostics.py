"""Diagnostics for the Netgear Nighthawk M6."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import NetgearM6ConfigEntry

TO_REDACT = {
    CONF_HOST,
    CONF_PASSWORD,
    "unique_id",
    "serial",
    "wan_ip",
    "imei",
    "iccid",
    "imsi",
    "phone_number",
    "wifi_mac",
    "ethernet_mac",
    "wifi_ssid",
    "cell_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: NetgearM6ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(
            {**entry.data, "unique_id": entry.unique_id}, TO_REDACT
        ),
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "data": (
            async_redact_data(asdict(coordinator.data), TO_REDACT)
            if coordinator.data
            else None
        ),
    }
