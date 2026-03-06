# filename: trade_manager.py

class TradeManager:

    def __init__(self):

        # tracking
        self.max_profit_seen = 0
        self.break_even_activated = False
        self.profit_buffer = []

        # parameters
        self.break_even_trigger = 0.30
        self.trailing_start = 0.40
        self.trailing_ratio = 0.60
        self.hard_stop = -1.20

        # stability controls
        self.buffer_size = 3
        self.spike_filter = 2.5

    # ==========================================
    # Reset State
    # ==========================================

    def reset(self):

        self.max_profit_seen = 0
        self.break_even_activated = False
        self.profit_buffer = []

    # ==========================================
    # Profit Smoothing
    # ==========================================

    def _smooth_profit(self, profit):

        self.profit_buffer.append(profit)

        if len(self.profit_buffer) > self.buffer_size:
            self.profit_buffer.pop(0)

        return sum(self.profit_buffer) / len(self.profit_buffer)

    # ==========================================
    # Update State
    # ==========================================

    def update(self, profit):

        profit = self._smooth_profit(profit)

        # filter extreme spikes
        if profit > self.max_profit_seen * self.spike_filter and self.max_profit_seen > 0:
            return

        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        # activate break-even
        if profit >= self.break_even_trigger:
            self.break_even_activated = True

    # ==========================================
    # Exit Decision
    # ==========================================

    def should_close(self, profit):

        profit = self._smooth_profit(profit)

        # HARD STOP LOSS
        if profit <= self.hard_stop:
            return True, "HARD_STOP"

        # BREAK EVEN PROTECTION
        if self.break_even_activated and profit < 0:
            return True, "BREAKEVEN_PROTECTION"

        # TRAILING EXIT
        if self.max_profit_seen > self.trailing_start:

            trail_level = self.max_profit_seen * self.trailing_ratio

            if profit < trail_level:
                return True, "TRAILING_EXIT"

        return False, None