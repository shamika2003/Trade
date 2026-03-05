# evaluator.py

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

    X = df[features]

    # ==============================
    # Regime Split
    # ==============================

    regime_threshold = df["volatility_regime"].median()

    high_mask = df["volatility_regime"] > regime_threshold
    low_mask = ~high_mask

    predictions = np.zeros(len(df))

    # ==============================
    # HIGH VOLATILITY REGIME
    # ==============================

    if high_mask.sum() > 0:

        short_pred = model_dict["high_short"].predict(X.loc[high_mask])
        long_pred = model_dict["high_long"].predict(X.loc[high_mask])

        predictions[high_mask] = (short_pred + long_pred) / 2

    # ==============================
    # LOW VOLATILITY REGIME
    # ==============================

    if low_mask.sum() > 0:

        short_pred = model_dict["low_short"].predict(X.loc[low_mask])
        long_pred = model_dict["low_long"].predict(X.loc[low_mask])

        predictions[low_mask] = (short_pred + long_pred) / 2

    # ==============================
    # Run Backtest
    # ==============================

    run_backtest(df.reset_index(drop=True), predictions)

    print("\nPrediction stats:")
    print(pd.Series(predictions).describe())

    if "future_return" in df.columns:

        corr = np.corrcoef(predictions, df["future_return"])[0, 1]
        print("Prediction correlation:", corr)


if __name__ == "__main__":
    evaluate()