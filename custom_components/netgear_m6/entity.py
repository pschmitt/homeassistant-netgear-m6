"""Shared entity base for the Netgear Nighthawk M6."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import NetgearM6Coordinator, device_identifier


class NetgearM6Entity(CoordinatorEntity[NetgearM6Coordinator]):
    """Base entity tying every platform entity to the one device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NetgearM6Coordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        # Model, serial, firmware and MACs arrive with the first poll, which
        # runs in the background; the coordinator adds them to this device.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier(entry))},
            name=entry.title,
            manufacturer=MANUFACTURER,
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def available(self) -> bool:
        """Wait for the first successful background poll."""
        return super().available and self.coordinator.data is not None
