# filename: executor.py

import MetaTrader5 as mt5
import time
import os
import csv

from config import (
    TRADE_LOT,
    MAX_OPEN_TRADES,
    MAX_TOTAL_TRADES,
    MAX_RETRY_EXECUTION,
    PRICE_VALIDATION_THRESHOLD
)

from core.logger import log

LOG_FILE = "executor_log.csv"


# =====================================================
# Risk Protection Layer
# =====================================================
def can_open_trade(symbol):
    if not mt5.terminal_info():  # type: ignore
        log("ERROR | MT5 terminal disconnected")
        return False

    positions_symbol = mt5.positions_get(symbol=symbol) or []  # type: ignore
    if len(positions_symbol) >= MAX_OPEN_TRADES:
        return False

    positions_all = mt5.positions_get() or []  # type: ignore
    if len(positions_all) >= MAX_TOTAL_TRADES:
        log("WARNING | Portfolio limit reached")
        return False

    return True


# =====================================================
# Executor (pure execution layer)
# =====================================================
class BrainExecutor:

    def __init__(self, capital=None):
        self.capital = capital or 0

        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "symbol", "signal", "price",
                    "sl", "tp", "profit", "action", "reason"
                ])

        log(f"INFO | Executor ready | Capital={self.capital}")

    # -----------------------------------------
    # Tick validation
    # -----------------------------------------
    def _valid_tick(self, tick):
        if tick is None:
            return False

        if tick.ask <= 0 or tick.bid <= 0:
            return False

        spread = abs(tick.ask - tick.bid)

        if spread <= 0:
            return False

        if spread > PRICE_VALIDATION_THRESHOLD:
            log(f"WARNING | High spread detected: {spread}")
            return False

        return True

    # -----------------------------------------
    # Safe order send
    # -----------------------------------------
    def _send_order(self, request):
        for attempt in range(MAX_RETRY_EXECUTION):
            try:
                if not mt5.terminal_info():  # type: ignore
                    log("ERROR | MT5 disconnected")
                    return False

                result = mt5.order_send(request)  # type: ignore

                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    return True

                if result:
                    log(f"WARNING | Order failed retcode={result.retcode}")

            except Exception as e:
                log(f"ERROR | Order exception: {e}")

            time.sleep(0.4)

        return False

    # -----------------------------------------
    # Open trade WITH REAL SL/TP
    # -----------------------------------------
    def open_trade(self, symbol, direction, lot=None, sl=None, tp=None):
        if not can_open_trade(symbol):
            return False

        tick = mt5.symbol_info_tick(symbol)  # type: ignore
        if not self._valid_tick(tick):
            return False

        if direction == "BUY":
            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
            sl_price = price - sl if sl else 0
            tp_price = price + tp if tp else 0

        elif direction == "SELL":
            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL
            sl_price = price + sl if sl else 0
            tp_price = price - tp if tp else 0
        else:
            return False

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot or TRADE_LOT,
            "type": order_type,
            "price": price,
            "sl": sl_price if sl else 0,
            "tp": tp_price if tp else 0,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_BRAIN",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        success = self._send_order(request)

        if success:
            log(f"INFO | {symbol} OPEN {direction} @ {price} SL={sl_price} TP={tp_price}")
            self._log_trade(symbol, direction, price, sl_price, tp_price, 0, "OPEN", "Signal")

        return success

    # -----------------------------------------
    # Close trade
    # -----------------------------------------
    def close_position(self, position, reason="CLOSE"):
        if position is None:
            return False

        symbol = position.symbol
        tick = mt5.symbol_info_tick(symbol)  # type: ignore

        if not self._valid_tick(tick):
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
            log(f"INFO | {symbol} CLOSE @ {price} | {reason}")
            self._log_trade(symbol, signal, price, 0, 0, position.profit, "CLOSE", reason)

        return success

    # -----------------------------------------
    # Logging
    # -----------------------------------------
    def _log_trade(self, symbol, signal, price, sl, tp, profit, action, reason):
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                symbol,
                signal,
                round(price, 5) if price else 0,
                round(sl, 5) if sl else 0,
                round(tp, 5) if tp else 0,
                round(profit, 2),
                action,
                reason
            ])