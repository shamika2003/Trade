# filename: dataset_builder.py

import pandas as pd
import numpy as np
import MetaTrader5 as mt5

from data_collector import MarketDataCollector
from config import FUTURE_PERIOD, DATA_PATH
from feature_engine import FeatureTransformer


def build_dataset():

    collector = MarketDataCollector()

    # ======================
    # Fetch M5 Data
    # ======================
    df_m5 = collector.fetch_history(
        symbol="EURUSD",
        timeframe=mt5.TIMEFRAME_M5,
        total_candles=500000
    )

    if df_m5 is None:
        raise RuntimeError("Dataset build failed `M5`")

    df_m5 = df_m5.sort_values("time").reset_index(drop=True)

    # ======================
    # Fetch H1 Data
    # ======================
    df_h1 = collector.fetch_history(
        symbol="EURUSD",
        timeframe=mt5.TIMEFRAME_H1,
        total_candles=40000
    )

    if df_h1 is None:
        raise RuntimeError("Dataset build failed `H1`")

    df_h1 = df_h1.sort_values("time").reset_index(drop=True)

    transformer = FeatureTransformer()

    # ======================
    # Technical Feature Engineering
    # ======================
    df_m5 = transformer.build_features(df_m5)
    df_h1 = transformer.build_features(df_h1)

    # ======================
    # Select H1 Context Features
    # ======================
    h1_cols = ["time", "ma20", "rsi", "trend_strength"]

    df_h1 = df_h1[h1_cols].copy()

    df_h1.rename(columns={
        "ma20": "h1_ma20",
        "rsi": "h1_rsi",
        "trend_strength": "h1_trend_strength"
    }, inplace=True)

    # ======================
    # Merge Multi-Timeframe Data
    # ======================
    df = pd.merge_asof(
        df_m5.sort_values("time"),
        df_h1.sort_values("time"),
        on="time",
        direction="backward"
    )

    # ======================
    # Alignment Features
    # ======================
    df["h1_trend_bias"] = np.sign(df["h1_trend_strength"])

    df["m5_h1_alignment"] = (
        np.sign(df["trend_strength"]) ==
        np.sign(df["h1_trend_strength"])
    ).astype(int)

    # ======================
    # Future Return Target
    # ======================
    future_close = df["close"].shift(-FUTURE_PERIOD)

    raw_return = (future_close - df["close"]) / df["close"]

    # Use rolling volatility as risk normalizer
    vol = df["return"].rolling(20).std()

    risk_adjusted_return = raw_return / (vol + 1e-9)

    # Bound extreme values (stable training)
    df["future_return"] = np.tanh(risk_adjusted_return)

    # ======================
    # Regime Feature
    # ======================
    df["volatility"] = df["future_return"].rolling(20).std()

    df["volatility_regime"] = np.where(
        df["volatility"] > df["volatility"].quantile(0.75),
        1,
        0
    )

    df["price_zscore"] = (
        df["close"] - df["close"].rolling(1000).mean()
    ) / (df["close"].rolling(1000).std() + 1e-9)

    # ======================
    # Momentum Context Feature
    # ======================
    df["momentum_context"] = df["close"].pct_change(10)

    # ======================
    # Spread Safety Handling
    # ======================
    if "spread" not in df.columns:
        df["spread"] = 0

    # ======================
    # Noise Filtering
    # ======================
    noise_threshold = 0.00005

    df = df[abs(df["future_return"]) > noise_threshold]


    # ======================
    # Multi Target Labels
    # ======================

    df["future_close_short"] = df["close"].shift(-6)
    df["future_close_long"] = df["close"].shift(-24)

    df["target_short"] = np.tanh(
        ((df["future_close_short"] - df["close"]) / df["close"]) * 100
    )

    df["target_long"] = np.tanh(
        ((df["future_close_long"] - df["close"]) / df["close"]) * 100
    )

    df.drop(columns=["future_close_short", "future_close_long"], inplace=True)

    # ======================
    # Leakage Safety Trim
    # ======================
    df = df.iloc[:-FUTURE_PERIOD].copy()

    df.dropna(inplace=True)

    df.to_csv(DATA_PATH, index=False)

    print("Dataset built successfully.")


if __name__ == "__main__":
    build_dataset()