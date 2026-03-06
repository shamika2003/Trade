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

    transformer = FeatureTransformer()
    features = transformer.get_feature_list()

    print("Loading trained ensemble model...")
    model_dict = joblib.load(MODEL_PATH)

    if "symbol" not in df.columns:
        raise RuntimeError("Dataset missing symbol column")

    all_symbols = df["symbol"].unique()

    print("\nEvaluating symbols:", all_symbols)

    for symbol in all_symbols:

        print(f"\n========== Evaluating {symbol} ==========")

        df_symbol = df[df["symbol"] == symbol].copy()

        df_symbol = df_symbol.reset_index(drop=True)

        X = df_symbol[features]

        # ==============================
        # Regime Split (Symbol Local)
        # ==============================

        regime_threshold = df_symbol["volatility_regime"].median()

        high_mask = df_symbol["volatility_regime"] > regime_threshold
        low_mask = ~high_mask

        predictions = np.zeros(len(df_symbol))

        # ==============================
        # HIGH VOLATILITY REGIME
        # ==============================

        if high_mask.sum() > 0:

            short_pred = model_dict["high_short"].predict(
                X.loc[high_mask]
            )

            long_pred = model_dict["high_long"].predict(
                X.loc[high_mask]
            )

            predictions[high_mask] = (short_pred + long_pred) / 2

        # ==============================
        # LOW VOLATILITY REGIME
        # ==============================

        if low_mask.sum() > 0:

            short_pred = model_dict["low_short"].predict(
                X.loc[low_mask]
            )

            long_pred = model_dict["low_long"].predict(
                X.loc[low_mask]
            )

            predictions[low_mask] = (short_pred + long_pred) / 2

        # ==============================
        # Backtest per Symbol
        # ==============================

        run_backtest(
            df_symbol.reset_index(drop=True),
            predictions
        )

        print("\nPrediction stats:")
        print(pd.Series(predictions).describe())

        if "future_return" in df_symbol.columns:

            corr = np.corrcoef(
                predictions,
                df_symbol["future_return"]
            )[0, 1]

            print("Prediction correlation:", corr)

    print("\nMulti-symbol evaluation completed.")


if __name__ == "__main__":
    evaluate()