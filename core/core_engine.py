# filename: core_engine.py

import MetaTrader5 as mt5

from core.predictor import Predictor
from core.signal_engine import decide_signal
from core.executor import BrainExecutor
from core.logger import log

from config_core import SYMBOLS, SIGNAL_THRESHOLD


# =====================================================
# CORE ENGINE (BRAIN ORCHESTRATOR)
# =====================================================
class CoreEngine:

    def __init__(self, capital=1000):

        self.capital = capital

        self.predictors = {
            s: Predictor() for s in SYMBOLS
        }

        self.executor = BrainExecutor(capital=capital)

        self.last_signal = {}

        log("INFO | Core Engine initialized")

    # =================================================
    # CHECK OPEN POSITIONS
    # =================================================
    def _has_open_trade(self, symbol=None):

        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        return positions is not None and len(positions) > 0

    # =================================================
    # AVOID REPEATED SIGNALS
    # =================================================
    def _is_repeated_signal(self, symbol, signal):

        if self.last_signal.get(symbol) == signal:
            return True

        self.last_signal[symbol] = signal
        return False

    # =================================================
    # PROCESS ONE SYMBOL
    # =================================================
    def process(self, symbol, df):

        try:

            # -----------------------------
            # BLOCK IF OPEN TRADE EXISTS
            # -----------------------------
            if self._has_open_trade(symbol):
                self._manage_open_trade(symbol)
                return

            # -----------------------------
            # PREDICTION
            # -----------------------------
            predictor = self.predictors[symbol]

            result = predictor.predict(df, None, symbol)

            if result is None:
                return

            signal_value = result["signal"]
            confidence = result["confidence"]

            # ================= DEBUG (KEEP THIS) =================
            log(f"DEBUG | {symbol} signal={signal_value:.6f} conf={confidence:.2f}")

            # -----------------------------
            # FILTER 1: SIGNAL STRENGTH
            # -----------------------------
            if abs(signal_value) < SIGNAL_THRESHOLD:
                return

            # -----------------------------
            # FILTER 2: CONFIDENCE (TEMP RELAXED)
            # -----------------------------
            if confidence < 0.0:
                return

            # -----------------------------
            # CONVERT TO TRADE SIGNAL
            # -----------------------------
            signal = decide_signal(signal_value)

            if signal is None:
                return

            # -----------------------------
            # FILTER 3: AVOID DUPLICATES
            # -----------------------------
            if self._is_repeated_signal(symbol, signal):
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
                log(f"INFO | TRADE OPENED → {symbol}")

        except Exception as e:
            log(f"ERROR | CoreEngine {symbol}: {e}")

    # =================================================
    # MANAGE OPEN TRADE
    # =================================================
    def _manage_open_trade(self, symbol):

        positions = mt5.positions_get(symbol=symbol)

        if not positions:
            return

        position = positions[0]

        profit = float(position.profit)

        # simple exit logic
        if profit > 2.0 or profit < -2.0:

            log(f"INFO | Closing {symbol} | profit={profit:.2f}")

            self.executor.close_position(position)