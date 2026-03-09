# filename: demo_bot.py

import time
import numpy as np
import MetaTrader5 as mt5

from config import COOLDOWN_SECONDS, BOT_MODE, SYMBOLS, SIGNAL_THRESHOLD
from core.data_fetcher import initialize_mt5, get_mtf_data
from core.predictor import Predictor
from core.executor import BrainExecutor
from core.feature_engine_live import FeatureTransformerLive
from core.trade_manager import TradeManager


# ==================================================
# Prediction Memory (per symbol)
# ==================================================

prediction_buffers = {}


def smooth_prediction(symbol, pred):

    if symbol not in prediction_buffers:
        prediction_buffers[symbol] = []

    buf = prediction_buffers[symbol]

    buf.append(pred)

    if len(buf) > 5:
        buf.pop(0)

    return float(np.mean(buf))


# ==================================================
# Main Brain Loop
# ==================================================

def main():

    initialize_mt5()

    capital = ask_capital()

    predictor = Predictor()
    transformer = FeatureTransformerLive()
    executor = BrainExecutor()

    trade_managers = {s: TradeManager() for s in SYMBOLS}

    # Entry lock memory
    active_symbols = set()
    last_trade_times = {s: 0 for s in SYMBOLS}

    print("Autonomous Multi-Symbol Brain Bot Started...")

    while True:

        try:

            if not mt5.terminal_info():
                print("MT5 disconnected — waiting reconnect")
                time.sleep(5)
                continue

            loop_start = time.time()

            for symbol in SYMBOLS:

                df_m5, df_h1 = get_mtf_data(symbol)

                if df_m5 is None or df_h1 is None:
                    continue

                df = transformer.build_multi_timeframe_features(
                    df_m5,
                    df_h1
                )

                if df is None or df.empty:
                    continue

                df["symbol"] = symbol

                feature_list = transformer.get_feature_list()

                raw_pred_arr = predictor.predict(df, feature_list)

                if raw_pred_arr is None or len(raw_pred_arr) == 0:
                    continue

                raw_pred = raw_pred_arr[-1]

                pred = smooth_prediction(symbol, raw_pred)

                # ================= SIGNAL FILTER =================

                if abs(pred) < SIGNAL_THRESHOLD:
                    print(symbol, "confidence", round(pred, 4))
                    continue

                signal = "BUY" if pred > 0 else "SELL"

                print(symbol, "Prediction:", round(pred, 4))
                print(symbol, "Signal:", signal)

                now = time.time()

                positions = mt5.positions_get(symbol=symbol)

                if positions is None:
                    continue

                trade_manager = trade_managers[symbol]

                # ================= ENTRY =================

                if len(positions) == 0:

                    if symbol in active_symbols:
                        continue

                    if now - last_trade_times[symbol] > COOLDOWN_SECONDS:

                        if BOT_MODE == "AUTO_DEMO":

                            if executor.open_trade(symbol, signal):

                                trade_manager.reset()

                                active_symbols.add(symbol)
                                last_trade_times[symbol] = now

                # ================= EXIT =================

                else:

                    pos = positions[0]

                    profit = float(pos.profit)

                    trade_manager.update(profit)

                    close, reason = trade_manager.should_close(profit)

                    if close:

                        print(symbol, "Closing trade:", reason)

                        if executor.close_position(pos):

                            trade_manager.reset()

                            if symbol in active_symbols:
                                active_symbols.remove(symbol)

                            last_trade_times[symbol] = now

                            time.sleep(1)

            elapsed = time.time() - loop_start

            time.sleep(max(1, 5 - elapsed))

        except Exception as e:

            print("Bot Loop Error:", e)
            time.sleep(10)


def ask_capital():

    try:
        capital = float(input("Enter Trading Capital (USD): "))

        if capital > 0:
            return capital

    except:
        pass

    print("Invalid capital input. Using default 1000.")
    return 1000.0


if __name__ == "__main__":
    main()