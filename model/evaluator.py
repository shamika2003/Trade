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

    print("Loading trained ensemble model...")
    model_dict = joblib.load(MODEL_PATH)

    all_symbols = df["symbol"].unique()

    print("\nEvaluating symbols:", all_symbols)

    for symbol in all_symbols:

        print(f"\n========== Evaluating {symbol} ==========")

        # ---------------------------------------
        # Load symbol models
        # ---------------------------------------

        symbol_models = model_dict.get(symbol)

        if symbol_models is None:
            print(f"No trained model for {symbol}, skipping.")
            continue

        df_symbol = df[df["symbol"] == symbol].copy()

        if "time" in df_symbol.columns:
            df_symbol = df_symbol.sort_values("time")

        df_symbol = df_symbol.reset_index(drop=True)

        # ---------------------------------------
        # Feature validation
        # ---------------------------------------

        missing_features = [f for f in features if f not in df_symbol.columns]

        if len(missing_features) > 0:
            raise RuntimeError(
                f"{symbol} missing features: {missing_features}"
            )

        X = df_symbol[features].copy()

        # Replace NaN and inf values
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)

        # ---------------------------------------
        # Regime split
        # ---------------------------------------

        if "volatility_regime" not in df_symbol.columns:
            raise RuntimeError(
                "Feature 'volatility_regime' missing. "
                "Feature engine must generate it."
            )

        vol = df_symbol["volatility_regime"]

        high_mask = vol > 0.7
        low_mask = vol < 0.3
        mid_mask = ~(high_mask | low_mask)

        predictions = np.zeros(len(df_symbol))

        # ---------------------------------------
        # HIGH VOLATILITY REGIME
        # ---------------------------------------

        if high_mask.sum() > 0:

            short_pred = symbol_models["high_short"].predict(
                X.loc[high_mask]
            )

            long_pred = symbol_models["high_long"].predict(
                X.loc[high_mask]
            )

            predictions[high_mask] = (short_pred + long_pred) / 2

        # ---------------------------------------
        # LOW VOLATILITY REGIME
        # ---------------------------------------

        if low_mask.sum() > 0:

            short_pred = symbol_models["low_short"].predict(
                X.loc[low_mask]
            )

            long_pred = symbol_models["low_long"].predict(
                X.loc[low_mask]
            )

            predictions[low_mask] = (short_pred + long_pred) / 2

        # ---------------------------------------
        # MID VOLATILITY REGIME
        # ---------------------------------------

        if mid_mask.sum() > 0:

            short_pred = symbol_models["low_short"].predict(
                X.loc[mid_mask]
            )

            long_pred = symbol_models["high_long"].predict(
                X.loc[mid_mask]
            )

            predictions[mid_mask] = (short_pred + long_pred) / 2

        # ---------------------------------------
        # Prediction sanity check
        # ---------------------------------------

        if np.isnan(predictions).any():
            print("WARNING: NaN predictions detected")
            predictions = np.nan_to_num(predictions)

        # ---------------------------------------
        # Backtest
        # ---------------------------------------

        results = run_backtest(
            df_symbol.reset_index(drop=True),
            predictions
        )

        # ---------------------------------------
        # Prediction statistics
        # ---------------------------------------

        print("\nPrediction statistics:")

        stats = pd.Series(predictions).describe()

        print(stats)

        # ---------------------------------------
        # Optional correlation check
        # ---------------------------------------

        if "future_return" in df_symbol.columns:

            corr = np.corrcoef(
                predictions,
                df_symbol["future_return"]
            )[0, 1]

            print("\nPrediction correlation with future_return:", corr)

        print("\nSymbol evaluation finished.")

    print("\nMulti-symbol evaluation completed.")


if __name__ == "__main__":
    evaluate()