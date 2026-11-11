"""Tests for the traffic accumulator."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant

from custom_components.netgear_m6.traffic import TrafficTracker

GIB = 1024**3


def _at(day: int, month: int = 11) -> datetime:
    return datetime(2026, month, day, 12, 0)


async def test_first_reading_is_only_a_baseline(hass: HomeAssistant) -> None:
    """Traffic before the first reading belongs to no observed period."""
    tracker = TrafficTracker(hass, "e")
    snapshot = tracker.update(5 * GIB, GIB, 1, _at(10))
    assert (snapshot.total_rx, snapshot.day_rx, snapshot.month_rx) == (0, 0, 0)


async def test_deltas_accumulate(hass: HomeAssistant) -> None:
    """Growth within a session is added to every counter."""
    tracker = TrafficTracker(hass, "e")
    tracker.update(GIB, GIB, 1, _at(10))
    snapshot = tracker.update(3 * GIB, 2 * GIB, 1, _at(10))
    assert snapshot.total_rx == 2 * GIB
    assert snapshot.total_tx == GIB
    assert snapshot.day_rx == 2 * GIB
    assert snapshot.month_rx == 2 * GIB


async def test_new_session_counts_from_zero(hass: HomeAssistant) -> None:
    """A smaller counter means the modem reconnected: its value is all new."""
    tracker = TrafficTracker(hass, "e")
    tracker.update(10 * GIB, 0, 1, _at(10))
    snapshot = tracker.update(GIB, 0, 2, _at(10))
    assert snapshot.total_rx == GIB


async def test_new_session_with_larger_counter(hass: HomeAssistant) -> None:
    """A changed session start wins even when the counter happens to be larger."""
    tracker = TrafficTracker(hass, "e")
    tracker.update(GIB, 0, 1, _at(10))
    snapshot = tracker.update(5 * GIB, 0, 2, _at(10))
    assert snapshot.total_rx == 5 * GIB


async def test_day_and_month_roll_over(hass: HomeAssistant) -> None:
    """Daily and monthly totals restart with their period, lifetime does not."""
    tracker = TrafficTracker(hass, "e")
    tracker.update(0, 0, 1, _at(30))
    tracker.update(GIB, 0, 1, _at(30))

    next_day = tracker.update(2 * GIB, 0, 1, _at(1, 12))
    assert next_day.day_rx == GIB
    assert next_day.month_rx == GIB
    assert next_day.total_rx == 2 * GIB
    assert next_day.day_start == "2026-12-01"
    assert next_day.month_start == "2026-12-01"


async def test_missing_counters_change_nothing(hass: HomeAssistant) -> None:
    """A poll without counters keeps the totals."""
    tracker = TrafficTracker(hass, "e")
    tracker.update(0, 0, 1, _at(10))
    tracker.update(GIB, 0, 1, _at(10))
    snapshot = tracker.update(None, None, None, _at(10))
    assert snapshot.total_rx == GIB


async def test_totals_survive_a_restart(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """The saved state is restored by a new tracker."""
    tracker = TrafficTracker(hass, "e")
    tracker.update(0, 0, 1, _at(10))
    tracker.update(GIB, 0, 1, _at(10))
    await tracker._store.async_save(tracker._state.as_dict())

    restored = TrafficTracker(hass, "e")
    await restored.async_load()
    snapshot = restored.update(2 * GIB, 0, 1, _at(10))
    assert snapshot.total_rx == 2 * GIB
