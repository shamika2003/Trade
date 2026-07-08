# filename: demo_bot.py

import time
import signal

from config_core import SYMBOLS

# =====================================================
# ONLINE MODE (MT5)
# =====================================================
from core.data_fetcher_online import (
    initialize_mt5,
    get_mtf_data
)

# =====================================================
# OFFLINE MODE (CSV REPLAY)
# =====================================================
from core.data_fetcher_offline import CSVDataFeed
csv_feed = CSVDataFeed()

from feature_engine import (
    FeatureTransformer
)

from core.core_engine import (
    CoreEngine
)

from core.logger import log


# =====================================
# GLOBAL CONTROL
# =====================================

running = True


def stop_bot(sig, frame):
    global running
    running = False
    log("INFO | Shutdown requested...")


signal.signal(signal.SIGINT, stop_bot)
signal.signal(signal.SIGTERM, stop_bot)


# =====================================
# MODE SWITCH
# =====================================

USE_OFFLINE = True   # <<< CHANGE THIS ONLY


# =====================================
# MAIN
# =====================================

def main():

    log("INFO | Starting Trade AI")

    # initialize_mt5()           # Online mode 

    transformer = FeatureTransformer()

    core = CoreEngine()

    log("INFO | Systems Ready")

    while running:

        loop_start = time.time()

        try:

            for symbol in SYMBOLS:

                try:

                    # =================================================
                    # FETCH DATA
                    # =================================================

                    if USE_OFFLINE:
                        # -----------------------------
                        # OFFLINE MODE (CSV REPLAY)
                        # -----------------------------
                        df_m5 = csv_feed.get_next(symbol)
                        df_h1 = csv_feed.get_next(symbol)

                    else:
                        # -----------------------------
                        # ONLINE MODE (MT5)
                        # -----------------------------
                        df_m5, df_h1 = get_mtf_data(symbol)

                    if df_m5 is None or df_h1 is None:
                        continue

                    # =================================================
                    # FEATURE BUILD
                    # =================================================
                    df = transformer.build_multi_timeframe_features(
                        df_m5,
                        df_h1
                    )

                    if df is None or df.empty:
                        continue

                    # =================================================
                    # CLEAN
                    # =================================================
                    df = df.replace(
                        [float("inf"), float("-inf")],
                        0
                    )

                    df["symbol"] = symbol

                    # =================================================
                    # MODEL -> SIGNAL -> TRADE
                    # =================================================
                    core.process(
                        symbol=symbol,
                        df=df
                    )

                except Exception as e:
                    log(f"ERROR | {symbol} processing failed: {e}")

        except Exception as e:
            log(f"ERROR | Main Loop: {e}")

        elapsed = time.time() - loop_start

        sleep_time = max(
            1,
            5 - elapsed
        )

        time.sleep(sleep_time)

    log("INFO | Bot Stopped")


# =====================================
# ENTRY
# =====================================

if __name__ == "__main__":
    main()