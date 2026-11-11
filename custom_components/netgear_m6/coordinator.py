"""Data update coordinator for the Netgear Nighthawk M6 integration."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import NetgearM6AuthError, NetgearM6Client, NetgearM6Error
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MANUFACTURER
from .models import NetgearM6Data
from .traffic import TrafficTracker

_LOGGER = logging.getLogger(__name__)

type NetgearM6ConfigEntry = ConfigEntry[NetgearM6Coordinator]


def device_identifier(entry: ConfigEntry) -> str:
    """Return the stable identifier of the device: its serial when known."""
    return entry.unique_id or entry.entry_id


class NetgearM6Coordinator(DataUpdateCoordinator[NetgearM6Data]):
    """Poll one Nighthawk M6."""

    config_entry: NetgearM6ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: NetgearM6ConfigEntry,
        client: NetgearM6Client,
        tracker: TrafficTracker,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            config_entry=entry,
        )
        self.client = client
        self.tracker = tracker

    async def _async_update_data(self) -> NetgearM6Data:
        try:
            model = await self.client.async_get_model()
        except NetgearM6AuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except NetgearM6Error as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err

        data = NetgearM6Data.from_model(model)
        self._update_device_registry(data)
        snapshot = self.tracker.update(
            data.session_rx, data.session_tx, data.session_start, dt_util.now()
        )
        return replace(data, traffic=snapshot)

    def _update_device_registry(self, data: NetgearM6Data) -> None:
        """Add what the device reports about itself to its registry entry."""
        entry = self.config_entry
        dr.async_get(self.hass).async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_identifier(entry))},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=data.model,
            serial_number=data.serial,
            sw_version=data.firmware,
            hw_version=data.hardware,
            connections={
                (dr.CONNECTION_NETWORK_MAC, dr.format_mac(mac))
                for mac in (data.wifi_mac, data.ethernet_mac)
                if mac
            },
        )

    async def async_apply(self, values: dict[str, str]) -> None:
        """Change settings on the device and refresh the state."""
        try:
            await self.client.async_set(values)
        except NetgearM6Error as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.async_refresh()
