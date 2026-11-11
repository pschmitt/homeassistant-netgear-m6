"""Tests for the entity platforms."""

from __future__ import annotations

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import get_state
from .fake_device import FakeM6

P = "netgear_nighthawk_m6"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)


async def _call(hass: HomeAssistant, domain: str, service: str, **data) -> None:
    await hass.services.async_call(domain, service, data, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_signal_and_network_sensors(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)

    assert get_state(hass, f"sensor.{P}_signal_bars").state == "4"
    assert get_state(hass, f"sensor.{P}_lte_rsrp").state == "-102"
    assert get_state(hass, f"sensor.{P}_5g_rsrp").state == "-94"
    assert get_state(hass, f"sensor.{P}_5g_sinr").state == "18"
    assert get_state(hass, f"sensor.{P}_network_type").state == "5G"
    assert get_state(hass, f"sensor.{P}_operator").state == "Test Telecom"
    assert get_state(hass, f"sensor.{P}_lte_bands").state == "B3, B1"
    assert get_state(hass, f"sensor.{P}_5g_bands").state == "n78"
    assert get_state(hass, f"sensor.{P}_connected_clients").state == "2"
    assert get_state(hass, f"sensor.{P}_temperature").state == "53"
    assert get_state(hass, f"sensor.{P}_sim_status").state == "Ready"
    assert get_state(hass, f"sensor.{P}_active_uplink").state == "LTE"


async def test_traffic_sensors_start_at_zero_and_grow(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)
    today = get_state(hass, f"sensor.{P}_traffic_today")
    assert today.state == "0.0"
    assert today.attributes["unit_of_measurement"] == "GiB"
    assert today.attributes["state_class"] == "total"
    assert "last_reset" in today.attributes


async def test_disabled_by_default_diagnostics(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    """Identifiers stay hidden until the user enables them."""
    await _setup(hass, mock_entry)
    for key in ("imei", "imei_sv", "iccid", "imsi", "phone_number"):
        assert hass.states.get(f"sensor.{P}_{key}") is None


async def test_battery_entities_skipped_without_battery(
    hass: HomeAssistant, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)
    assert hass.states.get(f"sensor.{P}_battery") is None


async def test_binary_sensors(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    await _setup(hass, mock_entry)

    assert (
        get_state(hass, f"binary_sensor.{P}_mobile_data_connection").state == STATE_ON
    )
    assert get_state(hass, f"binary_sensor.{P}_roaming").state == STATE_OFF
    assert get_state(hass, f"binary_sensor.{P}_failover").state == STATE_ON
    assert get_state(hass, f"binary_sensor.{P}_wi_fi").state == STATE_ON


@pytest.mark.parametrize(
    ("entity", "path", "initial"),
    [
        ("airplane_mode", ("power", "lpm"), False),
        ("upnp", ("router", "UPNPenabled"), True),
        ("vpn_passthrough", ("router", "VPNpassthrough"), True),
    ],
)
async def test_simple_switches(
    hass: HomeAssistant,
    device: FakeM6,
    mock_entry: MockConfigEntry,
    entity: str,
    path: tuple[str, str],
    initial: bool,
) -> None:
    await _setup(hass, mock_entry)
    entity_id = f"switch.{P}_{entity}"
    assert get_state(hass, entity_id).state == (STATE_ON if initial else STATE_OFF)

    service = SERVICE_TURN_OFF if initial else SERVICE_TURN_ON
    await _call(hass, SWITCH_DOMAIN, service, **{ATTR_ENTITY_ID: entity_id})

    assert device.model[path[0]][path[1]] is (not initial)
    assert get_state(hass, entity_id).state == (STATE_OFF if initial else STATE_ON)


async def test_data_switches_keep_each_other(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    """Mobile data and roaming share one form, so changing one keeps the other."""
    await _setup(hass, mock_entry)
    assert get_state(hass, f"switch.{P}_mobile_data").state == STATE_ON
    assert get_state(hass, f"switch.{P}_data_roaming").state == STATE_OFF

    await _call(
        hass,
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        **{ATTR_ENTITY_ID: f"switch.{P}_data_roaming"},
    )
    assert device.model["wwan"]["autoconnect"] == "Always"

    await _call(
        hass,
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        **{ATTR_ENTITY_ID: f"switch.{P}_mobile_data"},
    )
    assert device.model["wwan"]["autoconnect"] == "RoamNetwork"
    assert get_state(hass, f"switch.{P}_mobile_data").state == STATE_OFF
    assert get_state(hass, f"switch.{P}_data_roaming").state == STATE_ON


async def test_power_mode_without_battery_is_plugged_in(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    """No battery means the plugged-in profile, whatever the stored choice is."""
    await _setup(hass, mock_entry)
    entity_id = f"select.{P}_power_mode"
    state = get_state(hass, entity_id)
    assert state.state == "Plugged in"
    assert state.attributes[ATTR_OPTIONS] == ["Balanced", "Performance", "Plugged in"]

    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            **{ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "Performance"},
        )
    assert device.model["power"]["profileCurrent"] == "0"


async def test_power_mode_select_with_battery(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    device.model["power"].update({"batteryState": "Discharging", "battChargeLevel": 80})
    await _setup(hass, mock_entry)
    entity_id = f"select.{P}_power_mode"
    assert get_state(hass, entity_id).state == "Balanced"

    await _call(
        hass,
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        **{ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "Performance"},
    )
    assert device.model["power"]["profileCurrent"] == "1"
    assert get_state(hass, entity_id).state == "Performance"


async def test_restart_button(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)

    await _call(
        hass, BUTTON_DOMAIN, SERVICE_PRESS, **{ATTR_ENTITY_ID: f"button.{P}_restart"}
    )
    assert device.reboots == 1


async def test_refused_change_raises(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_entry)
    device.model["power"]["lpm"] = False
    device.fail_requests = True

    with pytest.raises(HomeAssistantError):
        await _call(
            hass,
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            **{ATTR_ENTITY_ID: f"switch.{P}_airplane_mode"},
        )
