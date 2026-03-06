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
# Capital Setup
# ==================================================

def ask_capital():

    try:
        capital = float(input("Enter Trading Capital (USD): "))

        if capital <= 0:
            raise ValueError

        return capital

    except:
        print("Invalid capital input. Using default 1000.")
        return 1000.0


# ==================================================
# Main Brain Loop
# ==================================================

def main():

    initialize_mt5()

    capital = ask_capital()

    predictor = Predictor()
    transformer = FeatureTransformerLive()
    executor = BrainExecutor()

    # Per-symbol state
    trade_managers = {s: TradeManager() for s in SYMBOLS}
    last_trade_times = {s: 0 for s in SYMBOLS}

    print("Autonomous Multi-Symbol Brain Bot Started...")

    while True:

        try:

            for symbol in SYMBOLS:

                df_m5, df_h1 = get_mtf_data(symbol)

                if df_m5 is None or df_h1 is None:
                    continue

                df = transformer.build_multi_timeframe_features(
                    df_m5,
                    df_h1
                )

                if df.empty:
                    continue

                feature_list = transformer.get_feature_list()

                X = df[feature_list].ffill().dropna()

                if X.empty:
                    continue

                raw_pred = predictor.predict(X, feature_list)[-1]

                pred = smooth_prediction(symbol, raw_pred)

                if abs(pred) < SIGNAL_THRESHOLD:
                    print(symbol, "confidence", pred)
                    continue

                signal = "BUY" if pred > 0 else "SELL"

                print(symbol, "Prediction:", round(pred, 4))
                print(symbol, "Signal:", signal)

                now = time.time()

                positions = mt5.positions_get(symbol=symbol)

                trade_manager = trade_managers[symbol]

                # ==========================================
                # ENTRY
                # ==========================================

                if positions is None or len(positions) == 0:

                    if now - last_trade_times[symbol] > COOLDOWN_SECONDS:

                        if BOT_MODE == "AUTO_DEMO":

                            executor.open_trade(symbol, signal)

                            trade_manager.reset()

                            last_trade_times[symbol] = now

                # ==========================================
                # EXIT
                # ==========================================

                else:

                    pos = positions[0]

                    profit = pos.profit

                    trade_manager.update(profit)

                    close, reason = trade_manager.should_close(profit)

                    if close:

                        print(symbol, "Closing trade:", reason)

                        executor.close_position(pos)

                        trade_manager.reset()

                        last_trade_times[symbol] = now

                        time.sleep(1)

            time.sleep(5)

        except Exception as e:

            print("Bot Loop Error:", e)

            time.sleep(20)


if __name__ == "__main__":
    main()