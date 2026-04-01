# filename: trade_manager.py

from core.logger import log  # <-- custom logger


class TradeManager:
    """
    Advanced Trade Manager for a single trade.

    Features:
    - Hard stop enforcement
    - Dynamic profit floor / trailing take profit
    - Buffered exit to avoid jitter
    - Full logging for debugging
    """

    def __init__(self, hard_stop=-50.0, take_profit=100.0, exit_hysteresis=0.02, buffer_size=2):
        """
        :param hard_stop: Maximum allowed loss per trade (USD)
        :param take_profit: Maximum take profit per trade (USD)
        :param exit_hysteresis: Small margin to prevent premature exits
        :param buffer_size: Number of consecutive exit confirmations
        """
        # =========================
        # State
        # =========================
        self.max_profit_seen = -999999.0
        self.profit_floor = None
        self.exit_buffer = []

        # =========================
        # Risk
        # =========================
        self.hard_stop = hard_stop
        self.take_profit = take_profit

        # =========================
        # Stability
        # =========================
        self.exit_hysteresis = exit_hysteresis
        self.buffer_size = buffer_size

    # =========================
    # Reset trade state
    # =========================
    def reset(self):
        """Resets all state for a new trade."""
        self.max_profit_seen = -999999.0
        self.profit_floor = None
        self.exit_buffer = []

    # =========================
    # Smooth exit buffer
    # =========================
    def _smooth_exit(self, signal: bool) -> bool:
        """
        Smooths exit signal over a buffer to prevent false triggers.
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
        Update trade state based on current floating profit.
        Adjusts profit floor dynamically.
        """
        # Track max profit
        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        peak = self.max_profit_seen

        # -------- PROFIT FLOOR LADDER --------
        # Dynamically lock-in gains progressively
        if peak >= 20:
            self.profit_floor = max(self.profit_floor or 0, 5)
        if peak >= 40:
            self.profit_floor = max(self.profit_floor or 0, 15)
        if peak >= 60:
            self.profit_floor = max(self.profit_floor or 0, 30)
        if peak >= 80:
            self.profit_floor = max(self.profit_floor or 0, 50)
        if peak >= 100:
            self.profit_floor = max(self.profit_floor or 0, 75)

        log(f"DEBUG | TradeManager Update | Max Profit: {self.max_profit_seen:.2f} | Profit Floor: {self.profit_floor}")

    # =========================
    # Determine if trade should close
    # =========================
    def should_close(self, profit: float):
        """
        Determines whether the current trade should be exited.

        :param profit: Current floating profit of trade
        :return: Tuple (bool: close, str: reason)
        """
        close_signal = False
        reason = None

        # ----------------------
        # Hard stop exit
        # ----------------------
        if profit <= self.hard_stop:
            close_signal = True
            reason = "HARD_STOP"

        # ----------------------
        # Profit floor exit
        # ----------------------
        elif self.profit_floor is not None:
            if profit < (self.profit_floor - self.exit_hysteresis):
                close_signal = True
                reason = "PROFIT_FLOOR_EXIT"

        # ----------------------
        # Max take profit exit
        # ----------------------
        elif profit >= self.take_profit:
            close_signal = True
            reason = "TAKE_PROFIT"

        # ----------------------
        # Apply smoothing buffer
        # ----------------------
        smoothed_close = self._smooth_exit(close_signal)
        if smoothed_close and reason is None:
            reason = "BUFFER_EXIT"

        return smoothed_close, reason