# filename: demo_bot.py

import time
import signal


from config_core import (

    SYMBOLS,
    DATA_PATH,

    USE_OFFLINE,

    DEFAULT_CAPITAL,

    HISTORY_SIZE,

    BACKTEST_DELAY,

    LIVE_INTERVAL

)


from core.logger import log

from core.feature_engine import FeatureTransformer

from core.core_engine import CoreEngine

from core.command_control import CommandControl



# =====================================================
# CONDITIONAL IMPORTS
# =====================================================

if USE_OFFLINE:

    from core.paper_executor import PaperExecutor

    from core.replay_engine import ReplayEngine

    from core.performance import PerformanceAnalyzer


else:

    from core.executor import BrainExecutor

    from core.data_fetcher_online import (
        initialize_mt5,
        get_mtf_data
    )



# =====================================================
# GLOBAL CONTROL
# =====================================================

running = True



def stop_bot(sig, frame):

    global running

    running = False

    log(
        "INFO | Shutdown requested"
    )



signal.signal(
    signal.SIGINT,
    stop_bot
)


signal.signal(
    signal.SIGTERM,
    stop_bot
)




# =====================================================
# CREATE H1 FROM M5
# =====================================================

def create_h1(df):

    try:

        h1 = (

            df

            .set_index(
                "time"
            )

            .resample(
                "1h"
            )

            .agg(
                {

                    "open":
                    "first",

                    "high":
                    "max",

                    "low":
                    "min",

                    "close":
                    "last",

                    "tick_volume":
                    "sum",

                    "spread":
                    "mean",

                    "real_volume":
                    "sum"

                }
            )

            .dropna()

            .reset_index()

        )


        return h1



    except Exception as e:


        log(
            f"ERROR | H1 creation failed {e}"
        )


        return None





# =====================================================
# REPORT FUNCTION
# =====================================================

def create_report(executor):


    if not USE_OFFLINE:


        log(
            "INFO | Reports available only in CSV mode"
        )

        return



    log(
        "INFO | Creating backtest report"
    )


    analyzer = PerformanceAnalyzer(

        initial_balance=DEFAULT_CAPITAL

    )


    analyzer.analyze(

        executor.trade_history

    )


    log(
        "INFO | Report completed"
    )





# =====================================================
# MAIN
# =====================================================

def main():

    global running



    log(
        "INFO | Starting Trade AI"
    )



    # =================================================
    # EXECUTOR
    # =================================================

    if USE_OFFLINE:


        executor = PaperExecutor(

            capital=DEFAULT_CAPITAL

        )


        log(
            "INFO | PAPER EXECUTOR ENABLED"
        )



    else:


        if not initialize_mt5():


            log(
                "ERROR | MT5 initialization failed"
            )

            return



        executor = BrainExecutor(

            capital=DEFAULT_CAPITAL

        )


        log(
            "INFO | MT5 EXECUTOR ENABLED"
        )





    # =================================================
    # CORE ENGINE
    # =================================================

    core = CoreEngine(

        executor=executor

    )


    transformer = FeatureTransformer()





    # =================================================
    # DATA ENGINE
    # =================================================

    if USE_OFFLINE:


        replay = ReplayEngine(

            file_path=DATA_PATH,

            symbols=SYMBOLS,

            history_size=HISTORY_SIZE

        )


        log(
            "INFO | CSV BACKTEST MODE"
        )



    else:


        replay = None


        log(
            "INFO | LIVE MT5 MODE"
        )





    log(
        "INFO | Systems Ready"
    )





    # =================================================
    # COMMAND CONTROL
    # =================================================

    controller = CommandControl()


    controller.start()


    log(
        "INFO | Commands: stop / pause / resume / report / status / exit"
    )





    # =====================================================
    # OFFLINE BACKTEST
    # =====================================================

    if USE_OFFLINE:



        while running and controller.running:



            if controller.report_requested:


                controller.report_requested = False


                create_report(
                    executor
                )




            if controller.paused:


                time.sleep(1)

                continue






            market = replay.next_market_snapshot()



            if market is None:


                log(
                    "INFO | CSV completed"
                )


                while running and controller.running:


                    time.sleep(1)



                    if controller.report_requested:


                        controller.report_requested = False


                        create_report(
                            executor
                        )



                break





            replay_time = replay.get_current_time()





            for symbol, df_m5 in market.items():


                try:



                    if df_m5 is None:

                        continue



                    if len(df_m5) < HISTORY_SIZE:

                        continue




                    df_h1 = create_h1(
                        df_m5
                    )



                    if df_h1 is None:

                        continue



                    df_h1["symbol"] = symbol




                    df = transformer.build_multi_timeframe_features(

                        df_m5,

                        df_h1

                    )



                    if df is None or df.empty:

                        continue





                    core.process(

                        symbol,

                        df,

                        candle_time=replay_time

                    )





                except Exception as e:


                    log(
                        f"ERROR | {symbol}: {e}"
                    )





            time.sleep(
                BACKTEST_DELAY
            )






    # =====================================================
    # LIVE MT5 MODE
    # =====================================================

    else:



        while running and controller.running:



            # =========================================
            # CHECK CLOSED MT5 TRADES
            # =========================================

            if hasattr(
                executor,
                "check_closed_trades"
            ):

                executor.check_closed_trades()




            # =========================================
            # COMMANDS
            # =========================================

            if controller.paused:


                time.sleep(1)

                continue





            # =========================================
            # MARKET LOOP
            # =========================================

            for symbol in SYMBOLS:



                try:



                    df_m5, df_h1 = get_mtf_data(

                        symbol

                    )



                    if (

                        df_m5 is None

                        or

                        df_h1 is None

                    ):

                        continue





                    df = transformer.build_multi_timeframe_features(

                        df_m5,

                        df_h1

                    )



                    if df is None or df.empty:

                        continue





                    core.process(

                        symbol,

                        df,

                        candle_time=df["time"].iloc[-1]

                    )





                except Exception as e:


                    log(
                        f"ERROR | {symbol}: {e}"
                    )





            time.sleep(
                LIVE_INTERVAL
            )





    # =====================================================
    # SHUTDOWN
    # =====================================================

    log(
        "INFO | Bot stopped"
    )






# =====================================================
# START
# =====================================================

if __name__ == "__main__":

    main()