# filename: executor.py

import MetaTrader5 as mt5

from datetime import datetime, timedelta

from core.logger import log
from core.trade_logger import TradeLogger

from config_core import (
    SYMBOLS,
    TRADE_LOT,
    MT5_MAGIC,
    DEVIATION,
    ATR_SL_MULTIPLIER,
    ATR_TP_MULTIPLIER
)


# =====================================================
# MT5 LIVE EXECUTOR
# =====================================================

class BrainExecutor:


    def __init__(self, capital=1000):

        self.capital = capital

        self.magic = MT5_MAGIC


        # trade logger
        self.trade_logger = TradeLogger()


        # local trade memory
        self.open_trades = {}


        log(
            "INFO | MT5 Executor initialized"
        )



    # =====================================================
    # PIP SIZE
    # =====================================================

    def pip_size(self, symbol):

        if "JPY" in symbol:
            return 0.01

        return 0.0001



    # =====================================================
    # POSITION CHECK
    # =====================================================

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
                f"ERROR | Position check failed {e}"
            )

            return False




    # =====================================================
    # GET POSITION
    # =====================================================

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
                f"ERROR | Get position failed {e}"
            )

            return None




    # =====================================================
    # RISK COMPATIBILITY
    # =====================================================

    def get_symbol_positions(self, symbol):

        positions = mt5.positions_get(
            symbol=symbol
        )


        if not positions:
            return []


        return list(positions)



    def get_all_positions(self):

        positions = mt5.positions_get()


        if not positions:
            return []


        return list(positions)




    # =====================================================
    # LOT SIZE
    # =====================================================

    def _calculate_lot(self, symbol):

        return TRADE_LOT




    # =====================================================
    # OPEN TRADE
    # =====================================================

    def open_trade(
            self,
            symbol,
            direction,
            price=None,
            lot=None,
            atr=None,
            candle_time=None
    ):


        try:


            if symbol not in SYMBOLS:

                log(
                    f"ERROR | Symbol blocked {symbol}"
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
                    f"ERROR | Tick missing {symbol}"
                )

                return False




            if atr is None:

                log(
                    f"ERROR | ATR missing {symbol}"
                )

                return False




            sl_distance = atr * ATR_SL_MULTIPLIER

            tp_distance = atr * ATR_TP_MULTIPLIER




            # BUY

            if direction == "BUY":

                order_type = mt5.ORDER_TYPE_BUY

                price = tick.ask

                sl = price - sl_distance

                tp = price + tp_distance




            # SELL

            elif direction == "SELL":

                order_type = mt5.ORDER_TYPE_SELL

                price = tick.bid

                sl = price + sl_distance

                tp = price - tp_distance



            else:

                return False





            request = {

                "action":
                mt5.TRADE_ACTION_DEAL,


                "symbol":
                symbol,


                "volume":
                lot,


                "type":
                order_type,


                "price":
                price,


                "sl":
                sl,


                "tp":
                tp,


                "deviation":
                DEVIATION,


                "magic":
                self.magic,


                "comment":
                "AI TRADING BOT",


                "type_time":
                mt5.ORDER_TIME_GTC,


                "type_filling":
                mt5.ORDER_FILLING_IOC

            }





            result = mt5.order_send(
                request
            )



            if result is None:

                log(
                    "ERROR | MT5 order failed None"
                )

                return False




            if result.retcode != mt5.TRADE_RETCODE_DONE:


                log(
                    f"ERROR | MT5 rejected {result.retcode}"
                )

                return False





            # save local open trade

            self.open_trades[symbol] = {


                "symbol":
                symbol,


                "type":
                direction,


                "entry_price":
                price,


                "volume":
                lot,


                "open_time":
                (
                    candle_time
                    if candle_time
                    else datetime.now()
                )

            }





            log(
                f"INFO | MT5 OPEN "
                f"{symbol} "
                f"{direction} "
                f"lot={lot}"
            )


            return True




        except Exception as e:


            log(
                f"ERROR | MT5 open failed {e}"
            )

            return False






    # =====================================================
    # CHECK CLOSED TRADES AND SAVE HISTORY
    # =====================================================

    def check_closed_trades(self):


        try:


            for symbol, trade in list(
                self.open_trades.items()
            ):



                # still open

                if self.has_open_trade(symbol):

                    continue





                start_time = trade["open_time"]


                if not isinstance(
                    start_time,
                    datetime
                ):

                    start_time = datetime.now() - timedelta(days=7)




                end_time = datetime.now()





                deals = mt5.history_deals_get(

                    start_time,

                    end_time

                )




                if not deals:

                    continue





                profit = 0

                exit_price = None




                for deal in deals:


                    if deal.symbol == symbol:


                        profit += deal.profit


                        exit_price = deal.price





                closed_trade = {

                    "symbol": symbol,

                    "type": trade["type"],

                    "entry_price": trade["entry_price"],

                    "current_price": exit_price,

                    "exit_price": exit_price,

                    "volume": trade["volume"],

                    "profit": round(profit, 2),

                    "open_time": start_time,

                    "close_time": end_time,

                    "exit_reason": "MT5_CLOSE"

                }





                self.trade_logger.save_trade(
                    closed_trade
                )




                del self.open_trades[symbol]




                log(
                    f"INFO | Live trade saved {symbol}"
                )




        except Exception as e:


            log(
                f"ERROR | Closed trade checker failed {e}"
            )






    # =====================================================
    # UPDATE PRICE
    # =====================================================

    def update_price(
            self,
            symbol,
            price,
            candle_time=None
    ):

        # MT5 handles SL / TP internally

        return False






    # =====================================================
    # CLOSE POSITION
    # =====================================================

    def close_position(self, position):


        try:


            symbol = position.symbol


            volume = position.volume



            tick = mt5.symbol_info_tick(
                symbol
            )



            if tick is None:

                return False





            if position.type == mt5.POSITION_TYPE_BUY:


                order_type = mt5.ORDER_TYPE_SELL

                price = tick.bid



            else:


                order_type = mt5.ORDER_TYPE_BUY

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


                "position":
                position.ticket,


                "price":
                price,


                "deviation":
                DEVIATION,


                "magic":
                self.magic,


                "comment":
                "AI CLOSE"

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
                    f"ERROR | Close failed {symbol}"
                )


                return False






            log(
                f"INFO | MT5 CLOSED {symbol}"
            )


            return True





        except Exception as e:


            log(
                f"ERROR | Close position failed {e}"
            )


            return False