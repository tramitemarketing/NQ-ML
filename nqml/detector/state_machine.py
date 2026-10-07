"""Una macchina a stati per (va_type, side). Strutturale e permissiva: nessuna soglia (spec §5)."""
from __future__ import annotations

import pandas as pd

from nqml.detector.events import Bar5m, Detection
from nqml.profile.volume_profile import ValueArea

FIVE_MIN = pd.Timedelta(minutes=5)


class SetupDetector:
    def __init__(self, va_type: str, side: str, max_excursion_minutes: int, tick_size: float):
        assert side in ("long", "short")
        self.va_type = va_type
        self.side = side
        self.max_excursion_minutes = max_excursion_minutes
        self.tick_size = tick_size
        self.state = "INSIDE"
        self._break_ts: pd.Timestamp | None = None
        self._va_break: ValueArea | None = None
        self._extreme: float | None = None
        self._bars_outside = 0

    # --- geometria per lato -------------------------------------------------
    def _outside(self, bar: Bar5m, va: ValueArea) -> bool:
        return bar.close < va.val if self.side == "long" else bar.close > va.vah

    def _beyond_opposite(self, bar: Bar5m, va: ValueArea) -> bool:
        return bar.close > va.vah if self.side == "long" else bar.close < va.val

    @staticmethod
    def _inside(bar: Bar5m, va: ValueArea) -> bool:
        return va.val <= bar.close <= va.vah

    def _update_extreme(self, bar: Bar5m) -> None:
        if self.side == "long":
            self._extreme = bar.low if self._extreme is None else min(self._extreme, bar.low)
        else:
            self._extreme = bar.high if self._extreme is None else max(self._extreme, bar.high)

    def _reset(self) -> None:
        self.state = "INSIDE"
        self._break_ts = self._va_break = self._extreme = None
        self._bars_outside = 0

    # --- transizioni --------------------------------------------------------
    def on_bar(self, bar: Bar5m, va: ValueArea | None) -> Detection | None:
        if va is None:
            return None
        if self.state == "INSIDE":
            if self._outside(bar, va):
                self.state = "BROKEN"
                self._break_ts = bar.ts_open
                self._va_break = va
                self._extreme = None
                self._update_extreme(bar)
                self._bars_outside = 1
            return None

        if self.state == "EXHAUSTED":
            # Riarmo permissivo (spec §5): dentro la VA, o oltre il bordo opposto (il prezzo ha
            # attraversato tutta la VA: il setup su questo lato e' comunque finito).
            if self._inside(bar, va) or self._beyond_opposite(bar, va):
                self._reset()
            return None

        # BROKEN
        self._update_extreme(bar)
        close_ts = bar.ts_open + FIVE_MIN
        minutes = int((close_ts - self._break_ts).total_seconds() // 60)
        if minutes > self.max_excursion_minutes:
            self.state = "EXHAUSTED"
            return None
        if self._beyond_opposite(bar, va):
            self._reset()
            return None
        if self._inside(bar, va):
            if self.side == "long":
                stop = self._extreme - self.tick_size
                target = va.vah
            else:
                stop = self._extreme + self.tick_size
                target = va.val
            det = Detection(
                va_type=self.va_type, side=self.side,
                break_ts=self._break_ts, reentry_ts=close_ts,
                extreme_price=self._extreme, va_break=self._va_break, va_reentry=va,
                entry_ref_price=bar.close, stop_price=stop, target_price=target,
                bars_outside=self._bars_outside, excursion_minutes=minutes,
            )
            self._reset()
            return det
        self._bars_outside += 1
        return None
