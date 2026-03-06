# filename: trainer.py

import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor

from config import DATA_PATH, MODEL_PATH, FUTURE_PERIOD, SYMBOLS
from feature_engine import FeatureTransformer


# ===============================
# Data Loader
# ===============================

def load_data():
    df = pd.read_csv(DATA_PATH)

    if "time" in df.columns:
        df.drop(columns=["time"], inplace=True)

    feature_engine = FeatureTransformer()
    feature_list = feature_engine.get_feature_list()

    missing = [f for f in feature_list if f not in df.columns]
    if missing:
        raise RuntimeError(f"Missing features: {missing}")

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    return df


# ===============================
# Weighting Function
# ===============================

def compute_weights(y, X):
    vol = X["volatility"].replace(0, np.nan).fillna(
        X["volatility"].median()
    )

    weight = np.abs(y) / (vol + 1e-9)

    weight = np.clip(weight * 2, 1e-6, 5)
    return np.maximum(weight, 1e-6)


# ===============================
# Diagnostics
# ===============================

def diagnostic_report(report_dict):
    print("\n===== TRAINING SUMMARY =====")

    for symbol, stats in report_dict.items():
        print(f"\nSymbol: {symbol}")
        print(f"CV RMSE Mean : {stats['rmse_mean']:.6f}")
        print(f"Directional Accuracy : {stats['dir_acc']:.4f}")

    print("=============================\n")


# ===============================
# Training Pipeline
# ===============================

def train():

    print("Loading dataset...")
    df = load_data()

    feature_engine = FeatureTransformer()
    feature_list = feature_engine.get_feature_list()

    MODEL_PARAMS = dict(
        n_estimators=600,
        learning_rate=0.015,
        max_depth=4,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=2,
        objective="reg:pseudohubererror",
        gamma=0.8,
        random_state=42,
        tree_method="hist"
    )

    symbol_model_package = {}

    report_stats = {}

    for symbol in SYMBOLS:

        print(f"\n==============================")
        print(f"Training Symbol: {symbol}")
        print(f"==============================")

        symbol_df = df[df["symbol"] == symbol].copy()

        if len(symbol_df) < 500:
            print(f"Skip {symbol}: dataset too small")
            continue

        X = symbol_df[feature_list]
        y_short = symbol_df["target_short"]
        y_long = symbol_df["target_long"]

        tscv = TimeSeriesSplit(
            n_splits=5,
            gap=FUTURE_PERIOD
        )

        fold_rmse = []
        fold_dir = []

        print("Walk-forward validation...")

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            
            print(f"\nFold {fold+1}")

            X_train = X.iloc[train_idx]
            X_val = X.iloc[val_idx]

            y_train = y_short.iloc[train_idx]
            y_val = y_short.iloc[val_idx]

            if len(X_train) < 100:
                continue

            model = XGBRegressor(**MODEL_PARAMS)

            model.fit(
                X_train,
                y_train,
                sample_weight=compute_weights(y_train, X_train),
                eval_set=[(X_val, y_val)],
                verbose=False
            )

            pred = model.predict(X_val)

            rmse = np.sqrt(mean_squared_error(y_val, pred))
            fold_rmse.append(rmse)

            fold_dir.append(
                np.mean(
                    np.sign(y_val.values) ==
                    np.sign(pred)
                )
            )

            print(f"RMSE : {rmse:.6f}")
            print(f"Directional Acc : {fold_dir[-1]:.4f}")

        print("Training final ensemble models...")

        # Regime split
        high_mask = symbol_df["volatility_regime"] == 1
        low_mask = symbol_df["volatility_regime"] == 0

        X_high = X[high_mask]
        X_low = X[low_mask]

        y_high_short = y_short[high_mask]
        y_low_short = y_short[low_mask]

        y_high_long = y_long[high_mask]
        y_low_long = y_long[low_mask]

        MODEL_HIGH_SHORT = XGBRegressor(**MODEL_PARAMS)
        MODEL_HIGH_LONG = XGBRegressor(**MODEL_PARAMS)
        MODEL_LOW_SHORT = XGBRegressor(**MODEL_PARAMS)
        MODEL_LOW_LONG = XGBRegressor(**MODEL_PARAMS)

        print("Fit HIGH regime models")

        MODEL_HIGH_SHORT.fit(
            X_high,
            y_high_short,
            sample_weight=compute_weights(y_high_short, X_high),
            verbose=False
        )

        MODEL_HIGH_LONG.fit(
            X_high,
            y_high_long,
            sample_weight=compute_weights(y_high_long, X_high),
            verbose=False
        )

        print("Fit LOW regime models")

        MODEL_LOW_SHORT.fit(
            X_low,
            y_low_short,
            sample_weight=compute_weights(y_low_short, X_low),
            verbose=False
        )

        MODEL_LOW_LONG.fit(
            X_low,
            y_low_long,
            sample_weight=compute_weights(y_low_long, X_low),
            verbose=False
        )

        symbol_model_package[symbol] = {
            "high_short": MODEL_HIGH_SHORT,
            "high_long": MODEL_HIGH_LONG,
            "low_short": MODEL_LOW_SHORT,
            "low_long": MODEL_LOW_LONG
        }

        report_stats[symbol] = {
            "rmse_mean": np.mean(fold_rmse) if fold_rmse else 0,
            "dir_acc": np.mean(fold_dir) if fold_dir else 0
        }

    diagnostic_report(report_stats)

    print("Saving models...")

    joblib.dump(symbol_model_package, MODEL_PATH)

    print("Multi-symbol ensemble training completed.")
    print("Model path:", MODEL_PATH)


if __name__ == "__main__":
    train()