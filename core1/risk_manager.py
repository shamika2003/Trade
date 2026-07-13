# filename: risk_manager.py

import time

from core.logger import log


# =====================================================
# RISK MANAGER
# =====================================================
class RiskManager:
    """
    Central gatekeeper for trading decisions.

    Responsibilities:
    - Prevent overtrading
    - Lock symbols when trade is active
    - Enforce cooldown
    - Control global + per-symbol exposure
    """


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


        # symbol-level state

        self.last_trade_time = {}

        self.locked_symbols = set()



    # =================================================
    # POSITION CHECKS
    # DELEGATED TO EXECUTOR
    # =================================================

    def get_symbol_positions(self, symbol):

        try:

            if hasattr(
                self.executor,
                "get_symbol_positions"
            ):

                return (
                    self.executor
                    .get_symbol_positions(symbol)
                )


            elif self.executor.has_open_trade(symbol):

                return [True]


            return []


        except Exception as e:

            log(
                f"ERROR | Symbol position check failed: {e}"
            )

            return []



    def get_all_positions(self):

        try:

            if hasattr(
                self.executor,
                "get_all_positions"
            ):

                return (
                    self.executor
                    .get_all_positions()
                )


            return []


        except Exception as e:

            log(
                f"ERROR | Total position check failed: {e}"
            )

            return []



    # =================================================
    # MAIN ENTRY CHECK
    # =================================================

    def can_trade(self, symbol):
        """
        Returns True if new trade is allowed.
        """


        # -----------------------------
        # COOLDOWN CHECK
        # -----------------------------

        now = time.time()

        last_time = (
            self.last_trade_time
            .get(symbol, 0)
        )


        if (
            now - last_time
            <
            self.cooldown_seconds
        ):

            return False



        # -----------------------------
        # SYMBOL LOCK CHECK
        # -----------------------------

        if symbol in self.locked_symbols:

            return False



        # -----------------------------
        # ACTIVE POSITION CHECK
        # -----------------------------

        symbol_positions = (
            self.get_symbol_positions(symbol)
        )


        if len(symbol_positions) >= 1:

            return False



        # -----------------------------
        # GLOBAL POSITION LIMIT
        # -----------------------------

        all_positions = (
            self.get_all_positions()
        )


        if len(all_positions) >= self.max_total_trades:

            return False



        return True



    # =================================================
    # REGISTER TRADE OPEN
    # =================================================

    def register_trade_open(self, symbol):

        self.last_trade_time[symbol] = (
            time.time()
        )

        self.locked_symbols.add(
            symbol
        )



    # =================================================
    # REGISTER TRADE CLOSE
    # =================================================

    def register_trade_close(self, symbol):

        self.locked_symbols.discard(
            symbol
        )


        self.last_trade_time[symbol] = (
            time.time()
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