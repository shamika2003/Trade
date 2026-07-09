# filename: demo_bot.py

import time
import signal

from config_core import SYMBOLS

from core.feature_engine import FeatureTransformer

from core.core_engine import CoreEngine
from core.logger import log


# =====================================================
# MODE SWITCH
# =====================================================

USE_OFFLINE = True

# True  = CSV replay mode
# False = MT5 live mode



# =====================================================
# SELECT EXECUTOR
# =====================================================

if USE_OFFLINE:

    from core.paper_executor import PaperExecutor

    executor = PaperExecutor()

    log(
        "INFO | Using Paper Executor"
    )


else:

    from core.executor import BrainExecutor

    executor = BrainExecutor()

    log(
        "INFO | Using MT5 Executor"
    )



# =====================================================
# DATA PROVIDER SELECTOR
# =====================================================

if USE_OFFLINE:


    from core.data_fetcher_offline import CSVDataFeed


    data_feed = CSVDataFeed()


    log(
        "INFO | Running OFFLINE CSV mode"
    )



else:


    from core.data_fetcher_online import (
        initialize_mt5,
        get_mtf_data
    )


    data_feed = None


    initialize_mt5()


    log(
        "INFO | Running ONLINE MT5 mode"
    )



# =====================================================
# GLOBAL CONTROL
# =====================================================

running = True



def stop_bot(sig, frame):

    global running


    running = False


    log(
        "INFO | Shutdown requested..."
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
# MAIN LOOP
# =====================================================

def main():


    log(
        "INFO | Starting Trade AI"
    )



    transformer = FeatureTransformer()



    # IMPORTANT:
    # Inject executor
    #
    # Offline:
    # PaperExecutor
    #
    # Live:
    # BrainExecutor

    core = CoreEngine(
        executor=executor
    )



    log(
        "INFO | Systems Ready"
    )



    while running:



        loop_start = time.time()



        try:



            for symbol in SYMBOLS:



                try:



                    # =================================================
                    # FETCH MARKET DATA
                    # =================================================


                    if USE_OFFLINE:


                        df_m5, df_h1 = (
                            data_feed
                            .get_mtf_data(symbol)
                        )



                    else:


                        df_m5, df_h1 = (
                            get_mtf_data(symbol)
                        )




                    if (
                        df_m5 is None
                        or
                        df_h1 is None
                    ):

                        continue




                    # =================================================
                    # FEATURE ENGINEERING
                    # =================================================


                    df = (
                        transformer
                        .build_multi_timeframe_features(
                            df_m5,
                            df_h1
                        )
                    )



                    if df is None or df.empty:

                        continue




                    # =================================================
                    # CLEAN DATA
                    # =================================================


                    df = df.replace(
                        [
                            float("inf"),
                            float("-inf")
                        ],
                        0
                    )



                    df["symbol"] = symbol




                    # =================================================
                    # AI BRAIN
                    # =================================================


                    core.process(
                        symbol=symbol,
                        df=df
                    )




                except Exception as e:


                    log(
                        f"ERROR | {symbol} processing failed: {e}"
                    )




        except Exception as e:


            log(
                f"ERROR | Main Loop: {e}"
            )




        # =================================================
        # LOOP SPEED CONTROL
        # =================================================


        elapsed = (
            time.time()
            -
            loop_start
        )



        if USE_OFFLINE:


            # Fast CSV replay
            sleep_time = 0.1



        else:


            # Live MT5 polling
            sleep_time = max(
                1,
                5 - elapsed
            )



        time.sleep(
            sleep_time
        )

    log(
        "INFO | Bot Stopped"
    )

# =====================================================
# ENTRY
# =====================================================

if __name__ == "__main__":

    main()