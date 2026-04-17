# filename: demo_bot.py

import time
import MetaTrader5 as mt5
import signal

from config import SYMBOLS, DEFAULT_CAPITAL
from core.data_fetcher import initialize_mt5, get_mtf_data
from core.predictor import Predictor
from core.feature_engine_live import FeatureTransformerLive
from core.brain_core import TradingBrainCore
from core.logger import log


# ======================
# Capital input
# ======================
def ask_capital():
    try:
        capital = float(input("Enter Trading Capital (USD): "))
        if capital > 0:
            return capital
    except Exception:
        pass

    log(f"WARNING | Invalid capital input. Using default {DEFAULT_CAPITAL} USD")
    return DEFAULT_CAPITAL


# ======================
# Graceful shutdown
# ======================
running = True

def stop_bot(sig, frame):
    global running
    running = False
    log("INFO | Bot received shutdown signal. Exiting gracefully...")

signal.signal(signal.SIGINT, stop_bot)
signal.signal(signal.SIGTERM, stop_bot)


# ======================
# Main bot loop
# ======================
def main():
    initialize_mt5()
    capital = ask_capital()

    predictor = Predictor()
    transformer = FeatureTransformerLive()

    # ✅ Create ONE brain per symbol
    brains = {
        symbol: TradingBrainCore(symbol, predictor, transformer)
        for symbol in SYMBOLS
    }

    log("INFO | Brain-based Multi-Symbol Bot Started...")

    while running:
        loop_start = time.time()

        for symbol in SYMBOLS:
            try:
                # Ensure symbol enabled
                if not mt5.symbol_select(symbol, True):  # type: ignore
                    log(f"WARNING | {symbol} not enabled in MT5")
                    continue

                if not mt5.terminal_info():  # type: ignore
                    log("WARNING | MT5 disconnected. Waiting...")
                    time.sleep(5)
                    continue

                # Fetch data
                df_m5, df_h1 = get_mtf_data(symbol)
                if df_m5 is None or df_h1 is None:
                    continue

                # Build features
                df = transformer.build_multi_timeframe_features(df_m5, df_h1)
                if df is None or df.empty:
                    continue

                df["symbol"] = symbol

                # ✅ Delegate EVERYTHING to brain
                brains[symbol].decide_and_act(df)

            except Exception as e:
                log(f"ERROR | Error in {symbol}: {e}")
                time.sleep(1)

        # Loop timing
        elapsed = time.time() - loop_start
        time.sleep(max(1, 5 - elapsed))

    log("INFO | Bot stopped gracefully.")


if __name__ == "__main__":
    main()