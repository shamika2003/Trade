import pandas as pd
import numpy as np


class FeatureTransformer:

    def _add_technical_features(self, df, prefix=""):

        df = df.copy()

        price = df["close"].replace(0, np.nan)

        df[f"{prefix}return"] = np.log(price / price.shift(1))

        df[f"{prefix}range"] = (df["high"] - df["low"]) / price

        delta = price.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        rs = gain.ewm(span=14, adjust=False).mean() / (
            loss.ewm(span=14, adjust=False).mean() + 1e-8
        )

        df[f"{prefix}rsi"] = 100 - (100 / (1 + rs))

        tr = pd.concat([
            df["high"] - df["low"],
            np.abs(df["high"] - price.shift()),
            np.abs(df["low"] - price.shift())
        ], axis=1).max(axis=1)

        df[f"{prefix}atr"] = tr.ewm(span=14, adjust=False).mean()

        df[f"{prefix}ma5"] = price.rolling(5).mean()
        df[f"{prefix}ma20"] = price.rolling(20).mean()

        df[f"{prefix}trend"] = df[f"{prefix}ma5"] - df[f"{prefix}ma20"]

        return df
    

    def build_features(self, df):

        df = df.copy()
        print(df.columns)

        # Sort time first (very important)
        df = df.sort_values("time").reset_index(drop=True)

        # M5 base features
        df = self._add_technical_features(df, prefix="m5_")

        base_df = df.copy()
        # Multi-timeframe fusion
        for tf, label in [
            ("15min", "m15_"),
            ("30min", "m30_")
        ]:

            resampled = (
                base_df.set_index("time")
                .resample(tf, origin="start")
                .agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last"
                })
                .dropna()
                .reset_index()
            )

            resampled = self._add_technical_features(
                resampled,
                prefix=label
            )

            df = pd.merge_asof(
                df.sort_values("time"),
                resampled.sort_values("time"),
                on="time",
                direction="backward"
            )

        df.dropna(inplace=True)

        return df

    def add_target(self, df, horizon=1):

        df = df.copy()

        df["future_close"] = df["close"].shift(-horizon)

        df["target"] = np.where(
            df["future_close"] > df["close"],
            1,
            -1
        )

        df.drop(columns=["future_close"], inplace=True)

        df.dropna(inplace=True)

        return df