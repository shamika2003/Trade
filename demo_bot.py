import time
import signal
import MetaTrader5 as mt5

from config import SYMBOLS, DEFAULT_CAPITAL
from core.data_fetcher import initialize_mt5, get_mtf_data
from core.predictor import Predictor
from core.feature_engine_live import FeatureTransformerLive
from core.executor import BrainExecutor
from core.brain_core import TradingBrainCore
from core.logger import log

running = True


def stop_bot(sig, frame):
    global running
    running = False
    log("INFO | Bot shutting down...")


signal.signal(signal.SIGINT, stop_bot)
signal.signal(signal.SIGTERM, stop_bot)


def ask_capital():
    try:
        capital = float(input("Enter Trading Capital (USD): "))
        if capital > 0:
            return capital
    except Exception:
        pass
    return DEFAULT_CAPITAL


def main():
    initialize_mt5()
    capital = ask_capital()

    executor = BrainExecutor(capital=capital)

    predictors = {s: Predictor() for s in SYMBOLS}
    transformer = FeatureTransformerLive()

    brains = {
        s: TradingBrainCore(s, predictors[s], transformer, executor)
        for s in SYMBOLS
    }

    log("INFO | Brain Bot Started")

    while running:
        start = time.time()

        for symbol in SYMBOLS:
            try:
                if not mt5.symbol_select(symbol, True):
                    continue

                if not mt5.terminal_info():
                    time.sleep(3)
                    continue

                df_m5, df_h1 = get_mtf_data(symbol)
                if df_m5 is None or df_h1 is None:
                    continue

                df = transformer.build_multi_timeframe_features(df_m5, df_h1)

                if df is None or df.empty:
                    continue

                df = df.replace([float("inf"), float("-inf")], 0)

                # 🔥 CRITICAL FIX: enforce symbol ALWAYS
                df["symbol"] = symbol

                brains[symbol].decide_and_act(df)

            except Exception as e:
                log(f"ERROR | {symbol}: {e}")
                time.sleep(1)

        time.sleep(max(1, 5 - (time.time() - start)))


if __name__ == "__main__":
    main()