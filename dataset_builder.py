import pandas as pd
import MetaTrader5 as mt5

from data_collector import MarketDataCollector
from feature_engine import FeatureTransformer


def build_dataset():

    collector = MarketDataCollector()

    df = collector.fetch_history(
        symbol="EURUSD",
        timeframe=mt5.TIMEFRAME_M5,
        total_candles=100000
    )

    if df is None:
        raise RuntimeError("Dataset build failed")

    # Safety sort (very important for time-series ML)
    df = df.sort_values("time").reset_index(drop=True)

    transformer = FeatureTransformer()

    df = transformer.build_features(df)
    df = transformer.add_target(df)

    if "target" in df.columns:
        df = df[df["target"] != 0]
    else:
        raise RuntimeError("Target column missing after feature engineering")

    df["target_binary"] = (df["target"] == 1).astype(int)

    df.to_csv("market_dataset.csv", index=False)

    print("Dataset built.")


if __name__ == "__main__":
    build_dataset()