"""Netgear Nighthawk M6 binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import NetgearM6ConfigEntry, NetgearM6Coordinator
from .entity import NetgearM6Entity
from .models import NetgearM6Data

PARALLEL_UPDATES = 0

HOME_NETWORK = "Home"


@dataclass(frozen=True, kw_only=True)
class NetgearM6BinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Nighthawk M6 binary sensor."""

    value_fn: Callable[[NetgearM6Data], bool | None]


BINARY_SENSORS: tuple[NetgearM6BinarySensorDescription, ...] = (
    NetgearM6BinarySensorDescription(
        key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: d.connected,
    ),
    NetgearM6BinarySensorDescription(
        key="wan_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.failover_wan_connected,
    ),
    NetgearM6BinarySensorDescription(
        key="failover",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.failover_enabled,
    ),
    NetgearM6BinarySensorDescription(
        key="wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.wifi_enabled,
    ),
    NetgearM6BinarySensorDescription(
        key="roaming",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: None if d.roaming is None else d.roaming != HOME_NETWORK,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetgearM6ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nighthawk M6 binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        NetgearM6BinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class NetgearM6BinarySensor(NetgearM6Entity, BinarySensorEntity):
    """A boolean read from the device."""

    entity_description: NetgearM6BinarySensorDescription

    def __init__(
        self,
        coordinator: NetgearM6Coordinator,
        description: NetgearM6BinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        data = self.coordinator.data
        return self.entity_description.value_fn(data) if data else None
