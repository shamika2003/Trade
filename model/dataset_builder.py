# filename: dataset_builder.py

import pandas as pd
import numpy as np
import MetaTrader5 as mt5

from data_collector import MarketDataCollector
from config import FUTURE_PERIOD, DATA_PATH, SYMBOLS
from feature_engine import FeatureTransformer


def build_dataset():

    print("\n" + "═" * 80)
    print("📡  MARKET DATASET CONSTRUCTION ENGINE")
    print("═" * 80)
    print("🔄 Initializing market data pipeline...\n")

    collector = MarketDataCollector()
    transformer = FeatureTransformer()

    all_symbol_data = []

    for symbol in SYMBOLS:

        print("\n" + "═" * 80)
        print(f"🌍 PROCESSING SYMBOL: {symbol}")
        print("═" * 80)

        # ======================
        # Fetch M5 Data
        # ======================
        print("📥 Acquiring M5 historical data...")

        df_m5 = collector.fetch_history(
            symbol=symbol,
            timeframe=mt5.TIMEFRAME_M5,
            total_candles=500000
        )

        if df_m5 is None or df_m5.empty:
            print(f"❌ M5 acquisition failed for {symbol}")
            continue

        df_m5 = df_m5.sort_values("time").drop_duplicates("time").reset_index(drop=True)

        print(f"✔ M5 loaded | Candles: {len(df_m5):,}")

        # ======================
        # Fetch H1 Data
        # ======================
        print("📥 Acquiring H1 context data...")

        df_h1 = collector.fetch_history(
            symbol=symbol,
            timeframe=mt5.TIMEFRAME_H1,
            total_candles=40000
        )

        if df_h1 is None or df_h1.empty:
            print(f"❌ H1 acquisition failed for {symbol}")
            continue

        df_h1 = df_h1.sort_values("time").drop_duplicates("time").reset_index(drop=True)

        print(f"✔ H1 loaded | Candles: {len(df_h1):,}")

        # ======================
        # Feature Engineering
        # ======================
        print("🧮 Generating market features...")

        df_m5 = transformer.build_features(df_m5)
        df_h1 = transformer.build_features(df_h1)

        print("✔ Feature engineering completed")

        # ======================
        # H1 Context Reduction (SAFE)
        # ======================
        print("📊 Preparing higher timeframe context...")

        required = ["time", "ma20", "rsi", "trend_strength"]
        missing = [c for c in required if c not in df_h1.columns]

        if missing:
            raise RuntimeError(f"H1 missing features: {missing}")

        df_h1 = df_h1[required].copy()

        df_h1.rename(columns={
            "ma20": "h1_ma20",
            "rsi": "h1_rsi",
            "trend_strength": "h1_trend_strength"
        }, inplace=True)

        # IMPORTANT: ensure sorted BEFORE merge_asof
        df_m5 = df_m5.sort_values("time")
        df_h1 = df_h1.sort_values("time")

        # ======================
        # Multi-timeframe Merge
        # ======================
        print("🔗 Building multi-timeframe context...")

        df = pd.merge_asof(
            df_m5,
            df_h1,
            on="time",
            direction="backward"
        )

        print("✔ Multi-timeframe merge completed")

        # ======================
        # Alignment Signals
        # ======================
        print("🧭 Calculating trend alignment signals...")

        df["h1_trend_bias"] = np.sign(df["h1_trend_strength"])

        df["m5_h1_alignment"] = (
            np.sign(df["trend_strength"]) ==
            np.sign(df["h1_trend_strength"])
        ).astype(int)

        # ======================
        # Targets
        # ======================
        print("🎯 Constructing prediction targets...")

        future_close = df["close"].shift(-FUTURE_PERIOD)
        raw_return = (future_close - df["close"]) / df["close"]

        df["future_return"] = np.tanh(raw_return)

        df["target_short"] = np.tanh(
            (df["close"].shift(-6) - df["close"]) / df["close"]
        )

        df["target_long"] = np.tanh(
            (df["close"].shift(-24) - df["close"]) / df["close"]
        )

        # ======================
        # Spread Safety
        # ======================
        if "spread" not in df.columns:
            df["spread"] = 0

        # ======================
        # Final Cleanup
        # ======================
        print("🧹 Performing dataset sanitation...")

        df = df.iloc[:-FUTURE_PERIOD].copy()
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        df["symbol"] = symbol

        if len(df) == 0:
            print(f"⚠️ Empty dataset after cleaning for {symbol}")
            continue

        print("✔ Data sanitation completed")

        print("─" * 80)
        print(f"✅ SYMBOL COMPLETE: {symbol}")
        print(f"📊 Final rows: {len(df):,}")
        print("─" * 80)

        all_symbol_data.append(df)

    print("\n🔌 Disconnecting market data source...")
    collector.disconnect()

    if not all_symbol_data:
        raise RuntimeError("Dataset build failed for all symbols")

    print("\n📦 Combining symbol datasets...")

    final_df = pd.concat(all_symbol_data, ignore_index=True)

    print("💾 Writing dataset to disk...")

    final_df.to_csv(DATA_PATH, index=False)

    print("\n" + "═" * 80)
    print("📊 DATASET BUILD REPORT")
    print("═" * 80)

    print(f"📈 Total Rows     : {len(final_df):,}")
    print(f"🧩 Symbols Loaded : {final_df['symbol'].nunique()}")
    print(f"💾 Output File    : {DATA_PATH}")

    print("\n🚀 Dataset generation completed successfully")
    print("═" * 80 + "\n")


if __name__ == "__main__":
    build_dataset()