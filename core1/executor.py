# filename: executor.py

import MetaTrader5 as mt5

from core.logger import log
from config_core import SYMBOLS


# =====================================================
# EXECUTOR (LIVE MT5 ORDER HANDLER)
# =====================================================
class BrainExecutor:


    def __init__(self, capital=1000):

        self.capital = capital

        log(
            "INFO | Executor initialized"
        )



    # =================================================
    # CHECK OPEN TRADE
    # =================================================
    def has_open_trade(self, symbol):

        try:

            positions = mt5.positions_get(
                symbol=symbol
            )

            return (
                positions is not None
                and
                len(positions) > 0
            )


        except Exception as e:

            log(
                f"ERROR | Position check failed: {e}"
            )

            return False



    # =================================================
    # GET CURRENT POSITION
    # =================================================
    def get_position(self, symbol):

        try:

            positions = mt5.positions_get(
                symbol=symbol
            )


            if not positions:

                return None


            return positions[0]


        except Exception as e:

            log(
                f"ERROR | Get position failed: {e}"
            )

            return None



    # =================================================
    # LOT CALCULATION
    # =================================================
    def _calculate_lot(self, symbol):

        return 0.01



    # =================================================
    # OPEN TRADE
    # =================================================
    def open_trade(
            self,
            symbol,
            direction,
            lot=None
    ):

        try:


            if symbol not in SYMBOLS:

                log(
                    f"ERROR | Symbol not allowed: {symbol}"
                )

                return False



            lot = (
                lot
                or
                self._calculate_lot(symbol)
            )



            tick = mt5.symbol_info_tick(
                symbol
            )


            if tick is None:

                log(
                    f"ERROR | No tick data for {symbol}"
                )

                return False



            # -----------------------------
            # BUY
            # -----------------------------
            if direction == "BUY":


                request = {

                    "action":
                    mt5.TRADE_ACTION_DEAL,

                    "symbol":
                    symbol,

                    "volume":
                    lot,

                    "type":
                    mt5.ORDER_TYPE_BUY,

                    "price":
                    tick.ask,

                    "deviation":
                    20,

                    "magic":
                    123456,

                    "comment":
                    "AI BUY",

                    "type_time":
                    mt5.ORDER_TIME_GTC,

                    "type_filling":
                    mt5.ORDER_FILLING_IOC,
                }



            # -----------------------------
            # SELL
            # -----------------------------
            elif direction == "SELL":


                request = {

                    "action":
                    mt5.TRADE_ACTION_DEAL,

                    "symbol":
                    symbol,

                    "volume":
                    lot,

                    "type":
                    mt5.ORDER_TYPE_SELL,

                    "price":
                    tick.bid,

                    "deviation":
                    20,

                    "magic":
                    123456,

                    "comment":
                    "AI SELL",

                    "type_time":
                    mt5.ORDER_TIME_GTC,

                    "type_filling":
                    mt5.ORDER_FILLING_IOC,
                }



            else:

                log(
                    f"WARNING | Invalid direction {direction}"
                )

                return False




            result = mt5.order_send(
                request
            )



            if result is None:

                log(
                    "ERROR | Order send returned None"
                )

                return False



            if result.retcode != mt5.TRADE_RETCODE_DONE:

                log(
                    f"ERROR | Order failed: {result.retcode}"
                )

                return False



            log(
                f"INFO | ORDER SUCCESS "
                f"{symbol} {direction} lot={lot}"
            )


            return True



        except Exception as e:

            log(
                f"ERROR | open_trade failed: {e}"
            )

            return False




    # =================================================
    # CLOSE POSITION
    # =================================================
    def close_position(self, position):

        try:


            symbol = position.symbol

            volume = position.volume



            tick = mt5.symbol_info_tick(
                symbol
            )


            if tick is None:

                log(
                    f"ERROR | No tick for close {symbol}"
                )

                return False




            if position.type == mt5.POSITION_TYPE_BUY:


                order_type = (
                    mt5.ORDER_TYPE_SELL
                )

                price = tick.bid



            else:


                order_type = (
                    mt5.ORDER_TYPE_BUY
                )

                price = tick.ask




            request = {

                "action":
                mt5.TRADE_ACTION_DEAL,

                "symbol":
                symbol,

                "volume":
                volume,

                "type":
                order_type,

                "price":
                price,

                "deviation":
                20,

                "magic":
                123456,

                "comment":
                "AI CLOSE",

                "type_time":
                mt5.ORDER_TIME_GTC,

                "type_filling":
                mt5.ORDER_FILLING_IOC,
            }




            result = mt5.order_send(
                request
            )



            if (
                result is None
                or
                result.retcode != mt5.TRADE_RETCODE_DONE
            ):

                log(
                    f"ERROR | Close failed: {symbol}"
                )

                return False



            log(
                f"INFO | POSITION CLOSED {symbol}"
            )


            return True



        except Exception as e:


            log(
                f"ERROR | close_position failed: {e}"
            )

            return False