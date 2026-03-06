# filename: trade_manager.py

class TradeManager:

    def __init__(self):

        self.max_profit_seen = 0
        self.break_even_activated = False

        # parameters
        self.break_even_trigger = 0.30
        self.trailing_start = 0.40
        self.trailing_ratio = 0.6
        self.hard_stop = -1.2

    def reset(self):

        self.max_profit_seen = 0
        self.break_even_activated = False

    def update(self, profit):

        if profit > self.max_profit_seen:
            self.max_profit_seen = profit

        # activate break-even
        if profit > self.break_even_trigger:
            self.break_even_activated = True

    def should_close(self, profit):

        # hard stop loss
        if profit <= self.hard_stop:
            return True, "HARD_STOP"

        # break even protection
        if self.break_even_activated and profit < 0:
            return True, "BREAKEVEN_PROTECTION"

        # trailing profit
        if self.max_profit_seen > self.trailing_start:

            trail_level = self.max_profit_seen * self.trailing_ratio

            if profit < trail_level:
                return True, "TRAILING_EXIT"

        return False, None