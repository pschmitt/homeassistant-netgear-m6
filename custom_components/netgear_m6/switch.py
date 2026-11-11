"""Netgear Nighthawk M6 switches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    AUTOCONNECT_ALWAYS,
    AUTOCONNECT_HOME,
    AUTOCONNECT_ROAMING,
)
from .coordinator import NetgearM6ConfigEntry, NetgearM6Coordinator
from .entity import NetgearM6Entity
from .models import NetgearM6Data

PARALLEL_UPDATES = 1

_DATA_ON = {AUTOCONNECT_HOME, AUTOCONNECT_ALWAYS}
_ROAMING_ON = {AUTOCONNECT_ROAMING, AUTOCONNECT_ALWAYS}


def _flag(value: bool) -> str:
    return "true" if value else "false"


@dataclass(frozen=True, kw_only=True)
class NetgearM6SwitchDescription(SwitchEntityDescription):
    """Describe a Nighthawk M6 switch.

    ``command_fn`` returns the web UI form fields that apply the new state.
    """

    is_on_fn: Callable[[NetgearM6Data], bool | None]
    command_fn: Callable[[NetgearM6Data, bool], dict[str, str]]


SWITCHES: tuple[NetgearM6SwitchDescription, ...] = (
    NetgearM6SwitchDescription(
        key="airplane_mode",
        is_on_fn=lambda d: d.airplane_mode,
        command_fn=lambda d, on: {"power.lpm": _flag(on)},
    ),
    # Both data switches post the same form, so each one passes the other's
    # current state along, like the web UI does.
    NetgearM6SwitchDescription(
        key="mobile_data",
        is_on_fn=lambda d: None if d.autoconnect is None else d.autoconnect in _DATA_ON,
        command_fn=lambda d, on: {
            "wwan.domesticdata": _flag(on),
            "wwan.intlroaming": _flag(d.autoconnect in _ROAMING_ON),
        },
    ),
    NetgearM6SwitchDescription(
        key="data_roaming",
        is_on_fn=lambda d: (
            None if d.autoconnect is None else d.autoconnect in _ROAMING_ON
        ),
        command_fn=lambda d, on: {
            "wwan.domesticdata": _flag(d.autoconnect in _DATA_ON),
            "wwan.intlroaming": _flag(on),
        },
    ),
    NetgearM6SwitchDescription(
        key="upnp",
        is_on_fn=lambda d: d.upnp,
        command_fn=lambda d, on: {"router.UPNPenabled": _flag(on)},
    ),
    NetgearM6SwitchDescription(
        key="vpn_passthrough",
        is_on_fn=lambda d: d.vpn_passthrough,
        command_fn=lambda d, on: {"router.VPNpassthrough": _flag(on)},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetgearM6ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nighthawk M6 switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        NetgearM6Switch(coordinator, description) for description in SWITCHES
    )


class NetgearM6Switch(NetgearM6Entity, SwitchEntity):
    """A setting that can be switched on the device."""

    entity_description: NetgearM6SwitchDescription

    def __init__(
        self,
        coordinator: NetgearM6Coordinator,
        description: NetgearM6SwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        data = self.coordinator.data
        return self.entity_description.is_on_fn(data) if data else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the setting on."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the setting off."""
        await self._async_set(False)

    async def _async_set(self, on: bool) -> None:
        await self.coordinator.async_apply(
            self.entity_description.command_fn(self.coordinator.data, on)
        )
