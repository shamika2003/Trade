# filename: evaluator.py

import pandas as pd
import numpy as np
import joblib

from backtester import run_backtest
from feature_engine import FeatureTransformer
from config import MODEL_PATH, DATA_PATH


def evaluate():

    print("Loading dataset...")
    df = pd.read_csv(DATA_PATH)

    if "symbol" not in df.columns:
        raise RuntimeError("Dataset missing 'symbol' column")

    if "time" in df.columns:
        df = df.sort_values("time")

    transformer = FeatureTransformer()
    features = transformer.get_feature_list()

    print("Loading trained model...")
    model_dict = joblib.load(MODEL_PATH)

    all_symbols = df["symbol"].unique()

    print("Model symbols:", list(model_dict.keys()))
    print("Dataset symbols:", all_symbols)

    print("\nEvaluating symbols:", all_symbols)

    for symbol in all_symbols:

        print(f"\n========== Evaluating {symbol} ==========")

        symbol_model = model_dict.get(symbol)

        if symbol_model is None:
            print(f"No trained model for {symbol}, skipping.")
            continue

        df_symbol = df[df["symbol"] == symbol].copy()

        if "time" in df_symbol.columns:
            df_symbol = df_symbol.sort_values("time")

        df_symbol = df_symbol.reset_index(drop=True)

        # ----------------------------
        # Feature validation
        # ----------------------------
        missing_features = [f for f in features if f not in df_symbol.columns]

        if missing_features:
            raise RuntimeError(f"{symbol} missing features: {missing_features}")

        X = df_symbol[features].copy()

        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)

        # ----------------------------
        # SINGLE MODEL PREDICTION (FIXED)
        # ----------------------------
        predictions = symbol_model.predict(X)

        # ----------------------------
        # Safety check
        # ----------------------------
        if np.isnan(predictions).any():
            print("WARNING: NaN predictions detected")
            predictions = np.nan_to_num(predictions)

        # ----------------------------
        # Backtest
        # ----------------------------
        results = run_backtest(
            df_symbol.reset_index(drop=True),
            predictions
        )

        # ----------------------------
        # Stats
        # ----------------------------
        print("\nPrediction statistics:")
        print(pd.Series(predictions).describe())

        if "future_return" in df_symbol.columns:
            corr = np.corrcoef(predictions, df_symbol["future_return"])[0, 1]
            print("\nCorrelation with future_return:", corr)

        print("\nSymbol evaluation finished.")

    print("\nMulti-symbol evaluation completed.")


if __name__ == "__main__":
    evaluate()