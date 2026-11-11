"""Home Assistant integration for the Netgear Nighthawk M6 5G/LTE hotspot."""

from __future__ import annotations

import aiohttp
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .client import NetgearM6Client
from .coordinator import NetgearM6ConfigEntry, NetgearM6Coordinator
from .traffic import TrafficTracker

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: NetgearM6ConfigEntry) -> bool:
    """Set up a Nighthawk M6 from a config entry."""
    # The device keeps its login in a cookie, which the shared session drops.

    session = async_create_clientsession(
        hass, cookie_jar=aiohttp.CookieJar(unsafe=True)
    )
    client = NetgearM6Client(session, entry.data[CONF_HOST], entry.data[CONF_PASSWORD])
    tracker = TrafficTracker(hass, entry.entry_id)
    await tracker.async_load()
    coordinator = NetgearM6Coordinator(hass, entry, client, tracker)

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Never block startup on the device: poll in the background and let the
    # entities wait for the first result.
    entry.async_create_background_task(
        hass, coordinator.async_refresh(), "netgear_m6_first_refresh"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NetgearM6ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: NetgearM6ConfigEntry) -> None:
    """Delete the stored traffic totals of a removed entry."""
    await TrafficTracker(hass, entry.entry_id).async_remove()


async def _async_reload_on_update(
    hass: HomeAssistant, entry: NetgearM6ConfigEntry
) -> None:
    """Reload when options or credentials change."""
    await hass.config_entries.async_reload(entry.entry_id)
