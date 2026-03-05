import time
import numpy as np
import MetaTrader5 as mt5

from config import COOLDOWN_SECONDS, BOT_MODE, SYMBOL, SIGNAL_THRESHOLD
from core.data_fetcher import initialize_mt5, get_mtf_data
from core.predictor import Predictor
from core.executor import execute_trade
from core.logger import log
from core.feature_engine_live import FeatureTransformerLive


# ==================================================
# Prediction Memory Buffer
# ==================================================

prediction_buffer = []


def smooth_prediction(pred):

    prediction_buffer.append(pred)

    if len(prediction_buffer) > 5:
        prediction_buffer.pop(0)

    return float(np.mean(prediction_buffer))


# ==================================================
# Capital Risk Setup
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
# Main Bot Loop
# ==================================================

def main():

    initialize_mt5()

    capital = ask_capital()

    predictor = Predictor()
    transformer = FeatureTransformerLive()

    last_trade_time = 0

    print("Demo Bot Started...")

    while True:

        try:

            df_m5, df_h1 = get_mtf_data()

            if df_m5 is None or df_h1 is None:
                time.sleep(30)
                continue

            df = transformer.build_multi_timeframe_features(
                df_m5.sort_values("time"),
                df_h1.sort_values("time")
            )

            if df.empty:
                time.sleep(30)
                continue

            feature_list = transformer.get_feature_list()

            X = df[feature_list].ffill().dropna()

            if X.empty:
                time.sleep(30)
                continue

            raw_pred = predictor.predict(X, feature_list)[-1]

            pred = smooth_prediction(raw_pred)

            # Confidence gating
            if abs(pred) < SIGNAL_THRESHOLD:
                print("Low confidence signal skipped")
                time.sleep(60)
                continue

            signal = "BUY" if pred > 0 else "SELL"

            print("Prediction:", pred)
            print("Signal:", signal)

            now = time.time()

            positions = mt5.positions_get(symbol=SYMBOL)

            # ==================================================
            # Entry Logic
            # ==================================================

            if positions is None or len(positions) == 0:

                if now - last_trade_time > COOLDOWN_SECONDS:

                    log(f"{signal} | {pred}")

                    if BOT_MODE == "AUTO_DEMO":
                        execute_trade(signal)

                    last_trade_time = now

            else:

                # ==================================================
                # Position Protection Layer
                # ==================================================

                pos = positions[0]

                if pos.profit > 0.5 or pos.profit < -1.0:

                    print("Brain exit protection triggered")

                    opposite = "SELL" if pos.type == mt5.ORDER_TYPE_BUY else "BUY"

                    execute_trade(opposite)

            time.sleep(60)

        except Exception as e:
            print("Bot Loop Error:", e)
            time.sleep(30)


if __name__ == "__main__":
    main()