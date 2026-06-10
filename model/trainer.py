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
# Load Data
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
# BETTER TARGET (IMPORTANT FIX)
# ===============================

def make_signal_target(y, X):
    """
    Removes noise-dominated samples by scaling signal strength.
    """
    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    # normalize signal strength
    signal = y / (vol + 1e-6)

    # amplify meaningful moves, suppress noise
    signal = np.tanh(signal * 5)

    return signal


# ===============================
# Directional Accuracy (REALISTIC)
# ===============================

def directional_accuracy(y_true, y_pred):
    # ignore tiny noise movements
    threshold = 0.00005

    true_dir = np.where(np.abs(y_true) < threshold, 0, np.sign(y_true))
    pred_dir = np.where(np.abs(y_pred) < threshold, 0, np.sign(y_pred))

    mask = true_dir != 0  # ignore flat noise zones

    if np.sum(mask) == 0:
        return 0

    return np.mean(true_dir[mask] == pred_dir[mask])


# ===============================
# Weights (STABLE FIX)
# ===============================

def compute_weights(y, X):
    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    weight = np.abs(y) / (vol + 1e-6)

    # reduce explosion
    return np.clip(weight, 0.3, 2.0)


# ===============================
# TRAINING
# ===============================

def train():

    print("Loading dataset...")
    df = load_data()

    feature_engine = FeatureTransformer()
    features = feature_engine.get_feature_list()

    MODEL_PARAMS = dict(
        n_estimators=600,
        learning_rate=0.01,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        objective="reg:pseudohubererror",
        tree_method="hist",
        random_state=42
    )

    models = {}
    report = {}

    for symbol in SYMBOLS:

        print(f"\n===== {symbol} =====")

        data = df[df["symbol"] == symbol].copy()

        if len(data) < 1200:
            print("Skip: not enough data")
            continue

        X = data[features]

        # USE BOTH TARGETS (FIXED)
        y_s = make_signal_target(data["target_short"], X)
        y_l = make_signal_target(data["target_long"], X)

        tscv = TimeSeriesSplit(n_splits=5, gap=FUTURE_PERIOD)

        acc_list = []
        rmse_list = []

        for i, (train_idx, val_idx) in enumerate(tscv.split(X)):

            print(f"Fold {i+1}")

            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y_s.iloc[train_idx], y_s.iloc[val_idx]

            model = XGBRegressor(**MODEL_PARAMS)

            model.fit(
                X_train,
                y_train,
                sample_weight=compute_weights(y_train, X_train),
                verbose=False
            )

            pred = model.predict(X_val)

            pred = np.clip(pred, -1, 1)

            rmse = np.sqrt(mean_squared_error(y_val, pred))
            acc = directional_accuracy(y_val.values, pred)

            rmse_list.append(rmse)
            acc_list.append(acc)

            print("RMSE:", round(rmse, 6))
            print("DIR ACC:", round(acc, 4))

        # FINAL MODEL (TRAIN FULL DATA)
        final_model = XGBRegressor(**MODEL_PARAMS)

        final_model.fit(
            X,
            y_s,
            sample_weight=compute_weights(y_s, X),
            verbose=False
        )

        models[symbol] = final_model

        report[symbol] = {
            "rmse": float(np.mean(rmse_list)),
            "acc": float(np.mean(acc_list))
        }

    print("\n===== SUMMARY =====")
    for k, v in report.items():
        print(k, v)

    joblib.dump(models, MODEL_PATH)
    print("\nSaved to:", MODEL_PATH)


if __name__ == "__main__":
    train()