"""Netgear Nighthawk M6 buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import NetgearM6Error
from .const import DOMAIN
from .coordinator import NetgearM6ConfigEntry, NetgearM6Coordinator
from .entity import NetgearM6Entity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetgearM6ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nighthawk M6 buttons."""
    async_add_entities([NetgearM6RestartButton(entry.runtime_data)])


class NetgearM6RestartButton(NetgearM6Entity, ButtonEntity):
    """Reboot the device."""

    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, coordinator: NetgearM6Coordinator) -> None:
        super().__init__(coordinator, "restart")

    async def async_press(self) -> None:
        """Reboot the device."""
        try:
            await self.coordinator.client.async_reboot()
        except NetgearM6Error as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="restart_failed",
                translation_placeholders={"error": str(err)},
            ) from err
