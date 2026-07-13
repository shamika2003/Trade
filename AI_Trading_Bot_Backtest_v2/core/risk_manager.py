import time

from core.logger import log


# =====================================================
# RISK MANAGER
# =====================================================

class RiskManager:


    def __init__(
            self,
            executor,
            max_open_trades=2,
            max_total_trades=5,
            cooldown_seconds=300
    ):

        self.executor = executor

        self.max_open_trades = max_open_trades
        self.max_total_trades = max_total_trades
        self.cooldown_seconds = cooldown_seconds


        self.last_trade_time = {}

        self.locked_symbols = set()



    # =================================================
    # POSITION CHECKS
    # =================================================

    def get_symbol_positions(self, symbol):

        try:

            if hasattr(
                self.executor,
                "get_symbol_positions"
            ):

                return self.executor.get_symbol_positions(symbol)


            if self.executor.has_open_trade(symbol):

                return [True]


            return []


        except Exception as e:

            log(
                f"ERROR | Symbol position check failed {e}"
            )

            return []




    def get_all_positions(self):

        try:

            if hasattr(
                self.executor,
                "get_all_positions"
            ):

                return self.executor.get_all_positions()


            return []


        except Exception as e:

            log(
                f"ERROR | Total position check failed {e}"
            )

            return []




    # =================================================
    # TIME HANDLER
    # =================================================

    def _get_time(self, candle_time=None):

        if candle_time is not None:

            try:

                return candle_time.timestamp()

            except:

                pass


        return time.time()



    # =================================================
    # ENTRY CHECK
    # =================================================

    def can_trade(
            self,
            symbol,
            candle_time=None
    ):


        now = self._get_time(
            candle_time
        )


        last_time = self.last_trade_time.get(
            symbol,
            0
        )



        # cooldown

        if (
            now - last_time
            <
            self.cooldown_seconds
        ):

            return False



        # active lock

        if symbol in self.locked_symbols:

            return False



        # existing position

        positions = self.get_symbol_positions(
            symbol
        )


        if len(positions) >= 1:

            return False



        # total positions

        total = self.get_all_positions()


        if len(total) >= self.max_total_trades:

            return False



        return True




    # =================================================
    # OPEN REGISTER
    # =================================================

    def register_trade_open(
            self,
            symbol,
            candle_time=None
    ):


        self.last_trade_time[symbol] = (
            self._get_time(candle_time)
        )


        self.locked_symbols.add(
            symbol
        )





    # =================================================
    # CLOSE REGISTER
    # =================================================

    def register_trade_close(
            self,
            symbol,
            candle_time=None
    ):


        self.locked_symbols.discard(
            symbol
        )


        self.last_trade_time[symbol] = (
            self._get_time(candle_time)
        )





    # =================================================
    # SIGNAL FILTER
    # =================================================

    def allow_signal(
            self,
            signal_value,
            threshold=0.4
    ):

        return abs(signal_value) >= threshold