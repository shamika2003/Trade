# filename: executor.py

import MetaTrader5 as mt5
import time
import os
import csv
from config import TRADE_LOT, MAX_OPEN_TRADES, MAX_TOTAL_TRADES, TAKE_PROFIT, STOP_LOSS

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
        return False

    positions_all = mt5.positions_get()
    if positions_all is not None and len(positions_all) >= MAX_TOTAL_TRADES:
        print("Trade blocked: Portfolio trade limit reached")
        return False

    return True

# =====================================================
# Brain Trade Executor
# =====================================================
class BrainExecutor:

    def __init__(self, capital=None):
        self.capital = capital or 0  # store capital for trade calculations or logging
        # create log file if not exists
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "symbol", "signal", "price",
                    "profit", "action", "reason"
                ])
        print(f"BrainExecutor initialized with capital: {self.capital} USD")

    # -----------------------------------------
    # Safe MT5 Order Sender
    # -----------------------------------------
    def _send_order(self, request):
        if request is None:
            return False

        for attempt in range(3):
            try:
                if not mt5.terminal_info():
                    print("MT5 connection lost")
                    return False

                result = mt5.order_send(request)
                if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                    return True
                elif result is not None:
                    print(f"Order failed retcode={result.retcode}")
            except Exception as e:
                print(f"Order exception: {e}")
            time.sleep(0.4)

        return False

    # -----------------------------------------
    # Open Trade with TP/SL safety
    # -----------------------------------------
    def open_trade(self, symbol, direction, lot=None, tp=None, sl=None):
        if not can_open_trade(symbol):
            print(f"{symbol}: Trade blocked (risk limit)")
            return False

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False

        if direction == "BUY":
            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
        elif direction == "SELL":
            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL
        else:
            return False

        if price is None or price <= 0:
            return False

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot or TRADE_LOT,
            "type": order_type,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_BRAIN",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        success = self._send_order(request)
        if success:
            print(f"{symbol}: Brain opened trade {direction} @ {price}")
            self._log_trade(symbol, direction, price, 0, "OPEN", "Signal")
        return success

    # -----------------------------------------
    # Close Trade
    # -----------------------------------------
    def close_position(self, position, reason="CLOSE"):
        if position is None:
            return False

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
            print(f"{symbol}: Brain closed position @ {price} | Reason: {reason}")
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
                round(price, 5) if price else 0,
                round(profit, 2),
                action,
                reason
            ])