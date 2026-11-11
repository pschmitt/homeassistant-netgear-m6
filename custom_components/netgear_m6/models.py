"""Typed view of the device document."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import INVALID_SIGNAL

NO_BATTERY = "NoBattery"


def _int(value: Any) -> int | None:
    """Return ``value`` as an int, or None when it is missing or not numeric."""
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _signal(value: Any) -> int | None:
    """Return a signal reading, treating the firmware's sentinel as missing."""
    number = _int(value)
    return None if number is None or number == INVALID_SIGNAL else number


def _bands(entries: Any) -> list[int]:
    """Return the active band numbers, primary carrier first."""
    if not isinstance(entries, list):
        return []
    found = [e for e in entries if isinstance(e, dict) and _int(e.get("band"))]
    found.sort(key=lambda e: not e.get("isPcc"))
    return [band for e in found if (band := _int(e.get("band"))) is not None]


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


AC_PROFILE_NAME = "ACPowered"


def _ac_profile(entries: Any) -> str | None:
    """Return the id of the profile the device uses when plugged in."""
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == AC_PROFILE_NAME:
            return str(entry["id"]) if entry.get("id") is not None else None
    return None


def _profiles(entries: Any) -> dict[str, str]:
    """Return the power profiles as ``{id: label}``."""
    if not isinstance(entries, list):
        return {}
    return {
        str(e["id"]): str(e.get("label") or e.get("name") or e["id"])
        for e in entries
        if isinstance(e, dict) and e.get("id") is not None
    }


@dataclass(frozen=True, slots=True)
class TrafficSnapshot:
    """Accumulated traffic in bytes, kept across modem sessions."""

    total_rx: int = 0
    total_tx: int = 0
    day_rx: int = 0
    day_tx: int = 0
    day_start: str | None = None
    month_rx: int = 0
    month_tx: int = 0
    month_start: str | None = None


