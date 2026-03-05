# filename: brain_core.py

import numpy as np
import MetaTrader5 as mt5
import time

from config import SYMBOL, TRADE_LOT, SIGNAL_THRESHOLD


class TradingBrainCore:

    def __init__(self, predictor, transformer):

        self.predictor = predictor
        self.transformer = transformer

        self.prediction_history = []

        self.cooldown_timestamp = 0

    # -------------------------------------------------
    # Prediction Stability Filter
    # -------------------------------------------------

    def smooth_prediction(self, pred):

        self.prediction_history.append(pred)

        if len(self.prediction_history) > 5:
            self.prediction_history.pop(0)

        return float(np.mean(self.prediction_history))

    # -------------------------------------------------
    # Position Tracker
    # -------------------------------------------------

    def get_open_position(self):

        positions = mt5.positions_get(symbol=SYMBOL)

        if positions is None or len(positions) == 0:
            return None

        return positions[0]

    # -------------------------------------------------
    # Trade Execution Safety Layer
    # -------------------------------------------------

    def _send_order(self, request):

        for _ in range(3):

            result = mt5.order_send(request)

            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                return True

            time.sleep(0.5)

        return False

    # -------------------------------------------------
    # Main Brain Decision Engine
    # -------------------------------------------------

    def decide_and_act(self, df_features):

        now = time.time()

        # Cooldown safety
        if now - self.cooldown_timestamp < 60:
            return

        feature_list = self.transformer.get_feature_list()

        X = df_features[feature_list].ffill().dropna()

        if X.empty:
            return

        raw_pred = self.predictor.predict(X, feature_list)[-1]

        pred = self.smooth_prediction(raw_pred)

        # Prediction clipping safety
        pred = np.clip(pred, -2, 2)

        # Confidence gating
        if abs(pred) < SIGNAL_THRESHOLD:
            return

        position = self.get_open_position()

        tick = mt5.symbol_info_tick(SYMBOL)

        if tick is None:
            return

        # -------------------------------------------------
        # Entry Logic
        # -------------------------------------------------

        if position is None:

            direction = "BUY" if pred > 0 else "SELL"

            price = tick.ask if direction == "BUY" else tick.bid

            if self._open_trade(direction, price):
                self.cooldown_timestamp = now

            return

        # -------------------------------------------------
        # Position Management Logic
        # -------------------------------------------------

        profit = position.profit

        # Take profit protection
        if profit > 0.5:

            if self._close_position(position):
                self.cooldown_timestamp = now

            return

        # Loss recovery logic
        if profit < -1:

            opposite_signal = (
                pred > 0 and position.type == mt5.ORDER_TYPE_SELL
            ) or (
                pred < 0 and position.type == mt5.ORDER_TYPE_BUY
            )

            if opposite_signal:

                self._close_position(position)

                direction = "BUY" if pred > 0 else "SELL"
                price = tick.ask if direction == "BUY" else tick.bid

                self._open_trade(direction, price)

                self.cooldown_timestamp = now

    # -------------------------------------------------

    def _open_trade(self, direction, price):

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
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
            print("Brain opened trade:", direction)

        return success

    # -------------------------------------------------

    def _close_position(self, position):

        tick = mt5.symbol_info_tick(SYMBOL)

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
            "symbol": SYMBOL,
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
            print("Brain closed position")

        return success