# filename: signal_engine.py

from config import SIGNAL_THRESHOLD
from core.logger import log


class SignalEngine:
    """
    Converts model predictions into trading signals
    with stability filtering.
    """

    def __init__(self, confirm_signals: int = 2, clamp_range: float = 2.0):

        self.confirm_signals = confirm_signals
        self.clamp_range = clamp_range
        self.signal_buffer = []


    # ==========================
    # Decide raw signal
    # ==========================
    def _raw_signal(self, pred: float):

        pred = max(min(pred, self.clamp_range), -self.clamp_range)

        if abs(pred) < SIGNAL_THRESHOLD:

            log(
                f"INFO | Signal ignored: "
                f"{pred:.5f} below threshold {SIGNAL_THRESHOLD}"
            )
            return None

        signal = "BUY" if pred > 0 else "SELL"

        log(f"DEBUG | Raw signal: {pred:.5f} -> {signal}")

        return signal


    # ==========================
    # Buffered signal filter
    # ==========================
    def decide(self, pred: float):

        raw = self._raw_signal(pred)

        self.signal_buffer.append(raw)

        if len(self.signal_buffer) > self.confirm_signals:
            self.signal_buffer.pop(0)

        # Require same signal multiple times
        if len(self.signal_buffer) == self.confirm_signals:

            if all(s == "BUY" for s in self.signal_buffer):

                log("INFO | Confirmed BUY signal")
                return "BUY"

            if all(s == "SELL" for s in self.signal_buffer):

                log("INFO | Confirmed SELL signal")
                return "SELL"

        return None