import MetaTrader5 as mt5
import time

SYMBOL = "EURUSD"

def test_trade():

    print("Initializing MT5...")

    if not mt5.initialize():
        print("MT5 initialize failed")
        return

    print("MT5 connected:", mt5.terminal_info() is not None)

    mt5.symbol_select(SYMBOL, True)

    tick = mt5.symbol_info_tick(SYMBOL)

    if tick is None:
        print("Tick data not available")
        return

    price = tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 50,
        "magic": 7777,
        "comment": "TEST_ORDER",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print("Sending test order...")

    result = mt5.order_send(request)

    print("Result:", result)

    if result is not None:
        print("Retcode:", result.retcode)

    mt5.shutdown()

if __name__ == "__main__":
    test_trade()