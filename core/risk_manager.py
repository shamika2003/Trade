# filename: risk_manager.py

import time
import MetaTrader5 as mt5


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
        max_open_trades=2,
        max_total_trades=5,
        cooldown_seconds=300
    ):
        self.max_open_trades = max_open_trades
        self.max_total_trades = max_total_trades
        self.cooldown_seconds = cooldown_seconds

        # symbol-level state
        self.last_trade_time = {}
        self.locked_symbols = set()

    # ==============================
    # MT5 STATE CHECK
    # ==============================
    def _mt5_ok(self):
        return mt5.terminal_info() is not None

    # ==============================
    # POSITION CHECKS
    # ==============================
    def get_symbol_positions(self, symbol):
        return mt5.positions_get(symbol=symbol) or []

    def get_all_positions(self):
        return mt5.positions_get() or []

    # ==============================
    # MAIN ENTRY CHECK
    # ==============================
    def can_trade(self, symbol):
        """
        Returns True if new trade is allowed.
        """

        if not self._mt5_ok():
            return False

        # --- cooldown check ---
        now = time.time()
        last_time = self.last_trade_time.get(symbol, 0)

        if now - last_time < self.cooldown_seconds:
            return False

        # --- symbol locked (already in active trade) ---
        if symbol in self.locked_symbols:
            return False

        # --- position limits ---
        symbol_positions = self.get_symbol_positions(symbol)
        if len(symbol_positions) >= 1:
            return False

        all_positions = self.get_all_positions()
        if len(all_positions) >= self.max_total_trades:
            return False

        return True

    # ==============================
    # CALL AFTER TRADE OPENED
    # ==============================
    def register_trade_open(self, symbol):
        self.last_trade_time[symbol] = time.time()
        self.locked_symbols.add(symbol)

    # ==============================
    # CALL AFTER TRADE CLOSED
    # ==============================
    def register_trade_close(self, symbol):
        self.locked_symbols.discard(symbol)
        self.last_trade_time[symbol] = time.time()

    # ==============================
    # OPTIONAL: SIGNAL GATE
    # ==============================
    def allow_signal(self, signal_value, threshold=0.4):
        """
        Extra safety filter before execution layer.
        """
        return abs(signal_value) >= threshold