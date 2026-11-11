"""Tests for setup, unload, availability, device info and diagnostics."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.netgear_m6.const import DEFAULT_SCAN_INTERVAL, DOMAIN

from . import get_state
from .fake_device import FakeM6

SIGNAL = "sensor.netgear_nighthawk_m6_signal_bars"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Advance past one polling interval and let the coordinator refresh."""
    freezer.tick(timedelta(seconds=DEFAULT_SCAN_INTERVAL + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_setup_and_unload(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)
    assert mock_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_entry.entry_id)
    assert mock_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_does_not_wait_for_the_device(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    """An unreachable device must not block setup."""
    device.fail_requests = True
    await _setup(hass, mock_entry)

    assert mock_entry.state is ConfigEntryState.LOADED
    assert get_state(hass, SIGNAL).state == STATE_UNAVAILABLE


async def test_recovers_when_the_device_comes_back(
    hass: HomeAssistant,
    device: FakeM6,
    mock_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    device.fail_requests = True
    await _setup(hass, mock_entry)

    device.fail_requests = False
    await _poll(hass, freezer)
    assert get_state(hass, SIGNAL).state == "4"


async def test_bad_password_starts_reauth(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    device.password = "rotated"
    await _setup(hass, mock_entry)

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any((flow.get("context") or {}).get("source") == "reauth" for flow in flows)


async def test_device_registry_metadata(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)

    registry = dr.async_get(hass)
    device_entry = registry.async_get_device_by_identifier(
        (DOMAIN, "FSN0000000001"), mock_entry.entry_id
    )
    assert device_entry is not None
    assert device_entry.manufacturer == "Netgear"
    assert device_entry.model == "MR6450"
    assert device_entry.serial_number == "FSN0000000001"
    assert device_entry.sw_version == "NTGX65_12.01.74.00"
    assert device_entry.hw_version == "1.0"
    assert {c[1] for c in device_entry.connections} == {
        "aa:bb:cc:00:00:01",
        "aa:bb:cc:00:00:02",
    }


async def test_diagnostics_redact_identifiers(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_entry: MockConfigEntry,
) -> None:
    await _setup(hass, mock_entry)

    diagnostics = cast(
        dict[str, Any],
        await get_diagnostics_for_config_entry(hass, hass_client, mock_entry),
    )

    assert diagnostics["entry"]["password"] == "**REDACTED**"
    assert diagnostics["entry"]["host"] == "**REDACTED**"
    data = diagnostics["data"]
    for key in ("serial", "imei", "iccid", "imsi", "phone_number", "wifi_mac"):
        assert data[key] == "**REDACTED**"
    assert data["signal_bars"] == 4
