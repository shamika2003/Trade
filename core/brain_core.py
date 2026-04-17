# filename: brain_core.py

import numpy as np
import MetaTrader5 as mt5
import time

from config import (
    SIGNAL_THRESHOLD,
    COOLDOWN_SECONDS,
    STOP_LOSS,
    TAKE_PROFIT,
    TRADE_LOT,
    MIN_MODEL_AGREEMENT,
    MIN_TRADE_STRENGTH
)

from core.logger import log
from core.trade_manager import TradeManager


class TradingBrainCore:

    def __init__(self, symbol, predictor, transformer, executor):
        self.symbol = symbol
        self.predictor = predictor
        self.transformer = transformer
        self.executor = executor

        self.pred_history = []
        self.cooldown_timestamp = 0

        self.trade_manager = TradeManager(
            hard_stop=-STOP_LOSS,
            take_profit=TAKE_PROFIT
        )

    def smooth(self, value):
        self.pred_history.append(float(value))

        if len(self.pred_history) > 5:
            self.pred_history.pop(0)

        return float(np.mean(self.pred_history))

    def get_position(self):
        positions = mt5.positions_get(symbol=self.symbol) or []
        return positions[0] if positions else None

    def decide_and_act(self, df):
        now = time.time()

        # --------------------------
        # COOLDOWN
        # --------------------------
        if now - self.cooldown_timestamp < COOLDOWN_SECONDS:
            return

        # --------------------------
        # DATA CHECK
        # --------------------------
        if df is None or df.empty:
            log(f"DEBUG | {self.symbol} empty dataframe")
            return

        feature_list = self.transformer.get_feature_list()

        missing = [f for f in feature_list if f not in df.columns]
        if missing:
            log(f"WARNING | {self.symbol} missing features: {missing[:5]}")
            return

        X = df[feature_list].ffill()

        if len(X) < 50:
            log(f"DEBUG | {self.symbol} not enough rows: {len(X)}")
            return

        # --------------------------
        # PREDICTION
        # --------------------------
        result = self.predictor.predict(X, feature_list, symbol=self.symbol)

        if result is None:
            log(f"DEBUG | {self.symbol} no prediction")
            return

        raw_signal = float(result["signal"])
        confidence = float(result["confidence"])
        agreement = float(result["agreement"])

        # --------------------------
        # FILTERS (CONFIDENCE SYSTEM)
        # --------------------------
        if confidence < MIN_MODEL_AGREEMENT:
            log(f"DEBUG | {self.symbol} low confidence: {confidence:.2f}")
            return

        # smooth AFTER filtering (important fix)
        signal = self.smooth(raw_signal)
        signal = float(np.clip(signal, -2, 2))

        if abs(signal) < MIN_TRADE_STRENGTH:
            log(f"DEBUG | {self.symbol} weak signal: {signal:.4f}")
            return

        # optional: agreement filter (NOW USED)
        if agreement < 0.5:
            log(f"DEBUG | {self.symbol} low agreement: {agreement:.2f}")
            return

        # --------------------------
        # POSITION CHECK
        # --------------------------
        position = self.get_position()

        # --------------------------
        # ENTRY
        # --------------------------
        if position is None:
            direction = "BUY" if signal > 0 else "SELL"

            success = self.executor.open_trade(
                self.symbol,
                direction,
                lot=TRADE_LOT,
                sl=STOP_LOSS,
                tp=TAKE_PROFIT
            )

            if success:
                log(f"INFO | {self.symbol} OPEN {direction} | signal={signal:.4f}")
                self.trade_manager.reset()
                self.cooldown_timestamp = now

            return

        # --------------------------
        # EXIT
        # --------------------------
        profit = float(position.profit)

        self.trade_manager.update(profit)
        close, reason = self.trade_manager.should_close(profit)

        if close:
            if self.executor.close_position(position, reason):
                log(f"INFO | {self.symbol} CLOSE {reason} | profit={profit:.2f}")
                self.trade_manager.reset()
                self.cooldown_timestamp = now