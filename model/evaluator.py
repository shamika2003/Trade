# filename: evaluator.py

import pandas as pd
import numpy as np
import joblib

from backtester import run_backtest
from feature_engine import FeatureTransformer
from config_model import MODEL_PATH, DATA_PATH


def evaluate():

    print("\n" + "═" * 80)
    print("🧪  QUANT MODEL EVALUATION ENGINE")
    print("═" * 80)

    df = pd.read_csv(DATA_PATH)

    if "symbol" not in df.columns:
        raise RuntimeError("Dataset missing 'symbol' column")

    if "time" in df.columns:
        df = df.sort_values("time")

    print(f"📊 Rows available: {len(df):,}")

    transformer = FeatureTransformer()
    features = transformer.get_feature_list()

    model_dict = joblib.load(MODEL_PATH)

    all_symbols = df["symbol"].unique()

    print(f"📈 Models loaded: {list(model_dict.keys())}")

    for symbol in all_symbols:

        print("\n" + "═" * 80)
        print(f"📈 SYMBOL: {symbol}")
        print("═" * 80)

        model = model_dict.get(symbol)

        if model is None:
            print("⚠️ No model for symbol")
            continue

        df_s = df[df["symbol"] == symbol].copy().reset_index(drop=True)

        print(f"📊 Samples: {len(df_s):,}")

        missing = [f for f in features if f not in df_s.columns]
        if missing:
            raise RuntimeError(f"{symbol} missing features: {missing}")

        X = df_s[features].replace([np.inf, -np.inf], np.nan).fillna(0)

        print("🧠 Predicting...")
        preds = model.predict(X)

        print(f"✔ Predictions: {len(preds):,}")

        # ===========================
        # DEBUG SIGNAL STATS
        # ===========================
        print("\n📊 Signal Stats:")
        print(pd.Series(preds).describe())

        print("\n📉 Running backtest...")
        results = run_backtest(df_s, preds)

        if results:
            print("\n📊 FINAL RESULT")
            print(results)

        print("\n✔ Done:", symbol)


if __name__ == "__main__":
    evaluate()