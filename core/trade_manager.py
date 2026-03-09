# filename: trade_manager.py

class TradeManager:

    def __init__(self):

        # ============================
        # State tracking
        # ============================

        self.max_profit_seen = -999999
        self.break_even = False
        self.locked_profit = 0

        # ============================
        # Risk controls
        # ============================

        self.hard_stop = -1.20

        # break-even
        self.break_even_trigger = 0.30

        # profit locking stages
        self.lock_stage1 = 0.50
        self.lock_stage2 = 0.80
        self.lock_stage3 = 1.20

        self.lock_ratio1 = 0.25
        self.lock_ratio2 = 0.45
        self.lock_ratio3 = 0.65

        # trailing ratios
        self.trail_loose = 0.70
        self.trail_tight = 0.85

        # collapse detection
        self.collapse_ratio = 0.50

        # stability
        self.exit_hysteresis = 0.03
        self.exit_buffer = []
        self.buffer_size = 2


    # ==================================
    # Reset state
    # ==================================

    def reset(self):

        self.max_profit_seen = -999999
        self.break_even = False
        self.locked_profit = 0
        self.exit_buffer = []


    # ==================================
    # Exit signal smoothing
    # ==================================

    def _smooth_exit(self, signal):

        self.exit_buffer.append(int(signal))

        if len(self.exit_buffer) > self.buffer_size:
            self.exit_buffer.pop(0)

        return sum(self.exit_buffer) >= 1


    # ==================================
    # Update state
    # ==================================

    def update(self, profit):

        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        if profit >= self.break_even_trigger:
            self.break_even = True

        # -------- Profit locking ladder --------

        if self.max_profit_seen >= self.lock_stage1:
            self.locked_profit = max(
                self.locked_profit,
                self.max_profit_seen * self.lock_ratio1
            )

        if self.max_profit_seen >= self.lock_stage2:
            self.locked_profit = max(
                self.locked_profit,
                self.max_profit_seen * self.lock_ratio2
            )

        if self.max_profit_seen >= self.lock_stage3:
            self.locked_profit = max(
                self.locked_profit,
                self.max_profit_seen * self.lock_ratio3
            )


    # ==================================
    # Exit decision
    # ==================================

    def should_close(self, profit):

        close_signal = False

        # -------------------------------
        # 1 Hard stop
        # -------------------------------

        if profit <= self.hard_stop:
            close_signal = True

        # -------------------------------
        # 2 Break-even protection
        # -------------------------------

        elif self.break_even and profit < -self.exit_hysteresis:
            close_signal = True

        # -------------------------------
        # 3 Locked profit protection
        # -------------------------------

        elif profit < (self.locked_profit - self.exit_hysteresis):
            close_signal = True

        # -------------------------------
        # 4 Momentum trailing
        # -------------------------------

        elif self.max_profit_seen > 0.60:

            trail = self.max_profit_seen * self.trail_loose

            if profit < (trail - self.exit_hysteresis):
                close_signal = True

        # -------------------------------
        # 5 Tight trailing for big wins
        # -------------------------------

        if self.max_profit_seen > 1.00:

            trail = self.max_profit_seen * self.trail_tight

            if profit < (trail - self.exit_hysteresis):
                close_signal = True

        # -------------------------------
        # 6 Profit collapse detection
        # -------------------------------

        collapse_level = self.max_profit_seen * self.collapse_ratio

        if self.max_profit_seen > 0.70 and profit < collapse_level:
            close_signal = True


        return self._smooth_exit(close_signal), \
               ("AUTO_EXIT" if close_signal else None)