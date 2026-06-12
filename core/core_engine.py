# filename: core_engine.py

import MetaTrader5 as mt5
import numpy as np

from core.predictor import Predictor
from core.signal_engine import decide_signal
from core.executor import BrainExecutor
from core.logger import log

from config_core import (
    SYMBOLS,
    SIGNAL_THRESHOLD,
)


# =====================================================
# CORE ENGINE (BRAIN ORCHESTRATOR)
# =====================================================
class CoreEngine:

    def __init__(self, capital=1000):

        self.capital = capital

        self.predictors = {s: Predictor() for s in SYMBOLS}
        self.executor = BrainExecutor(capital=capital)

        self.last_signal = {}
        self.active_symbol = None  # IMPORTANT: single-trade lock system

        log("INFO | Core Engine initialized")

    # =================================================
    # CHECK OPEN POSITIONS
    # =================================================
    def _has_open_trade(self):
        positions = mt5.positions_get() or []
        return len(positions) > 0

    # =================================================
    # PROCESS ONE SYMBOL
    # =================================================
    def process(self, symbol, df):

        try:

            # -----------------------------
            # BLOCK NEW TRADES IF ONE OPEN
            # -----------------------------
            if self._has_open_trade():

                # only manage existing trade
                self._manage_open_trade(symbol)
                return

            # -----------------------------
            # MODEL PREDICTION
            # -----------------------------
            feature_list = self.predictors[symbol].models  # safe access check not needed

            result = self.predictors[symbol].predict(
                df,
                self.predictors[symbol].models.keys() if self.predictors[symbol].models else [],
                symbol
            )

            if result is None:
                return

            signal_value = result["signal"]
            confidence = result["confidence"]

            # -----------------------------
            # BASIC FILTER
            # -----------------------------
            if abs(signal_value) < SIGNAL_THRESHOLD:
                return

            if confidence < 0.55:
                return

            # -----------------------------
            # FINAL SIGNAL DECISION
            # -----------------------------
            signal = decide_signal(signal_value)

            if signal is None:
                return

            log(f"INFO | {symbol} SIGNAL → {signal} | conf={confidence:.2f}")

            # -----------------------------
            # EXECUTE TRADE
            # -----------------------------
            success = self.executor.open_trade(
                symbol=symbol,
                direction=signal,
                lot=None
            )

            if success:
                self.active_symbol = symbol
                log(f"INFO | TRADE OPENED → {symbol}")

        except Exception as e:
            log(f"ERROR | CoreEngine {symbol}: {e}")

    # =================================================
    # MANAGE OPEN TRADE (ONLY ONE SYMBOL ACTIVE)
    # =================================================
    def _manage_open_trade(self, symbol):

        positions = mt5.positions_get(symbol=symbol) or []

        if not positions:
            self.active_symbol = None
            return

        position = positions[0]

        profit = float(position.profit)

        # -----------------------------
        # SIMPLE EXIT RULE (TEMP CORE LOGIC)
        # -----------------------------
        if profit > 1.0 or profit < -1.0:

            log(f"INFO | Closing trade {symbol} profit={profit:.2f}")

            self.executor.close_position(position)

            self.active_symbol = None