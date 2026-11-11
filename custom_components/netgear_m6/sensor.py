"""Netgear Nighthawk M6 sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import NetgearM6ConfigEntry, NetgearM6Coordinator
from .entity import NetgearM6Entity
from .models import NetgearM6Data

PARALLEL_UPDATES = 0

type Value = int | float | str | None


@dataclass(frozen=True, kw_only=True)
class NetgearM6SensorDescription(SensorEntityDescription):
    """Describe a Nighthawk M6 sensor."""

    value_fn: Callable[[NetgearM6Data], Value]
    last_reset_fn: Callable[[NetgearM6Data], str | None] | None = None
    requires_battery: bool = False


def _traffic(
    key: str,
    value_fn: Callable[[NetgearM6Data], int],
    *,
    reset: Callable[[NetgearM6Data], str | None] | None = None,
) -> NetgearM6SensorDescription:
    """Describe a traffic counter in bytes, shown in GiB."""
    return NetgearM6SensorDescription(
        key=key,
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        suggested_display_precision=2,
        state_class=(
            SensorStateClass.TOTAL if reset else SensorStateClass.TOTAL_INCREASING
        ),
        value_fn=value_fn,
        last_reset_fn=reset,
    )


def _day(data: NetgearM6Data) -> str | None:
    return data.traffic.day_start


def _month(data: NetgearM6Data) -> str | None:
    return data.traffic.month_start


def _bands(bands: list[int], prefix: str) -> str | None:
    return ", ".join(f"{prefix}{band}" for band in bands) or None


SENSORS: tuple[NetgearM6SensorDescription, ...] = (
    _traffic("download_today", lambda d: d.traffic.day_rx, reset=_day),
    _traffic("upload_today", lambda d: d.traffic.day_tx, reset=_day),
    _traffic(
        "traffic_today", lambda d: d.traffic.day_rx + d.traffic.day_tx, reset=_day
    ),
    _traffic("download_month", lambda d: d.traffic.month_rx, reset=_month),
    _traffic("upload_month", lambda d: d.traffic.month_tx, reset=_month),
    _traffic(
        "traffic_month",
        lambda d: d.traffic.month_rx + d.traffic.month_tx,
        reset=_month,
    ),
    _traffic("download_total", lambda d: d.traffic.total_rx),
    _traffic("upload_total", lambda d: d.traffic.total_tx),
    NetgearM6SensorDescription(
        key="signal_bars",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.signal_bars,
    ),
    NetgearM6SensorDescription(
        key="lte_rsrp",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.rsrp,
    ),
    NetgearM6SensorDescription(
        key="lte_sinr",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.sinr,
    ),
    NetgearM6SensorDescription(
        key="lte_rsrq",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.rsrq,
    ),
    NetgearM6SensorDescription(
        key="lte_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.rssi,
    ),
    NetgearM6SensorDescription(
        key="nr_rsrp",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.nr_rsrp,
    ),
    NetgearM6SensorDescription(
        key="nr_sinr",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.nr_sinr,
    ),
    NetgearM6SensorDescription(
        key="nr_rsrq",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.nr_rsrq,
    ),
    NetgearM6SensorDescription(
        key="network_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.network_type,
    ),
    NetgearM6SensorDescription(
        key="operator",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.operator,
    ),
    NetgearM6SensorDescription(
        key="lte_bands",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _bands(d.lte_bands, "B"),
    ),
    NetgearM6SensorDescription(
        key="nr_bands",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _bands(d.nr_bands, "n"),
    ),
    NetgearM6SensorDescription(
        key="connected_clients",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.clients,
    ),
    NetgearM6SensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.temperature,
    ),
    NetgearM6SensorDescription(
        key="thermal_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.thermal_state,
    ),
    NetgearM6SensorDescription(
        key="uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.uptime,
    ),
    NetgearM6SensorDescription(
        key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=1,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.session_duration,
    ),
    NetgearM6SensorDescription(
        key="wan_ip",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.wan_ip,
    ),
    NetgearM6SensorDescription(
        key="sim_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.sim_status,
    ),
    NetgearM6SensorDescription(
        key="cell_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.cell_id,
    ),
    NetgearM6SensorDescription(
        key="plmn",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.plmn,
    ),
    NetgearM6SensorDescription(
        key="failover_backhaul",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.failover_backhaul,
    ),
    NetgearM6SensorDescription(
        key="wifi_clients",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.wifi_clients,
    ),
    NetgearM6SensorDescription(
        key="wifi_ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.wifi_ssid,
    ),
    NetgearM6SensorDescription(
        key="ethernet_speed",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.ethernet_speed,
    ),
    NetgearM6SensorDescription(
        key="modem_firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.modem_firmware,
    ),
    NetgearM6SensorDescription(
        key="sim_pin_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.sim_pin_mode,
    ),
    NetgearM6SensorDescription(
        key="imei",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.imei,
    ),
    NetgearM6SensorDescription(
        key="imei_sv",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.imei_sv,
    ),
    NetgearM6SensorDescription(
        key="iccid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.iccid,
    ),
    NetgearM6SensorDescription(
        key="imsi",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.imsi,
    ),
    NetgearM6SensorDescription(
        key="phone_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.phone_number,
    ),
    NetgearM6SensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        requires_battery=True,
        value_fn=lambda d: d.battery_level,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NetgearM6ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Nighthawk M6 sensors."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_missing() -> None:
        entities = []
        for description in SENSORS:
            if description.key in known:
                continue
            if description.requires_battery and not (
                coordinator.data and coordinator.data.has_battery
            ):
                continue
            known.add(description.key)
            entities.append(NetgearM6Sensor(coordinator, description))
        if entities:
            async_add_entities(entities)

    _add_missing()
    entry.async_on_unload(coordinator.async_add_listener(_add_missing))


class NetgearM6Sensor(NetgearM6Entity, SensorEntity):
    """A value read from the device."""

    entity_description: NetgearM6SensorDescription

    def __init__(
        self,
        coordinator: NetgearM6Coordinator,
        description: NetgearM6SensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Value:
        """Return the sensor value."""
        data = self.coordinator.data
        return self.entity_description.value_fn(data) if data else None

    @property
    def last_reset(self) -> datetime | None:
        """Return the start of the period a daily/monthly counter covers."""
        data = self.coordinator.data
        reset_fn = self.entity_description.last_reset_fn
        if data is None or reset_fn is None or not (start := reset_fn(data)):
            return None
        return dt_util.start_of_local_day(date.fromisoformat(start))
