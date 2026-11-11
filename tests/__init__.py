"""Tests for the Netgear Nighthawk M6 integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, State


def get_state(hass: HomeAssistant, entity_id: str) -> State:
    """Return an entity's state, failing loudly when it does not exist."""
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} does not exist"
    return state
