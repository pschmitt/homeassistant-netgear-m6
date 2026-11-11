"""Tests for parsing the device document."""

from __future__ import annotations

from custom_components.netgear_m6.models import NetgearM6Data

from .fake_device import base_model


def test_parses_a_full_document() -> None:
    """Every field of a healthy 5G session is read."""
    data = NetgearM6Data.from_model(base_model())

    assert data.serial == "FSN0000000001"
    assert data.model == "MR6450"
    assert data.connected is True
    assert data.network_type == "5G"
    assert data.operator == "Test Telecom"
    assert (data.rsrp, data.rsrq, data.sinr) == (-102, -16, 5)
    assert (data.nr_rsrp, data.nr_rsrq, data.nr_sinr) == (-94, -11, 18)
    assert data.session_rx == 2147483648
    assert data.session_tx == 1073741824
    assert data.clients == 2
    assert data.plmn == "262-07"
    assert data.cell_id == 1234567
    assert data.iccid == "8949000000000000001"
    assert data.imei_sv == "19"
    assert data.wifi_mac == "AA:BB:CC:00:00:01"
    assert data.ethernet_mac == "AA:BB:CC:00:00:02"
    assert data.failover_backhaul == "LTE"
    assert data.power_profiles == {
        "0": "Balanced",
        "1": "Performance",
        "2": "Plugged in",
    }


def test_invalid_signal_sentinel_is_missing() -> None:
    """The firmware's -32768 marker means there is no reading."""
    model = base_model()
    model["wwan"]["signalStrength"]["rsrp"] = -32768
    assert NetgearM6Data.from_model(model).rsrp is None


def test_bands_list_the_primary_carrier_first() -> None:
    """Empty band slots are dropped and the primary carrier leads."""
    data = NetgearM6Data.from_model(base_model())
    assert data.lte_bands == [3, 1]
    assert data.nr_bands == [78]


def test_no_battery() -> None:
    """A device without a battery hides the battery values."""
    data = NetgearM6Data.from_model(base_model())
    assert data.has_battery is False
    assert data.battery_level is None


def test_battery_present() -> None:
    """A device with a battery reports its level."""
    model = base_model()
    model["power"].update({"batteryState": "Discharging", "battChargeLevel": 80})
    data = NetgearM6Data.from_model(model)
    assert data.has_battery is True
    assert data.battery_level == 80


def test_tolerates_a_guest_document() -> None:
    """An unauthenticated document has no sections and still parses."""
    data = NetgearM6Data.from_model({"session": {"userRole": "Guest"}})
    assert data.connected is False
    assert data.clients == 0
    assert data.power_profiles == {}
    assert data.plmn is None


def test_effective_power_profile_without_battery() -> None:
    """A device without a battery always runs the plugged-in profile."""
    data = NetgearM6Data.from_model(base_model())
    assert data.power_profile == "0"
    assert data.effective_power_profile == "2"


def test_effective_power_profile_with_battery() -> None:
    """With a battery the stored profile applies."""
    model = base_model()
    model["power"]["batteryState"] = "Discharging"
    assert NetgearM6Data.from_model(model).effective_power_profile == "0"
