# filename: feature_engine_live.py

import pandas as pd
import numpy as np


class FeatureTransformerLive:

    # =====================================================
    # Feature Schema (Keep synchronized with training)
    # =====================================================

    def get_feature_list(self):

        return [
            "return","range","ma5","ma20","trend",
            "tick_volume","spread","rsi","atr",
            "momentum_3","momentum_10",
            "volatility","range_position",
            "volume_change","atr_ratio",
            "trend_strength",

            "h1_ma20","h1_rsi",
            "h1_trend_strength","h1_trend_bias",

            "m5_h1_alignment","structure_bias",
            "volatility_regime","price_zscore",
            "volatility_change",
            "dist_to_high_50","dist_to_low_50",
            "hour_sin","hour_cos"
        ]

    # =====================================================
    # Technical Feature Generator
    # =====================================================

    def _technical(self, df):

        df = df.copy()

        eps = 1e-9

        if "close" not in df.columns:
            return df

        price = df["close"].replace(0, np.nan)

        df["return"] = np.log(price / price.shift(1))

        df["range"] = (df["high"] - df["low"]) / (price + eps)

        delta = price.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        rs = gain.ewm(span=14).mean() / (
            loss.ewm(span=14).mean() + eps
        )

        df["rsi"] = 100 - (100/(1+rs))

        tr = pd.concat([
            df["high"]-df["low"],
            abs(df["high"]-price.shift()),
            abs(df["low"]-price.shift())
        ], axis=1).max(axis=1)

        df["atr"] = tr.ewm(span=14).mean()

        df["ma5"] = price.rolling(5).mean()
        df["ma20"] = price.rolling(20).mean()

        df["trend"] = df["ma5"] - df["ma20"]

        df["volume_change"] = df["tick_volume"].pct_change().fillna(0)

        df["atr_ratio"] = df["range"] / (df["atr"] + eps)

        high20 = df["high"].rolling(20).max()
        low20 = df["low"].rolling(20).min()

        df["range_position"] = ((price-low20)/(high20-low20+eps)).clip(0,1)

        df["trend_strength"] = df["trend"] / (price + eps)

        df["volatility"] = df["return"].rolling(20).std()

        df["momentum_3"] = price - price.shift(3)
        df["momentum_10"] = price - price.shift(10)

        df["structure_bias"] = np.sign(
            df["ma5"]-df["ma20"]
        ) * df["volatility"]

        df["price_zscore"] = (
            price-price.rolling(1000).mean()
        )/(price.rolling(1000).std()+eps)

        df["volatility_change"] = (
            df["volatility"]/(df["volatility"].shift(10)+eps)
        ).fillna(0)

        rolling_high_50 = df["high"].rolling(50).max()
        rolling_low_50 = df["low"].rolling(50).min()

        df["dist_to_high_50"] = (rolling_high_50-price)/(price+eps)
        df["dist_to_low_50"] = (price-rolling_low_50)/(price+eps)

        if "time" in df.columns:

            hours = pd.to_datetime(df["time"]).dt.hour

            df["hour_sin"] = np.sin(2*np.pi*hours/24)
            df["hour_cos"] = np.cos(2*np.pi*hours/24)

        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        vol = df["return"].rolling(50).std()

        df["volatility_regime"] = (
            vol.rolling(200).rank(pct=True)
        )

        return df

    # =====================================================
    # Multi-Timeframe Feature Fusion
    # =====================================================

    def build_multi_timeframe_features(self, df_m5, df_h1):

        df_m5 = self._technical(df_m5)
        df_h1 = self._technical(df_h1)

        required_cols = [
            "time","ma20","rsi",
            "trend_strength","structure_bias"
        ]

        df_h1 = df_h1[[c for c in required_cols if c in df_h1.columns]].copy()

        rename_map = {
            "ma20":"h1_ma20",
            "rsi":"h1_rsi",
            "trend_strength":"h1_trend_strength",
            "structure_bias":"h1_structure_bias"
        }

        df_h1.rename(columns=rename_map, inplace=True)

        if "h1_trend_strength" in df_h1.columns:
            df_h1["h1_trend_bias"] = np.sign(
                df_h1["h1_trend_strength"]
            )
        else:
            df_h1["h1_trend_bias"] = 0

        if "time" not in df_m5.columns:
            return pd.DataFrame()

        df_h1.set_index("time", inplace=True)
        df_m5.set_index("time", inplace=True)

        df_h1 = df_h1.reindex(df_m5.index, method="ffill")

        df_m5 = df_m5.reset_index()
        df_h1 = df_h1.reset_index()

        df = pd.concat([
            df_m5,
            df_h1.drop(columns=["time"], errors="ignore")
        ], axis=1)

        if "structure_bias" in df.columns and "h1_structure_bias" in df.columns:
            df["m5_h1_alignment"] = (
                (df["structure_bias"]>0) &
                (df["h1_structure_bias"]>0)
            ).astype(int)
        else:
            df["m5_h1_alignment"] = 0

        df.dropna(inplace=True)

        return df