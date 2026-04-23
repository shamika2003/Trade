# filename: dataset_builder.py

import pandas as pd
import numpy as np
import MetaTrader5 as mt5

from data_collector import MarketDataCollector
from config import FUTURE_PERIOD, DATA_PATH, SYMBOLS
from feature_engine import FeatureTransformer


def build_dataset():

    collector = MarketDataCollector()
    transformer = FeatureTransformer()

    all_symbol_data = []

    for symbol in SYMBOLS:

        print(f"\nBuilding dataset for {symbol}")

        # ======================
        # Fetch M5 Data
        # ======================

        df_m5 = collector.fetch_history(
            symbol=symbol,
            timeframe=mt5.TIMEFRAME_M5,
            total_candles=500000
        )

        if df_m5 is None:
            print(f"{symbol} M5 data failed")
            continue

        df_m5 = df_m5.sort_values("time").reset_index(drop=True)

        # ======================
        # Fetch H1 Data
        # ======================

        df_h1 = collector.fetch_history(
            symbol=symbol,
            timeframe=mt5.TIMEFRAME_H1,
            total_candles=40000
        )

        if df_h1 is None:
            print(f"{symbol} H1 data failed")
            continue

        df_h1 = df_h1.sort_values("time").reset_index(drop=True)

        # ======================
        # Feature Engineering
        # ======================

        df_m5 = transformer.build_features(df_m5)
        df_h1 = transformer.build_features(df_h1)

        # ======================
        # Select H1 Context
        # ======================

        h1_cols = ["time", "ma20", "rsi", "trend_strength"]

        df_h1 = df_h1[h1_cols].copy()

        df_h1.rename(columns={
            "ma20": "h1_ma20",
            "rsi": "h1_rsi",
            "trend_strength": "h1_trend_strength"
        }, inplace=True)

        # ======================
        # Merge MTF (safe)
        # ======================

        df = pd.merge_asof(
            df_m5.sort_values("time"),
            df_h1.sort_values("time"),
            on="time",
            direction="backward"
        )

        # ======================
        # Alignment Signals
        # ======================

        df["h1_trend_bias"] = np.sign(df["h1_trend_strength"])

        df["m5_h1_alignment"] = (
            np.sign(df["trend_strength"]) ==
            np.sign(df["h1_trend_strength"])
        ).astype(int)

        # ======================
        # Target Construction (LEAKAGE SAFE)
        # ======================

        future_close = df["close"].shift(-FUTURE_PERIOD)

        raw_return = (future_close - df["close"]) / df["close"]

        # Bounded, stable target
        df["future_return"] = np.tanh(raw_return)

        # ======================
        # Multi Targets (aligned + safe)
        # ======================

        df["future_close_short"] = df["close"].shift(-6)
        df["future_close_long"] = df["close"].shift(-24)

        df["target_short"] = np.tanh(
            (df["future_close_short"] - df["close"]) / df["close"]
        )

        df["target_long"] = np.tanh(
            (df["future_close_long"] - df["close"]) / df["close"]
        )

        df.drop(
            columns=["future_close_short", "future_close_long"],
            inplace=True
        )

        # ======================
        # Spread Safety
        # ======================

        if "spread" not in df.columns:
            df["spread"] = 0

        # ======================
        # Final Cleanup
        # ======================

        # Remove rows where future data not available
        df = df.iloc[:-FUTURE_PERIOD].copy()

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        df["symbol"] = symbol

        all_symbol_data.append(df)

    collector.disconnect()

    if not all_symbol_data:
        raise RuntimeError("Dataset build failed for all symbols")

    final_df = pd.concat(all_symbol_data, ignore_index=True)

    final_df.to_csv(DATA_PATH, index=False)

    print("\nDataset built successfully.")
    print("Total rows:", len(final_df))
    print("Symbols:", final_df["symbol"].unique())


if __name__ == "__main__":
    build_dataset()