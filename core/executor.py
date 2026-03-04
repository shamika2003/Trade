import MetaTrader5 as mt5
from config import SYMBOL, TRADE_LOT, MAX_OPEN_TRADES

def can_open_trade():

    positions = mt5.positions_get(symbol=SYMBOL)

    if positions is None:
        return True

    return len(positions) < MAX_OPEN_TRADES


def execute_trade(direction):

    if not can_open_trade():
        return

    tick = mt5.symbol_info_tick(SYMBOL)

    if direction == "BUY":
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
    else:
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": TRADE_LOT,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 7777,
        "comment": "DEMO_ML_BOT",
    }

    mt5.order_send(request)