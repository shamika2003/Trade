# filename: paper_executor.py

from datetime import datetime

from core.logger import log
from core.trade_logger import TradeLogger


from config_core import (

    SYMBOLS,

    TRADE_LOT,

    TAKE_PROFIT_PIPS,

    STOP_LOSS_PIPS,

    COMMISSION_PER_LOT,

    DEFAULT_SPREAD_PIPS

)



class PaperExecutor:



    def __init__(

            self,

            capital=1000

    ):



        self.initial_capital = capital


        self.balance = capital


        self.equity = capital



        self.positions = {}



        self.trade_history = []



        self.trade_logger = TradeLogger()



        log(

            "INFO | Paper Executor initialized"

        )





    # =====================================================
    # POSITION API
    # =====================================================


    def has_open_trade(

            self,

            symbol

    ):


        return symbol in self.positions





    def get_position(

            self,

            symbol

    ):


        return self.positions.get(symbol)





    def get_symbol_positions(

            self,

            symbol

    ):



        position = self.get_position(symbol)



        if position:


            return [position]


        return []





    def get_all_positions(self):


        return list(

            self.positions.values()

        )






    # =====================================================
    # PIP SIZE
    # =====================================================


    def pip_size(

            self,

            symbol

    ):


        if "JPY" in symbol:


            return 0.01



        return 0.0001





    # =====================================================
    # SLIPPAGE
    # =====================================================


    def slippage_price(

            self,

            symbol,

            price,

            direction

    ):


        pip = self.pip_size(symbol)



        slippage = (

            0.2

            *

            pip

        )



        if direction == "BUY":


            return price + slippage



        else:


            return price - slippage







    # =====================================================
    # OPEN TRADE
    # =====================================================


    def open_trade(

            self,

            symbol,

            direction,

            price,

            lot=TRADE_LOT,

            candle_time=None

    ):



        try:



            if symbol not in SYMBOLS:


                return False





            if self.has_open_trade(symbol):


                return False






            pip = self.pip_size(symbol)



            spread = (

                DEFAULT_SPREAD_PIPS

                *

                pip

            )





            entry = float(price)



            # spread simulation


            if direction == "BUY":


                entry += spread / 2



            else:


                entry -= spread / 2





            # slippage


            entry = self.slippage_price(

                symbol,

                entry,

                direction

            )






            position = {



                "symbol":

                symbol,



                "type":

                direction,



                "volume":

                lot,



                "entry_price":

                entry,



                "current_price":

                entry,



                "exit_price":

                None,



                "profit":

                0,



                "pips":

                0,



                "commission":

                COMMISSION_PER_LOT * lot,



                "open_time":

                (

                    candle_time

                    if candle_time is not None

                    else datetime.now()

                ),



                "close_time":

                None,



                "exit_reason":

                None,



                "status":

                "OPEN"

            }





            self.positions[symbol] = position




            log(

                f"INFO | PAPER OPEN "

                f"{symbol} "

                f"{direction} "

                f"{entry}"

            )




            return True




        except Exception as e:



            log(

                f"ERROR | Paper open failed {e}"

            )


            return False







    # =====================================================
    # UPDATE PRICE
    # =====================================================


    def update_price(
            self,
            symbol,
            price,
            candle_time=None
    ):


        if symbol not in self.positions:

            return False



        pos = self.positions[symbol]


        price = float(price)


        pos["current_price"] = price



        pip = self.pip_size(symbol)



        if pos["type"] == "BUY":

            diff = price - pos["entry_price"]

        else:

            diff = pos["entry_price"] - price



        pips = diff / pip



        pos["pips"] = round(
            pips,
            2
        )


        profit = (

            pips

            *

            10

            *

            pos["volume"]

        )


        profit -= pos["commission"]



        pos["profit"] = round(
            profit,
            2
        )



        return self.check_exit(

            symbol,

            candle_time

        )






    # =====================================================
    # EXIT CHECK
    # =====================================================


    def check_exit(

            self,

            symbol,

            candle_time=None

    ):



        pos = self.positions.get(symbol)



        if pos is None:


            return False





        if pos["pips"] >= TAKE_PROFIT_PIPS:



            return self.close_position(

                symbol,

                "TAKE_PROFIT",

                candle_time

            )





        if pos["pips"] <= -STOP_LOSS_PIPS:



            return self.close_position(

                symbol,

                "STOP_LOSS",

                candle_time

            )




        return False






    # =====================================================
    # CLOSE POSITION
    # =====================================================


    def close_position(

            self,

            symbol,

            reason,

            candle_time=None

    ):



        if symbol not in self.positions:


            return False





        pos = self.positions.pop(symbol)




        pos["status"] = "CLOSED"



        pos["exit_reason"] = reason




        pos["close_time"] = (

            candle_time

            if candle_time is not None

            else datetime.now()

        )




        pos["exit_price"] = pos["current_price"]





        self.balance += pos["profit"]


        self.equity = self.balance





        self.trade_history.append(

            pos.copy()

        )





        self.trade_logger.save_trade(

            pos

        )





        log(

            f"INFO | PAPER CLOSE "

            f"{symbol} "

            f"{reason} "

            f"profit={pos['profit']}"

        )



        return True





    # =====================================================
    # RESET
    # =====================================================


    def reset(self):


        self.balance = self.initial_capital


        self.equity = self.initial_capital


        self.positions.clear()


        self.trade_history.clear()