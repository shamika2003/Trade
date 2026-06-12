# filename: trade_bot.py

import time
import signal

from core.data_fetcher import initialize_mt5, get_mtf_data
from core.feature_engine_live import FeatureTransformerLive
from core.core_engine import CoreEngine
from core.logger import log


# =========================
# GLOBAL CONTROL
# =========================
running = True


def stop_bot(sig, frame):
    global running
    running = False
    log("INFO | Bot shutting down...")


signal.signal(signal.SIGINT, stop_bot)
signal.signal(signal.SIGTERM, stop_bot)


# =========================
# CAPITAL (optional future use)
# =========================
def ask_capital():
    try:
        return float(input("Enter Trading Capital (USD): "))
    except:
        return 1000.0


# =========================
# MAIN BOT LOOP
# =========================
def main():

    # 1. INIT SYSTEMS
    initialize_mt5()
    capital = ask_capital()

    transformer = FeatureTransformerLive()

    # CORE ENGINE (we will build next)
    core = CoreEngine(capital=capital)

    log("INFO | Trade Bot Started")

    # =========================
    # MAIN LOOP
    # =========================
    while running:

        loop_start = time.time()

        try:

            # =========================
            # GET DATA PER SYMBOL
            # =========================
            for symbol in core.symbols:

                df_m5, df_h1 = get_mtf_data(symbol)

                if df_m5 is None or df_h1 is None:
                    continue

                # =========================
                # FEATURE ENGINE
                # =========================
                df = transformer.build_multi_timeframe_features(df_m5, df_h1)

                if df is None or df.empty:
                    continue

                df = df.replace([float("inf"), float("-inf")], 0)
                df["symbol"] = symbol

                # =========================
                # CORE PIPELINE
                # =========================
                core.process(symbol, df)

        except Exception as e:
            log(f"ERROR | Main loop: {e}")

        # =========================
        # LOOP CONTROL
        # =========================
        elapsed = time.time() - loop_start
        time.sleep(max(1, 5 - elapsed))


    log("INFO | Bot stopped")


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    main()