# filename: brain_core.py

import numpy as np
import MetaTrader5 as mt5
import time
import os
import csv
from config import TRADE_LOT, SIGNAL_THRESHOLD, COOLDOWN_SECONDS, TAKE_PROFIT, STOP_LOSS
from logger import log  # <-- custom logger

LOG_FILE = "trade_log.csv"


class TradingBrainCore:

    def __init__(self, symbol, predictor, transformer):
        self.symbol = symbol
        self.predictor = predictor
        self.transformer = transformer

        # =================================================
        # Prediction smoothing
        # =================================================
        self.prediction_history = []

        # =================================================
        # Cooldown per symbol
        # =================================================
        self.cooldown_timestamp = 0

        # =================================================
        # Logging
        # =================================================
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "symbol", "signal", "price",
                    "profit", "action", "reason"
                ])

    # =====================================================
    # Prediction Stabilizer
    # =====================================================
    def smooth_prediction(self, pred):
        self.prediction_history.append(float(pred))
        if len(self.prediction_history) > 5:
            self.prediction_history.pop(0)
        return float(np.mean(self.prediction_history))

    # =====================================================
    # Position Tracker
    # =====================================================
    def get_open_position(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None or len(positions) == 0:
            return None
        return positions[0]

    # =====================================================
    # Safe Execution Layer
    # =====================================================
    def _send_order(self, request):
        if request is None:
            return False

        for attempt in range(3):
            try:
                result = mt5.order_send(request)
                if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                    return True
                elif result is not None:
                    log(f"WARNING | Order failed ({self.symbol}) retcode={result.retcode}")
            except Exception as e:
                log(f"ERROR | Order exception ({self.symbol}): {e}")
            time.sleep(0.4)
        return False

    # =====================================================
    # Brain Decision Engine
    # =====================================================
    def decide_and_act(self, df_features):
        now = time.time()

        # Cooldown safety
        if now - self.cooldown_timestamp < COOLDOWN_SECONDS:
            return

        if df_features is None or df_features.empty:
            return

        feature_list = self.transformer.get_feature_list()
        missing = [f for f in feature_list if f not in df_features.columns]
        if missing:
            log(f"WARNING | {self.symbol} missing features: {missing}")
            return

        X = df_features[feature_list].ffill().dropna()
        if X.empty:
            return

        if "symbol" in df_features.columns:
            X = X.copy()
            X["symbol"] = df_features["symbol"].iloc[-1]

        raw_pred = self.predictor.predict(X, feature_list)
        if raw_pred is None or len(raw_pred) == 0:
            return

        pred = self.smooth_prediction(raw_pred[-1])
        pred = np.clip(pred, -2, 2)

        if abs(pred) < SIGNAL_THRESHOLD:
            log(f"INFO | [{self.symbol}] Prediction too weak: {round(pred, 4)}")
            return

        # =================================================
        # ENTRY / EXIT
        # =================================================
        position = self.get_open_position()
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return

        # ENTRY
        if position is None:
            direction = "BUY" if pred > 0 else "SELL"
            price = tick.ask if direction == "BUY" else tick.bid
            if price is None or price <= 0:
                return

            if self._open_trade(direction, price):
                self.cooldown_timestamp = now
            return

        # EXIT
        profit = float(position.profit)

        # Take Profit
        if profit >= TAKE_PROFIT:
            if self._close_position(position, reason="TAKE_PROFIT"):
                self.cooldown_timestamp = now
            return

        # Stop Loss
        if profit <= -STOP_LOSS:
            if self._close_position(position, reason="STOP_LOSS"):
                self.cooldown_timestamp = now
            return

    # =====================================================
    # Trade Executors
    # =====================================================
    def _open_trade(self, direction, price):
        if price is None or price <= 0:
            return False

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": TRADE_LOT,
            "type": order_type,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": "ML_BRAIN"
        }

        success = self._send_order(request)
        if success:
            log(f"INFO | [{self.symbol}] Brain opened trade: {direction} @ {price}")
            self._log_trade(direction, price, 0, "OPEN", "Signal")
        return success

    def _close_position(self, position, reason="CLOSE"):
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return False

        if position.type == mt5.ORDER_TYPE_BUY:
            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL
        else:
            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": "ML_CLOSE"
        }

        success = self._send_order(request)
        if success:
            log(f"INFO | [{self.symbol}] Closed trade @ {price} | Reason: {reason}")
            self._log_trade(
                "SELL" if position.type == mt5.ORDER_TYPE_BUY else "BUY",
                price,
                position.profit,
                "CLOSE",
                reason
            )
        return success

    # =====================================================
    # Logging
    # =====================================================
    def _log_trade(self, signal, price, profit, action, reason):
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                self.symbol,
                signal,
                round(price, 5) if price else 0,
                round(profit, 2),
                action,
                reason
            ])