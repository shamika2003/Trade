# filename: trade_manager.py

from core.logger import log


class TradeManager:
    """
    Manages risk, trailing profit floors, and exit logic.
    """

    def __init__(self, hard_stop=-20.0, exit_hysteresis=0.05, buffer_size=2):

        # =========================
        # State
        # =========================
        self.max_profit_seen = float("-inf")
        self.profit_floor = None

        # =========================
        # Risk
        # =========================
        self.hard_stop = hard_stop

        # =========================
        # Stability
        # =========================
        self.exit_hysteresis = exit_hysteresis
        self.buffer_size = buffer_size
        self.exit_buffer = []


    # =========================
    # Reset trade state
    # =========================
    def reset(self):

        self.max_profit_seen = float("-inf")
        self.profit_floor = None
        self.exit_buffer = []


    # =========================
    # Smooth exit signal
    # =========================
    def _smooth_exit(self, signal: bool):

        self.exit_buffer.append(int(signal))

        if len(self.exit_buffer) > self.buffer_size:
            self.exit_buffer.pop(0)

        return sum(self.exit_buffer) >= self.buffer_size


    # =========================
    # Update trade state
    # =========================
    def update(self, profit: float):

        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        peak = self.max_profit_seen

        # -------------------------
        # Profit floor ladder
        # -------------------------
        if peak >= 0.50:
            self.profit_floor = max(self.profit_floor or 0, 0.10)

        if peak >= 0.75:
            self.profit_floor = max(self.profit_floor or 0, 0.25)

        if peak >= 1.00:
            self.profit_floor = max(self.profit_floor or 0, 0.45)

        if peak >= 1.50:
            self.profit_floor = max(self.profit_floor or 0, 0.75)

        if peak >= 2.00:
            self.profit_floor = max(self.profit_floor or 0, 1.20)

        log(
            f"DEBUG | TradeManager | Profit={profit:.2f} "
            f"| Peak={self.max_profit_seen:.2f} "
            f"| Floor={self.profit_floor}"
        )


    # =========================
    # Exit Decision
    # =========================
    def should_close(self, profit: float):

        reason = None
        close_signal = False

        # -------------------------
        # Hard stop
        # -------------------------
        if profit <= self.hard_stop:

            close_signal = True
            reason = "HARD_STOP"

        # -------------------------
        # Trailing profit floor
        # -------------------------
        elif self.profit_floor is not None:

            if profit < (self.profit_floor - self.exit_hysteresis):

                close_signal = True
                reason = "TRAIL_EXIT"

        # -------------------------
        # Smooth signal
        # -------------------------
        smoothed_close = self._smooth_exit(close_signal)

        if smoothed_close and reason is None:
            reason = "BUFFER_EXIT"

        return smoothed_close, reason