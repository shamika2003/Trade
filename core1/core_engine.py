# filename: core_engine.py

from core.predictor import Predictor
from core.signal_engine import decide_signal
from core.logger import log

from config_core import SYMBOLS, SIGNAL_THRESHOLD


# =====================================================
# CORE ENGINE (BRAIN ORCHESTRATOR)
# =====================================================
class CoreEngine:


    def __init__(
            self,
            executor,
            capital=1000
    ):

        self.capital = capital


        self.predictors = {
            s: Predictor()
            for s in SYMBOLS
        }


        # =================================================
        # EXECUTOR INJECTION
        #
        # LIVE:
        #     BrainExecutor -> MT5
        #
        # OFFLINE:
        #     PaperExecutor -> Simulation
        # =================================================
        self.executor = executor


        self.last_signal = {}


        log(
            "INFO | Core Engine initialized"
        )



    # =================================================
    # CHECK OPEN POSITIONS
    # DELEGATED TO EXECUTOR
    # =================================================
    def _has_open_trade(
            self,
            symbol
    ):

        try:

            return self.executor.has_open_trade(
                symbol
            )


        except Exception as e:

            log(
                f"ERROR | Position check failed: {e}"
            )

            return False



    # =================================================
    # AVOID REPEATED SIGNALS
    # =================================================
    def _is_repeated_signal(
            self,
            symbol,
            signal
    ):


        if self.last_signal.get(symbol) == signal:

            return True


        self.last_signal[symbol] = signal

        return False



    # =================================================
    # PROCESS ONE SYMBOL
    # =================================================
    def process(
            self,
            symbol,
            df
    ):

        try:


            # -----------------------------
            # ACTIVE TRADE MANAGEMENT
            # -----------------------------
            if self._has_open_trade(symbol):

                self._manage_open_trade(
                    symbol
                )

                return



            # -----------------------------
            # PREDICTION
            # -----------------------------
            predictor = (
                self.predictors[symbol]
            )


            result = predictor.predict(
                df,
                None,
                symbol
            )


            if result is None:

                return



            signal_value = result["signal"]

            confidence = result["confidence"]



            log(
                f"DEBUG | {symbol} "
                f"signal={signal_value:.6f} "
                f"conf={confidence:.2f}"
            )



            # -----------------------------
            # SIGNAL STRENGTH FILTER
            # -----------------------------
            if abs(signal_value) < SIGNAL_THRESHOLD:

                return



            # -----------------------------
            # CONFIDENCE FILTER
            # -----------------------------
            if confidence < 0.0:

                return



            # -----------------------------
            # ML -> TRADE SIGNAL
            # -----------------------------
            signal = decide_signal(
                signal_value
            )


            if signal is None:

                return



            # -----------------------------
            # DUPLICATE SIGNAL FILTER
            # -----------------------------
            if self._is_repeated_signal(
                symbol,
                signal
            ):

                return



            log(
                f"INFO | {symbol} SIGNAL "
                f"-> {signal} "
                f"| conf={confidence:.2f}"
            )



            # -----------------------------
            # EXECUTION
            # -----------------------------
            success = self.executor.open_trade(
                symbol=symbol,
                direction=signal,
                lot=None
            )



            if success:

                log(
                    f"INFO | TRADE OPENED -> {symbol}"
                )



        except Exception as e:

            log(
                f"ERROR | CoreEngine {symbol}: {e}"
            )



    # =================================================
    # MANAGE OPEN TRADE
    # =================================================
    def _manage_open_trade(
            self,
            symbol
    ):


        position = (
            self.executor.get_position(symbol)
        )


        if position is None:

            return



        if isinstance(position, dict):

            profit = float(
                position.get(
                    "profit",
                    0
                )
            )

        else:

            profit = float(
                position.profit
            )



        # -----------------------------
        # SIMPLE EXIT RULE
        # -----------------------------
        if profit > 2.0 or profit < -2.0:


            log(
                f"INFO | Closing {symbol} "
                f"| profit={profit:.2f}"
            )


            self.executor.close_position(
                position
            )