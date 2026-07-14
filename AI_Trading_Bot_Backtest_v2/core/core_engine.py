from core.predictor import Predictor
from core.signal_engine import decide_signal
from core.risk_manager import RiskManager
from core.logger import log


from config_core import (
    SYMBOLS,
    SIGNAL_THRESHOLD,
    MAX_OPEN_TRADES,
    MIN_CONFIDENCE,
    MAX_TOTAL_TRADES,
    COOLDOWN_SECONDS
)



# =====================================================
# CORE ENGINE
# =====================================================

class CoreEngine:


    def __init__(
            self,
            executor,
            capital=1000
    ):


        self.capital = capital

        self.executor = executor



        self.risk = RiskManager(

            executor=self.executor,

            max_open_trades=MAX_OPEN_TRADES,

            max_total_trades=MAX_TOTAL_TRADES,

            cooldown_seconds=COOLDOWN_SECONDS

        )



        self.predictors = {

            symbol:

            Predictor()

            for symbol in SYMBOLS

        }



        self.last_signal = {}



        log(
            "INFO | Core Engine initialized"
        )




    # =====================================================
    # RESET SIGNAL
    # =====================================================

    def reset_signal(
            self,
            symbol
    ):

        self.last_signal.pop(
            symbol,
            None
        )





    # =====================================================
    # PROCESS MARKET
    # =====================================================

    def process(
            self,
            symbol,
            df,
            candle_time=None
    ):


        try:


            if df is None or df.empty:

                return




            # =========================================
            # CURRENT PRICE
            # =========================================

            current_price = float(

                df["close"].iloc[-1]

            )


            # =========================================
            # CURRENT ATR
            # =========================================

            current_atr = float(
                df["atr"].iloc[-1]
            )




            # =========================================
            # FALLBACK TIME
            # =========================================

            if candle_time is None:


                if "time" in df.columns:

                    candle_time = df["time"].iloc[-1]



            # =========================================
            # MANAGE EXISTING POSITION
            # =========================================

            if self.executor.has_open_trade(symbol):


                if hasattr(
                    self.executor,
                    "update_price"
                ):


                    closed = self.executor.update_price(

                        symbol=symbol,

                        price=current_price,

                        candle_time=candle_time

                    )



                    if closed:


                        self.reset_signal(
                            symbol
                        )


                        self.risk.register_trade_close(

                            symbol,

                            candle_time

                        )


                        log(

                            f"INFO | CLOSED POSITION {symbol}"

                        )


                return






            # =========================================
            # AI PREDICTION
            # =========================================

            predictor = self.predictors.get(symbol)



            if predictor is None:


                log(

                    f"ERROR | Predictor missing {symbol}"

                )

                return





            result = predictor.predict(

                df,

                None,

                symbol

            )



            if result is None:

                return





            signal_value = float(

                result["signal"]

            )


            confidence = float(

                result["confidence"]

            )

            if confidence < MIN_CONFIDENCE:

                log(
                    f"DEBUG | {symbol} confidence too low "
                    f"{confidence:.2f}"
                )

                return



            log(

                f"DEBUG | {symbol} "

                f"signal={signal_value:.6f} "

                f"confidence={confidence:.2f}"

            )





            # =========================================
            # SIGNAL THRESHOLD
            # =========================================

            if abs(signal_value) < SIGNAL_THRESHOLD:

                return





            signal = decide_signal(

                signal_value

            )



            if signal is None:

                return






            # =========================================
            # DUPLICATE SIGNAL
            # =========================================

            if self.last_signal.get(symbol) == signal:

                return





            # =========================================
            # RISK CHECK
            # =========================================

            if not self.risk.can_trade(

                symbol,

                candle_time

            ):


                log(

                    f"DEBUG | Risk blocked {symbol}"

                )

                return





            # =========================================
            # OPEN TRADE
            # =========================================

            success = False



            try:


                success = self.executor.open_trade(

                    symbol=symbol,

                    direction=signal,

                    price=current_price,

                    lot=0.01,

                    atr=current_atr,

                    candle_time=candle_time

                )



            except TypeError:


                # MT5 executor compatibility

                success = self.executor.open_trade(

                    symbol=symbol,

                    direction=signal,

                    price=current_price,

                    lot=0.01,
                    
                    atr=current_atr 

                )







            if success:


                self.last_signal[symbol] = signal



                self.risk.register_trade_open(

                    symbol,

                    candle_time

                )


                log(

                    f"INFO | TRADE OPENED {symbol}"

                )



            else:


                self.reset_signal(

                    symbol

                )






        except Exception as e:


            log(

                f"ERROR | CoreEngine {symbol}: {e}"

            )