import time
import pandas as pd

from config import COOLDOWN_SECONDS, BOT_MODE
from core.data_fetcher import initialize_mt5, get_mtf_data
from core.predictor import Predictor
from core.signal_engine import decide_signal
from core.executor import execute_trade
from core.logger import log

from model.feature_engine import FeatureTransformer


def main():

    initialize_mt5()

    predictor = Predictor()
    transformer = FeatureTransformer()

    last_trade_time = 0

    print("Demo Bot Started...")

    while True:

        try:

            # ============================
            # Fetch Multi Timeframe Data
            # ============================

            df_m5, df_h1 = get_mtf_data()

            if df_m5 is None or df_h1 is None:
                print("Market data fetch failed")
                time.sleep(60)
                continue

            # Sort timeline safety
            df_m5 = df_m5.sort_values("time")
            df_h1 = df_h1.sort_values("time")

            # ============================
            # Feature Engineering
            # ============================

            df_m5 = transformer.build_features(df_m5)
            df_h1 = transformer.build_features(df_h1)

            # ============================
            # Prepare H1 Feature Mapping
            # ============================

            h1_cols_raw = ["ma20", "rsi", "trend_strength", "structure_bias"]

            df_h1 = df_h1[["time"] + [c for c in h1_cols_raw if c in df_h1.columns]]

            df_h1.rename(columns={
                "ma20": "h1_ma20",
                "rsi": "h1_rsi",
                "trend_strength": "h1_trend_strength",
                "structure_bias": "h1_structure_bias"
            }, inplace=True)

            # ============================
            # Align H1 Timeline to M5 Timeline
            # ============================

            df_h1 = df_h1.set_index("time")
            df_h1 = df_h1.reindex(df_m5["time"], method="ffill")
            df_h1 = df_h1.reset_index()
            df_h1.rename(columns={"index": "time"}, inplace=True)

            # ============================
            # Merge Feature Frames
            # ============================

            df = pd.concat(
                [
                    df_m5.reset_index(drop=True),
                    df_h1.drop(columns=["time"], errors="ignore").reset_index(drop=True)
                ],
                axis=1
            )

            # ============================
            # Cross Timeframe Feature
            # ============================

            df["m5_h1_alignment"] = (
                (df["structure_bias"] > 0) &
                (df["h1_structure_bias"] > 0)
            ).astype(int)

            # ============================
            # Prediction Pipeline Safety Check
            # ============================

            feature_list = transformer.get_feature_list()

            if len(df) == 0:
                print("Empty dataframe after merge")
                time.sleep(60)
                continue

            missing_cols = [c for c in feature_list if c not in df.columns]

            if missing_cols:
                print("Missing features:", missing_cols)
                time.sleep(60)
                continue

            X = df[feature_list].dropna()

            if len(X) == 0:
                print("Empty feature matrix")
                time.sleep(60)
                continue

            pred_array = predictor.predict(X, feature_list)

            if len(pred_array) == 0:
                print("Prediction failed")
                time.sleep(60)
                continue

            pred = pred_array[-1]

            signal = decide_signal(pred)

            now = time.time()

            # ============================
            # Execution Layer
            # ============================

            if signal and (now - last_trade_time > COOLDOWN_SECONDS):

                log(f"Signal {signal} | Pred {pred}")

                if BOT_MODE == "AUTO_DEMO":
                    execute_trade(signal)

                elif BOT_MODE == "SEMI":
                    print("Signal:", signal)

                last_trade_time = now

            time.sleep(60)

        except Exception as e:
            print("Bot Loop Error:", e)
            time.sleep(60)


if __name__ == "__main__":
    main()