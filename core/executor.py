# filename: executor.py

import MetaTrader5 as mt5
import time

from config import SYMBOL, TRADE_LOT, MAX_OPEN_TRADES


# =====================================================
# Position Capacity Control
# =====================================================

def can_open_trade():

    positions = mt5.positions_get(symbol=SYMBOL)

    if positions is None:
        return True

    return len(positions) < MAX_OPEN_TRADES


# =====================================================
# Safe Trade Executor
# =====================================================

def execute_trade(direction):

    if not can_open_trade():
        print("Trade blocked: Max position limit reached")
        return

    if direction not in ["BUY", "SELL"]:
        print("Invalid trade direction")
        return

    for attempt in range(3):

        tick = mt5.symbol_info_tick(SYMBOL)

        if tick is None:
            print("Tick data not available")
            time.sleep(1)
            continue

        if direction == "BUY":
            price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
        else:
            price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL

        # Prevent invalid price execution
        if price is None or price <= 0:
            print("Invalid market price")
            time.sleep(1)
            continue

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": TRADE_LOT,
            "type": order_type,
            "price": price,
            "deviation": 50,
            "magic": 7777,
            "comment": "ML_DEMO_BOT",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is not None:

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print("Trade executed successfully:", direction)
                return

            else:
                print("Trade execution failed retcode:", result.retcode)

        time.sleep(1)

    print("Trade failed after retries")