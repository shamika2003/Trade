# filename: trade_manager.py

class TradeManager:

    def __init__(self):

        # ------------------------------
        # Tracking State
        # ------------------------------

        self.max_profit_seen = -999999
        self.break_even_activated = False

        # ------------------------------
        # Risk Parameters
        # ------------------------------

        self.break_even_trigger = 0.30
        self.trailing_start = 0.40
        self.trailing_ratio = 0.60
        self.hard_stop = -1.20

        # ------------------------------
        # Exit Stability Controls
        # ------------------------------

        self.exit_buffer = []
        self.buffer_size = 2
        self.exit_hysteresis = 0.03

    # =====================================================
    # Reset State
    # =====================================================

    def reset(self):

        self.max_profit_seen = -999999
        self.break_even_activated = False
        self.exit_buffer = []

    # =====================================================
    # Exit Signal Smoother (Only for Decision Stability)
    # =====================================================

    def _smooth_exit_signal(self, close_signal):

        self.exit_buffer.append(int(close_signal))

        if len(self.exit_buffer) > self.buffer_size:
            self.exit_buffer.pop(0)

        return sum(self.exit_buffer) >= 1

    # =====================================================
    # State Update (Peak Tracking Only)
    # =====================================================

    def update(self, profit):

        # Peak profit memory
        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        # Breakeven activation
        if profit >= self.break_even_trigger:
            self.break_even_activated = True

    # =====================================================
    # Exit Decision Engine
    # =====================================================

    def should_close(self, profit):

        close_signal = False

        # ------------------------------
        # Hard Stop Loss
        # ------------------------------

        if profit <= self.hard_stop:
            close_signal = True

        # ------------------------------
        # Breakeven Protection
        # ------------------------------

        elif self.break_even_activated and profit < -self.exit_hysteresis:
            close_signal = True

        # ------------------------------
        # Trailing Exit Logic
        # ------------------------------

        elif self.max_profit_seen > self.trailing_start:

            trail_level = self.max_profit_seen * self.trailing_ratio

            if profit < (trail_level - self.exit_hysteresis):
                close_signal = True

        return self._smooth_exit_signal(close_signal), \
               ("AUTO_EXIT" if close_signal else None)