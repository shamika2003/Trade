# filename: feature_engine.py

import pandas as pd
import numpy as np


class FeatureTransformer:

    # ===============================
    # Feature List
    # ===============================

    def get_feature_list(self):
        return [
            "return", "range",
            "ma5", "ma20", "trend",
            "tick_volume", "spread",
            "rsi", "atr",
            "momentum_3", "momentum_10",
            "volatility", "range_position",
            "volume_change", "atr_ratio",
            "trend_strength",
            "h1_ma20", "h1_rsi",
            "h1_trend_strength", "h1_trend_bias",
            "m5_h1_alignment",
            "structure_bias",
            "volatility_regime",
            "price_zscore",
            "volatility_change",
            "dist_to_high_50",
            "dist_to_low_50",
            "hour_sin",
            "hour_cos",
        ]

    # ===============================
    # Technical Feature Block
    # ===============================

    def _technical(self, df, prefix=""):

        df = df.copy()

        eps = 1e-9

        price = df["close"].replace(0, np.nan)

        # Base Signals
        df[f"{prefix}return"] = np.log(price / price.shift(1))
        df[f"{prefix}range"] = (df["high"] - df["low"]) / (price + eps)

        # RSI
        delta = price.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        rs = gain.ewm(span=14, adjust=False).mean() / (
            loss.ewm(span=14, adjust=False).mean() + eps
        )

        df[f"{prefix}rsi"] = 100 - (100 / (1 + rs))

        # ATR
        tr = pd.concat([
            df["high"] - df["low"],
            np.abs(df["high"] - price.shift()),
            np.abs(df["low"] - price.shift())
        ], axis=1).max(axis=1)

        df[f"{prefix}atr"] = tr.ewm(span=14, adjust=False).mean()

        # Moving averages
        df[f"{prefix}ma5"] = price.rolling(5).mean()
        df[f"{prefix}ma20"] = price.rolling(20).mean()

        df[f"{prefix}trend"] = df[f"{prefix}ma5"] - df[f"{prefix}ma20"]

        # Derived signals
        df["volume_change"] = df["tick_volume"].pct_change()

        df["atr_ratio"] = df[f"{prefix}range"] / (df[f"{prefix}atr"] + eps)

        high20 = df["high"].rolling(20).max()
        low20 = df["low"].rolling(20).min()

        df["range_position"] = (price - low20) / (high20 - low20 + eps)
        df["range_position"] = df["range_position"].clip(0, 1)

        # Trend strength proxy
        df["trend_strength"] = df[f"{prefix}trend"] / (price + eps)

        df["volatility"] = df[f"{prefix}return"].rolling(20).std()

        df["momentum_3"] = price - price.shift(3)
        df["momentum_10"] = price - price.shift(10)

        # Structure bias signal
        df["structure_bias"] = np.sign(
            df["ma5"] - df["ma20"]
        ) * df["volatility"]

        # ===============================
        # Autonomous Trading Support Signals
        # ===============================

        # Adaptive price normalization anchor
        df["price_zscore"] = (
            price - price.rolling(1000).mean()
        ) / (price.rolling(1000).std() + eps)

        # ===============================
        # Volatility Expansion Signal
        # ===============================

        df["volatility_change"] = (
            df["volatility"] /
            (df["volatility"].shift(10) + eps)
        )

        # ===============================
        # Breakout Structure Features
        # ===============================

        rolling_high_50 = df["high"].rolling(50).max()
        rolling_low_50 = df["low"].rolling(50).min()

        df["dist_to_high_50"] = (
            (rolling_high_50 - price) / (price + eps)
        )

        df["dist_to_low_50"] = (
            (price - rolling_low_50) / (price + eps)
        )

        # ===============================
        # Time-of-Day Cyclical Encoding
        # ===============================

        if "time" in df.columns:
            hours = pd.to_datetime(df["time"]).dt.hour
            df["hour_sin"] = np.sin(2 * np.pi * hours / 24)
            df["hour_cos"] = np.cos(2 * np.pi * hours / 24)


        # Numerical stability guard
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Regime score proxy
        df["volatility_regime"] = (
            df["return"].rolling(50).std()
            .rank(pct=True)
        )

        return df

    # ===============================
    # Public Feature Builder
    # ===============================

    def build_features(self, df):

        df = df.copy()

        df = df.sort_values("time").reset_index(drop=True)

        df = self._technical(df, prefix="")

        df.dropna(inplace=True)

        return df

    # ===============================
    # Autonomous-Safe Target Function
    # ===============================

    def add_target(self, df, horizon=12):

        df = df.copy()

        df["future_close"] = df["close"].shift(-horizon)

        raw_return = (
            df["future_close"] - df["close"]
        ) / df["close"]

        # Stabilized bounded target (research safe)
        df["target"] = np.tanh(raw_return * 100)

        df.drop(columns=["future_close"], inplace=True)

        df.dropna(inplace=True)

        return df