# filename: executor.py

import MetaTrader5 as mt5
import time

from config import TRADE_LOT, MAX_OPEN_TRADES, MAX_TOTAL_TRADES


# =====================================================
# Position Capacity Control
# =====================================================

def can_open_trade(symbol):

    # Symbol level protection
    positions_symbol = mt5.positions_get(symbol=symbol)

    if positions_symbol is not None:
        if len(positions_symbol) >= MAX_OPEN_TRADES:
            return False

    # Portfolio level protection
    positions_all = mt5.positions_get()

    if positions_all is not None:
        if len(positions_all) >= MAX_TOTAL_TRADES:
            print("Trade blocked: Portfolio trade limit reached")
            return False

    return True


# =====================================================
# Safe Brain Trade Executor
# =====================================================

class BrainExecutor:

    # -----------------------------------------
    # Internal Order Sender
    # -----------------------------------------

    def _send_order(self, request):

        for _ in range(3):

            result = mt5.order_send(request)

            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                return True

            time.sleep(0.5)

        return False

    # -----------------------------------------
    # Open Trade
    # -----------------------------------------

    def open_trade(self, symbol, direction):

        if not can_open_trade(symbol):
            print(f"{symbol}: Trade blocked (risk limit)")
            return False

        if direction not in ["BUY", "SELL"]:
            print("Invalid trade direction")
            return False

        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            print(f"{symbol}: Tick data not available")
            return False

        if direction == "BUY":
            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
        else:
            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL

        if price is None or price <= 0:
            print(f"{symbol}: Invalid market price")
            return False

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": TRADE_LOT,
            "type": order_type,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_DEMO_BOT",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        success = self._send_order(request)

        if success:
            print(f"{symbol}: Brain opened trade {direction}")

        return success

    # -----------------------------------------
    # Close Position
    # -----------------------------------------

    def close_position(self, position):

        symbol = position.symbol

        tick = mt5.symbol_info_tick(symbol)

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
            "symbol": symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        success = self._send_order(request)

        if success:
            print(f"{symbol}: Brain closed position")

        return success