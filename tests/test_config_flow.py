"""Tests for the config, reauth, reconfigure and options flows."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.netgear_m6.const import CONF_SCAN_INTERVAL, DOMAIN

from .fake_device import PASSWORD, FakeM6


async def _start(hass: HomeAssistant, host: str, password: str):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: host, CONF_PASSWORD: password}
    )


async def test_user_flow_creates_entry(hass: HomeAssistant, device: FakeM6) -> None:
    result = await _start(hass, device.host, PASSWORD)

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Netgear Nighthawk M6"
    assert result.get("data") == {CONF_HOST: device.host, CONF_PASSWORD: PASSWORD}
    entry = result.get("result")
    assert entry is not None
    assert entry.unique_id == "FSN0000000001"


async def test_user_flow_invalid_auth_then_recovers(
    hass: HomeAssistant, device: FakeM6
) -> None:
    result = await _start(hass, device.host, "wrong")
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: device.host, CONF_PASSWORD: PASSWORD}
    )
    assert result.get("type") is FlowResultType.CREATE_ENTRY


async def test_user_flow_cannot_connect_offers_offline_save(
    hass: HomeAssistant, socket_enabled: None
) -> None:
    result = await _start(hass, "127.0.0.1:1", PASSWORD)
    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {"base": "cannot_connect"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "127.0.0.1:1", CONF_PASSWORD: PASSWORD, "save_offline": True},
    )
    assert result.get("type") is FlowResultType.CREATE_ENTRY
    entry = result.get("result")
    assert entry is not None
    assert entry.unique_id == "127.0.0.1:1"


async def test_user_flow_already_configured(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)

    result = await _start(hass, device.host, PASSWORD)

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_reauth_flow(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    device.password = "rotated"

    result = await mock_entry.start_reauth_flow(hass)
    assert result.get("step_id") == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "still-wrong"}
    )
    assert result.get("errors") == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "rotated"}
    )
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reauth_successful"
    assert mock_entry.data[CONF_PASSWORD] == "rotated"


async def test_reconfigure_flow(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    mock_entry.add_to_hass(hass)
    device.password = "new-pw"

    result = await mock_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: device.host, CONF_PASSWORD: "new-pw"}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"
    assert mock_entry.data[CONF_PASSWORD] == "new-pw"


async def test_reconfigure_rejects_a_different_device(
    hass: HomeAssistant, device: FakeM6, mock_entry: MockConfigEntry
) -> None:
    device.model["general"]["FSN"] = "FSN-OTHER"
    mock_entry.add_to_hass(hass)

    result = await mock_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: device.host, CONF_PASSWORD: PASSWORD}
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "wrong_device"


async def test_options_flow(hass: HomeAssistant, mock_entry: MockConfigEntry) -> None:
    mock_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 120}
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert mock_entry.options == {CONF_SCAN_INTERVAL: 120}
