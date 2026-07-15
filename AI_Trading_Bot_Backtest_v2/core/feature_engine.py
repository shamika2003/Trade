# filename: feature_engine.py

import pandas as pd
import numpy as np


class FeatureTransformer:

    # =====================================================
    # MODEL FEATURE LIST
    # MUST MATCH TRAINING + LIVE
    # =====================================================
    def get_feature_list(self):

        return [
            "return",
            "range",
            "ma5",
            "ma20",
            "trend",
            "tick_volume",
            "spread",
            "rsi",
            "atr",
            "momentum_3",
            "momentum_10",
            "volatility",
            "range_position",
            "volume_change",
            "atr_ratio",
            "trend_strength",

            "h1_ma20",
            "h1_rsi",
            "h1_trend_strength",
            "h1_trend_bias",
            "m5_h1_alignment",
            "structure_bias",
            "volatility_regime",
            "price_zscore",
            "volatility_change",
            "dist_to_high_50",
            "dist_to_low_50",
            "hour_sin",
            "hour_cos"
        ]

    # =====================================================
    # TECHNICAL FEATURE ENGINE
    # =====================================================
    def _technical(self, df):

        df = df.copy()
        eps = 1e-9
        price = df["close"].replace(0,np.nan)

        # -----------------------------
        # Returns
        # -----------------------------
        df["return"] = np.log(
            price / price.shift(1)
        )

        # -----------------------------
        # Candle Range
        # -----------------------------

        df["range"] = (df["high"] - df["low"]) / (price + eps)

        # -----------------------------
        # RSI
        # -----------------------------
        delta = price.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(span=14, adjust=False).mean()

        avg_loss = loss.ewm(span=14, adjust=False).mean()

        rs = avg_gain / (avg_loss + eps)

        df["rsi"] = (100 - (100/(1+rs)))

        # -----------------------------
        # ATR
        # -----------------------------
        tr = pd.concat([
                df["high"]-df["low"],
                abs(
                    df["high"] - price.shift()
                ),
                abs(df["low"] - price.shift()
               )
            ],

            axis=1
        ).max(axis=1)


        df["atr"] = tr.ewm(span=14, adjust=False).mean()

        # -----------------------------
        # Moving Average Trend
        # -----------------------------
        df["ma5"] = price.rolling(5).mean()

        df["ma20"] = price.rolling(20).mean()


        df["trend"] = (df["ma5"] - df["ma20"])

        # -----------------------------
        # Volume
        # -----------------------------
        df["volume_change"] = (df["tick_volume"].pct_change().fillna(0))

        # -----------------------------
        # ATR ratio
        # -----------------------------
        df["atr_ratio"] = (df["range"] / (df["atr"]+eps))

        # -----------------------------
        # Position in range
        # -----------------------------
        high20 = df["high"].rolling(20).max()

        low20 = df["low"].rolling(20).min()

        df["range_position"] = ((price-low20) / (high20-low20+eps)).clip(0,1)

        # -----------------------------
        # Trend strength
        # -----------------------------
        df["trend_strength"] = (df["trend"] / (price+eps))

        # -----------------------------
        # Momentum
        # -----------------------------
        df["momentum_3"] = (price-price.shift(3))

        df["momentum_10"] = (price-price.shift(10))

        # -----------------------------
        # Volatility
        # -----------------------------
        df["volatility"] = (df["return"].rolling(20) .std())

        # -----------------------------
        # Market Structure
        # -----------------------------
        df["structure_bias"] = (

            np.sign(df["ma5"] -df["ma20"]) * df["volatility"]

        )

        # -----------------------------
        # Z score
        # -----------------------------
        mean = price.rolling(1000).mean()

        std = price.rolling(1000).std()

        df["price_zscore"] = (price-mean)/(std+eps)

        # -----------------------------
        # Volatility Expansion
        # -----------------------------
        df["volatility_change"] = (

            df["volatility"] / ( df["volatility"].shift(10) + eps)
        )

        # -----------------------------
        # Breakout Distance
        # -----------------------------
        high50 = df["high"].rolling(50).max()

        low50 = df["low"].rolling(50).min()

        df["dist_to_high_50"] = (high50-price)/(price+eps)



        df["dist_to_low_50"] = (price-low50)/(price+eps)

        # -----------------------------
        # Time encoding
        # -----------------------------
        if "time" in df.columns:

            hour = pd.to_datetime(df["time"]).dt.hour

            df["hour_sin"] = np.sin(2*np.pi*hour/24)

            df["hour_cos"] = np.cos(2*np.pi*hour/24)

        # -----------------------------
        # Volatility regime
        # -----------------------------
        vol = (df["return"].rolling(50).std())

        df["volatility_regime"] = (vol.rolling(200).rank(pct=True))

        return df

    # =====================================================
    # M5 + H1 FUSION
    # =====================================================
    def build_multi_timeframe_features(self, df_m5, df_h1):

        df_m5 = self._technical(df_m5)

        df_h1 = self._technical(df_h1)

        h1 = df_h1[
            [
                "time",
                "ma20",
                "rsi",
                "trend_strength",
                "structure_bias"
            ]
        ].copy()

        h1.rename(
            columns={
                "ma20":"h1_ma20",
                "rsi":"h1_rsi",
                "trend_strength":
                "h1_trend_strength",
                "structure_bias":
                "h1_structure_bias"
            },

            inplace=True
        )

        h1["h1_trend_bias"] = np.sign(h1["h1_trend_strength"])

        df_m5 = df_m5.set_index("time")
        h1 = h1.set_index("time")

        h1 = h1.reindex(df_m5.index, method="ffill")

        df = pd.concat([
                df_m5,

                h1.drop(columns=[], errors="ignore")
            ], axis=1
        )

        df["m5_h1_alignment"] = (

            (df["structure_bias"] > 0) & (df["h1_structure_bias"] > 0)

        ).astype(int)

        df.reset_index(inplace=True)

        return self._final_clean(df)

    # =====================================================
    # SINGLE TIMEFRAME TRAINING
    # =====================================================
    def build_features(self,df):

        df=df.copy()

        if "symbol" in df.columns:

            df = (df.groupby("symbol", group_keys=False).apply(self._technical))

        else:
            df=self._technical(df)

        return self._final_clean(df)

    # =====================================================
    # TARGET CREATION
    # =====================================================
    def add_target(self, df, horizon=12):

        df=df.copy()

        future = df["close"].shift(
            -horizon
        )

        df["target"] = np.tanh((future - df["close"]) / df["close"] * 100)

        df.dropna(inplace=True)

        return df

    # =====================================================
    # FINAL CLEAN
    # =====================================================
    def _final_clean(self, df):

        # remove duplicated columns
        df = df.loc[:, ~df.columns.duplicated()]

        df.replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan,
            inplace=True
        )

        df.dropna(inplace=True)

        df.reset_index(
            drop=True,
            inplace=True
        )

        return df