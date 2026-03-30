# filename: trade_manager.py

from core.logger import log  # <-- custom logger


class TradeManager:
    """
    Manages risk, profit floors, and exit logic for a single trade.
    """

    def __init__(self, hard_stop=-1.00, exit_hysteresis=0.02, buffer_size=2):
        """
        :param hard_stop: maximum loss before immediate exit
        :param exit_hysteresis: small margin to avoid premature exits
        :param buffer_size: number of consecutive exit signals to confirm exit
        """
        # =========================
        # State
        # =========================
        self.max_profit_seen = -999999.0
        self.profit_floor = None

        # =========================
        # Risk
        # =========================
        self.hard_stop = hard_stop

        # Stability buffer
        self.exit_hysteresis = exit_hysteresis
        self.exit_buffer = []
        self.buffer_size = buffer_size

    # =========================
    # Reset trade state
    # =========================
    def reset(self):
        """Resets trade state for new trade."""
        self.max_profit_seen = -999999.0
        self.profit_floor = None
        self.exit_buffer = []

    # =========================
    # Smooth exit buffer
    # =========================
    def _smooth_exit(self, signal: bool) -> bool:
        """
        Smooths exit signal over buffer to avoid false triggers.
        :param signal: boolean indicating immediate exit
        :return: boolean confirming exit
        """
        self.exit_buffer.append(int(signal))
        if len(self.exit_buffer) > self.buffer_size:
            self.exit_buffer.pop(0)
        return sum(self.exit_buffer) >= 1

    # =========================
    # Update profit state
    # =========================
    def update(self, profit: float):
        """
        Update trade state based on current profit.
        Adjusts profit floor for trailing exit.
        """
        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        peak = self.max_profit_seen

        # -------- PROFIT FLOOR LADDER --------
        if peak >= 0.50:
            self.profit_floor = max(self.profit_floor or 0, 0.10)
        if peak >= 0.60:
            self.profit_floor = max(self.profit_floor or 0, 0.20)
        if peak >= 0.80:
            self.profit_floor = max(self.profit_floor or 0, 0.35)
        if peak >= 1.00:
            self.profit_floor = max(self.profit_floor or 0, 0.55)
        if peak >= 1.20:
            self.profit_floor = max(self.profit_floor or 0, 0.75)

        log(f"DEBUG | TradeManager Update | Max Profit: {self.max_profit_seen:.2f} | Profit Floor: {self.profit_floor}")

    # =========================
    # Determine if trade should close
    # =========================
    def should_close(self, profit: float):
        """
        Determines if current trade should be exited.
        :param profit: current floating profit of trade
        :return: tuple (bool: close, str: reason)
        """
        close_signal = False

        # Hard stop exit
        if profit <= self.hard_stop:
            close_signal = True
            reason = "HARD_STOP"
        # Profit floor protection exit
        elif self.profit_floor is not None:
            if profit < (self.profit_floor - self.exit_hysteresis):
                close_signal = True
                reason = "AUTO_EXIT"
            else:
                reason = None
        else:
            reason = None

        # Apply smoothing buffer
        smoothed_close = self._smooth_exit(close_signal)
        if smoothed_close and reason is None:
            reason = "BUFFER_EXIT"

        return smoothed_close, reason