@dataclass(frozen=True, slots=True)
class NetgearM6Data:
    """Everything the integration shows, parsed from one poll."""

    serial: str | None
    model: str | None
    firmware: str | None
    hardware: str | None
    modem_firmware: str | None
    uptime: int | None
    temperature: int | None

    connection: str | None
    network_type: str | None
    operator: str | None
    roaming: str | None
    thermal_state: str | None
    wan_ip: str | None
    session_start: int | None
    session_duration: int | None
    session_rx: int | None
    session_tx: int | None

    signal_bars: int | None
    rssi: int | None
    rsrp: int | None
    rsrq: int | None
    sinr: int | None
    nr_rsrp: int | None
    nr_rsrq: int | None
    nr_sinr: int | None
    lte_bands: list[int]
    nr_bands: list[int]

    clients: int
    ethernet_speed: str | None

    has_battery: bool
    battery_level: int | None
    battery_state: str | None
    battery_temperature: int | None

    imei: str | None
    imei_sv: str | None
    iccid: str | None
    imsi: str | None
    phone_number: str | None
    sim_status: str | None
    sim_pin_mode: str | None
    cell_id: int | None
    plmn: str | None
    wifi_mac: str | None
    ethernet_mac: str | None
    wifi_ssid: str | None
    wifi_enabled: bool | None
    wifi_clients: int | None

    failover_enabled: bool | None
    failover_backhaul: str | None
    failover_wan_connected: bool | None

    airplane_mode: bool | None
    autoconnect: str | None
    upnp: bool | None
    vpn_passthrough: bool | None
    power_profile: str | None
    power_profiles: dict[str, str]
    power_profile_ac: str | None

    traffic: TrafficSnapshot = field(default_factory=TrafficSnapshot)

    @property
    def effective_power_profile(self) -> str | None:
        """Return the active profile id.

        ``power.profileCurrent`` only holds the profile used on battery. A device
        without a battery always runs the plugged-in profile, which is what the
        web interface shows too.
        """
        if not self.has_battery and self.power_profile_ac is not None:
            return self.power_profile_ac
        return self.power_profile

    @property
    def connected(self) -> bool:
        """Return True while the modem has a data session."""
        return self.connection == "Connected"

    @classmethod
    def from_model(cls, model: dict[str, Any]) -> NetgearM6Data:
        """Parse the device document, tolerating missing sections."""
        general = _section(model, "general")
        wwan = _section(model, "wwan")
        power = _section(model, "power")
        router = _section(model, "router")
        signal = _section(wwan, "signalStrength")
        ethernet = _section(model, "ethernet")
        sim = _section(model, "sim")
        wifi = _section(model, "wifi")
        failover = _section(model, "failover")
        wwanadv = _section(model, "wwanadv")

        clients = router.get("clientList")
        battery_state = _text(power.get("batteryState"))
        has_battery = battery_state is not None and battery_state != NO_BATTERY
        temperature = _int(general.get("devTemperature"))

        return cls(
            serial=_text(general.get("FSN")),
            model=_text(general.get("model")),
            firmware=_text(general.get("FWversion")),
            hardware=_text(general.get("HWversion")),
            modem_firmware=_text(general.get("modemFwVersion")),
            uptime=_int(general.get("upTime")),
            temperature=temperature,
            connection=_text(wwan.get("connection")),
            network_type=_text(wwan.get("connectionText")),
            operator=_text(wwan.get("registerNetworkDisplay")),
            roaming=_text(wwan.get("roamingType")),
            thermal_state=_text(wwan.get("thermalState")),
            wan_ip=_text(wwan.get("IP")),
            session_start=_int(wwan.get("sessStartTime")),
            session_duration=_int(wwan.get("sessDuration")),
            session_rx=_int(wwan.get("dataTransferredRx")),
            session_tx=_int(wwan.get("dataTransferredTx")),
            signal_bars=_int(signal.get("bars")),
            rssi=_signal(signal.get("rssi")),
            rsrp=_signal(signal.get("rsrp")),
            rsrq=_signal(signal.get("rsrq")),
            sinr=_signal(signal.get("sinr")),
            nr_rsrp=_signal(signal.get("nr5gRsrp")),
            nr_rsrq=_signal(signal.get("nr5gRsrq")),
            nr_sinr=_signal(signal.get("nr5gSinr")),
            lte_bands=_bands(wwan.get("lteBandInfo")),
            nr_bands=_bands(wwan.get("nr5gBandInfo")),
            clients=(
                sum(1 for c in clients if isinstance(c, dict) and c.get("IP"))
                if isinstance(clients, list)
                else 0
            ),
            ethernet_speed=_text(ethernet.get("speedMax")),
            imei=_text(general.get("IMEI")),
            imei_sv=_text(
                str(general["SVN"]) if general.get("SVN") is not None else None
            ),
            iccid=_text(sim.get("iccid")),
            imsi=_text(sim.get("imsi")),
            phone_number=_text(sim.get("phoneNumber")),
            sim_status=_text(sim.get("status")),
            sim_pin_mode=_text(_section(sim, "pin").get("mode")),
            cell_id=_int(wwanadv.get("cellId")),
            plmn=(
                f"{wwanadv['MCC']}-{wwanadv['MNC']}"
                if _text(wwanadv.get("MCC")) and _text(wwanadv.get("MNC"))
                else None
            ),
            wifi_mac=_text(wifi.get("MAC")),
            ethernet_mac=_text(ethernet.get("mac")),
            wifi_ssid=_text(wifi.get("SSID")),
            wifi_enabled=_bool(wifi.get("enabled")),
            wifi_clients=_int(wifi.get("clientCount")),
            failover_enabled=_bool(failover.get("enabled")),
            failover_backhaul=_text(failover.get("backhaul")),
            failover_wan_connected=_bool(failover.get("wanConnected")),
            airplane_mode=_bool(power.get("lpm")),
            autoconnect=_text(wwan.get("autoconnect")),
            upnp=_bool(router.get("UPNPenabled")),
            vpn_passthrough=_bool(router.get("VPNpassthrough")),
            power_profile=_text(power.get("profileCurrent")),
            power_profiles=_profiles(power.get("profileList")),
            power_profile_ac=_ac_profile(power.get("profileList")),
            has_battery=has_battery,
            battery_level=_int(power.get("battChargeLevel")) if has_battery else None,
            battery_state=battery_state if has_battery else None,
            battery_temperature=(
                _int(power.get("batteryTemperature")) if has_battery else None
            ),
        )


def _section(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    return value if isinstance(value, dict) else {}
