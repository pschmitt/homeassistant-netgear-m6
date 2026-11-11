"""Daily, monthly and lifetime traffic, accumulated across modem sessions.

The device only reports the bytes moved in its *current* data session, and the
counter starts again from zero whenever the modem reconnects or the device
reboots. The tracker turns those readings into deltas and keeps running totals
in Home Assistant's storage, so the numbers survive restarts and reconnects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION
from .models import TrafficSnapshot

SAVE_DELAY = 60


@dataclass(slots=True)
class _State:
    last_rx: int | None = None
    last_tx: int | None = None
    last_session: int | None = None
    total_rx: int = 0
    total_tx: int = 0
    day: str | None = None
    day_rx: int = 0
    day_tx: int = 0
    month: str | None = None
    month_rx: int = 0
    month_tx: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__slots__}

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> _State:
        state = cls()
        for name in cls.__slots__:
            if name in raw:
                setattr(state, name, raw[name])
        return state


class TrafficTracker:
    """Persistent traffic accumulator for one device."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.traffic"
        )
        self._state = _State()

    async def async_load(self) -> None:
        """Restore the saved totals."""
        if raw := await self._store.async_load():
            self._state = _State.from_dict(raw)

    async def async_remove(self) -> None:
        """Delete the saved totals (the config entry was removed)."""
        await self._store.async_remove()

    def update(
        self,
        rx: int | None,
        tx: int | None,
        session_start: int | None,
        now: datetime,
    ) -> TrafficSnapshot:
        """Fold one reading into the totals and return the current snapshot."""
        state = self._state
        self._roll_periods(now.date())

        if rx is not None and tx is not None:
            if state.last_rx is None or state.last_tx is None:
                # First reading ever: only a baseline, the earlier traffic
                # belongs to periods we did not observe.
                delta_rx = delta_tx = 0
            elif (
                rx < state.last_rx
                or tx < state.last_tx
                or (
                    session_start is not None
                    and state.last_session is not None
                    and session_start != state.last_session
                )
            ):
                # A new session started: its counter began at zero.
                delta_rx, delta_tx = rx, tx
            else:
                delta_rx, delta_tx = rx - state.last_rx, tx - state.last_tx

            state.last_rx, state.last_tx = rx, tx
            state.last_session = session_start
            state.total_rx += delta_rx
            state.total_tx += delta_tx
            state.day_rx += delta_rx
            state.day_tx += delta_tx
            state.month_rx += delta_rx
            state.month_tx += delta_tx
            self._store.async_delay_save(state.as_dict, SAVE_DELAY)

        return TrafficSnapshot(
            total_rx=state.total_rx,
            total_tx=state.total_tx,
            day_rx=state.day_rx,
            day_tx=state.day_tx,
            day_start=state.day,
            month_rx=state.month_rx,
            month_tx=state.month_tx,
            month_start=state.month,
        )

    def _roll_periods(self, today: date) -> None:
        state = self._state
        day = today.isoformat()
        if state.day != day:
            state.day, state.day_rx, state.day_tx = day, 0, 0
        month = today.replace(day=1).isoformat()
        if state.month != month:
            state.month, state.month_rx, state.month_tx = month, 0, 0
