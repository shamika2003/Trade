import MetaTrader5 as mt5
from model.config import TRADE_LOT, SYMBOL

def execute_trade(direction):

    if not mt5.initialize():
        print("MT5 init failed")
        return

    symbol_tick = mt5.symbol_info_tick(SYMBOL)

    if direction == "BUY":
        price = symbol_tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = symbol_tick.bid
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": TRADE_LOT,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 7777,
        "comment": "ML_DEMO_BOT"
    }

    mt5.order_send(request)