# filename: executor.py

import MetaTrader5 as mt5
import time
import os
import csv

from config import (
    TRADE_LOT,
    MAX_OPEN_TRADES,
    MAX_TOTAL_TRADES,
    TAKE_PROFIT,
    STOP_LOSS,
    MAX_RETRY_EXECUTION
)

LOG_FILE = "executor_log.csv"


# =====================================================
# Risk Protection Layer
# =====================================================
def can_open_trade(symbol):

    if not mt5.terminal_info():
        print("MT5 terminal disconnected")
        return False

    positions_symbol = mt5.positions_get(symbol=symbol)

    if positions_symbol is not None and len(positions_symbol) >= MAX_OPEN_TRADES:
        print(f"{symbol}: Max symbol trades reached")
        return False

    positions_all = mt5.positions_get()

    if positions_all is not None and len(positions_all) >= MAX_TOTAL_TRADES:
        print("Trade blocked: portfolio limit reached")
        return False

    return True


# =====================================================
# Brain Trade Executor
# =====================================================
class BrainExecutor:

    def __init__(self, capital=None):

        self.capital = capital or 0

        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "symbol",
                    "signal",
                    "price",
                    "profit",
                    "action",
                    "reason"
                ])

        print(f"BrainExecutor initialized with capital: {self.capital} USD")


    # -----------------------------------------
    # Safe MT5 Order Sender
    # -----------------------------------------
    def _send_order(self, request):

        for attempt in range(MAX_RETRY_EXECUTION):

            if not mt5.terminal_info():
                print("MT5 connection lost")
                return False

            result = mt5.order_send(request)

            if result is None:
                time.sleep(0.5)
                continue

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return True

            print(f"Order failed retcode={result.retcode}")
            time.sleep(0.5)

        return False


    # -----------------------------------------
    # Normalize lot size
    # -----------------------------------------
    def _normalize_lot(self, symbol, lot):

        info = mt5.symbol_info(symbol)

        if info is None:
            return lot

        step = info.volume_step
        min_lot = info.volume_min
        max_lot = info.volume_max

        lot = max(min_lot, min(lot, max_lot))
        lot = round(lot / step) * step

        return lot


    # -----------------------------------------
    # Open Trade
    # -----------------------------------------
    def open_trade(self, symbol, direction, lot=None):

        if not can_open_trade(symbol):
            return False

        symbol_info = mt5.symbol_info(symbol)

        if symbol_info is None:
            print(f"{symbol}: symbol not found")
            return False

        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            return False

        lot = self._normalize_lot(symbol, lot or TRADE_LOT)

        if direction == "BUY":
            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
            sl = price - STOP_LOSS * symbol_info.point
            tp = price + TAKE_PROFIT * symbol_info.point

        elif direction == "SELL":
            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL
            sl = price + STOP_LOSS * symbol_info.point
            tp = price - TAKE_PROFIT * symbol_info.point

        else:
            return False

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_BRAIN",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        success = self._send_order(request)

        if success:
            print(f"{symbol}: OPEN {direction} @ {price}")
            self._log_trade(symbol, direction, price, 0, "OPEN", "Signal")

        return success


    # -----------------------------------------
    # Close Trade
    # -----------------------------------------
    def close_position(self, position, reason="CLOSE"):

        symbol = position.symbol

        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            return False

        if position.type == mt5.ORDER_TYPE_BUY:

            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL
            signal = "SELL"

        else:

            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
            signal = "BUY"

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        success = self._send_order(request)

        if success:
            print(f"{symbol}: CLOSE @ {price} | {reason}")
            self._log_trade(symbol, signal, price, position.profit, "CLOSE", reason)

        return success


    # -----------------------------------------
    # Logging
    # -----------------------------------------
    def _log_trade(self, symbol, signal, price, profit, action, reason):

        with open(LOG_FILE, "a", newline="") as f:

            writer = csv.writer(f)

            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                symbol,
                signal,
                round(price, 5),
                round(profit, 2),
                action,
                reason
            ])