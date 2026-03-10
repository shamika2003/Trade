# filename: trade_manager.py

class TradeManager:

    def __init__(self):

        # =========================
        # State
        # =========================

        self.max_profit_seen = -999999
        self.profit_floor = None

        # =========================
        # Risk
        # =========================

        self.hard_stop = -1.00

        # stability
        self.exit_hysteresis = 0.02
        self.exit_buffer = []
        self.buffer_size = 2


    # =========================
    # Reset
    # =========================

    def reset(self):

        self.max_profit_seen = -999999
        self.profit_floor = None
        self.exit_buffer = []


    # =========================
    # Smoothing
    # =========================

    def _smooth_exit(self, signal):

        self.exit_buffer.append(int(signal))

        if len(self.exit_buffer) > self.buffer_size:
            self.exit_buffer.pop(0)

        return sum(self.exit_buffer) >= 1


    # =========================
    # Update profit state
    # =========================

    def update(self, profit):

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


    # =========================
    # Exit logic
    # =========================

    def should_close(self, profit):

        close_signal = False

        # hard stop
        if profit <= self.hard_stop:
            close_signal = True

        # profit floor protection
        elif self.profit_floor is not None:
            if profit < (self.profit_floor - self.exit_hysteresis):
                close_signal = True

        return self._smooth_exit(close_signal), \
               ("AUTO_EXIT" if close_signal else None)