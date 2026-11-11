"""Netgear Nighthawk M6 selects."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import NetgearM6ConfigEntry, NetgearM6Coordinator
from .entity import NetgearM6Entity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetgearM6ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nighthawk M6 selects."""
    async_add_entities([NetgearM6PowerModeSelect(entry.runtime_data)])


class NetgearM6PowerModeSelect(NetgearM6Entity, SelectEntity):
    """Choose the power profile (Balanced, Performance, Plugged in, ...)."""

    def __init__(self, coordinator: NetgearM6Coordinator) -> None:
        super().__init__(coordinator, "power_mode")

    @property
    def options(self) -> list[str]:
        """Return the profile labels the device offers."""
        data = self.coordinator.data
        return list(data.power_profiles.values()) if data else []

    @property
    def current_option(self) -> str | None:
        """Return the active profile label."""
        data = self.coordinator.data
        profile = data.effective_power_profile if data else None
        return data.power_profiles.get(profile) if data and profile else None

    async def async_select_option(self, option: str) -> None:
        """Activate a profile."""
        data = self.coordinator.data
        if option == self.current_option:
            return
        if not data.has_battery:
            # Without a battery the device always runs the plugged-in profile;
            # the stored choice would only apply once a battery is fitted.
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="power_mode_plugged_in"
            )
        profiles = data.power_profiles
        profile_id = next((i for i, label in profiles.items() if label == option), None)
        if profile_id is None:
            raise ValueError(option)
        await self.coordinator.async_apply({"powermanager.profile": profile_id})
