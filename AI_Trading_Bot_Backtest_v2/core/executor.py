# filename: executor.py

import MetaTrader5 as mt5


from core.logger import log


from config_core import (

    SYMBOLS,

    STOP_LOSS_PIPS,

    TAKE_PROFIT_PIPS,

    TRADE_LOT,

    MT5_MAGIC,

    DEVIATION

)





# =====================================================
# MT5 LIVE EXECUTOR
# =====================================================

class BrainExecutor:



    def __init__(

            self,

            capital=1000

    ):


        self.capital = capital


        self.magic = MT5_MAGIC



        log(

            "INFO | MT5 Executor initialized"

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
    # POSITION CHECK
    # =====================================================


    def has_open_trade(

            self,

            symbol

    ):


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


    def get_position(

            self,

            symbol

    ):


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


    def get_symbol_positions(

            self,

            symbol

    ):


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


    def _calculate_lot(

            self,

            symbol

    ):


        return TRADE_LOT





    # =====================================================
    # OPEN TRADE
    # =====================================================


    def open_trade(

            self,

            symbol,

            direction,

            lot=None

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






            pip = self.pip_size(symbol)







            # =====================================
            # BUY
            # =====================================


            if direction == "BUY":


                order_type = mt5.ORDER_TYPE_BUY


                price = tick.ask



                sl = (

                    price

                    -

                    STOP_LOSS_PIPS * pip

                )



                tp = (

                    price

                    +

                    TAKE_PROFIT_PIPS * pip

                )






            # =====================================
            # SELL
            # =====================================


            elif direction == "SELL":


                order_type = mt5.ORDER_TYPE_SELL


                price = tick.bid



                sl = (

                    price

                    +

                    STOP_LOSS_PIPS * pip

                )



                tp = (

                    price

                    -

                    TAKE_PROFIT_PIPS * pip

                )





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

                    f"ERROR | MT5 rejected "

                    f"{result.retcode}"

                )


                return False






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
    # UPDATE PRICE
    # =====================================================


    def update_price(

            self,

            symbol,

            price,

            candle_time=None

    ):


        # MT5 manages floating P/L itself

        return False







    # =====================================================
    # CLOSE POSITION
    # =====================================================


    def close_position(

            self,

            position

    ):


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