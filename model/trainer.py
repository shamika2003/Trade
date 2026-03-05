import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error

from xgboost import XGBRegressor

from config import DATA_PATH, MODEL_PATH
from feature_engine import FeatureTransformer


# ===============================
# Data Loader
# ===============================

def load_data():

    df = pd.read_csv(DATA_PATH)

    if "time" in df.columns:
        df = df.drop(columns=["time"])

    transformer = FeatureTransformer()
    feature_list = transformer.get_feature_list()

    missing = [f for f in feature_list if f not in df.columns]

    if missing:
        raise RuntimeError(f"Missing features: {missing}")

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    X = df[feature_list]

    y_short = df["target_short"]
    y_long = df["target_long"]

    return X, y_short, y_long


# ===============================
# Weighting
# ===============================

def compute_weights(y, X):

    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    weight = np.abs(y) / (vol + 1e-9)

    weight = np.clip(weight * 2, 1e-6, 5)

    weight = np.maximum(weight, 1e-6)

    return weight


# ===============================
# Regime Split
# ===============================

def split_regime_data(X, y):

    regime = X["volatility_regime"]

    high_mask = regime == 1
    low_mask = regime == 0

    return (
        X[high_mask], y[high_mask],
        X[low_mask], y[low_mask]
    )


# ===============================
# Diagnostics
# ===============================

def diagnostic_report(fold_rmse, fold_dir):

    print("\n===== MODEL DIAGNOSTICS =====")

    if len(fold_rmse) == 0:
        return

    print(f"CV RMSE Mean : {np.mean(fold_rmse):.6f}")
    print(f"CV RMSE Std  : {np.std(fold_rmse):.6f}")
    print(f"Directional Accuracy : {np.mean(fold_dir):.4f}")

    print("=============================\n")




def entropy_filter(X, y_short, y_long, threshold=0.35):

    print("Samples before entropy filter:", len(X))

    vol = X["volatility"].fillna(X["volatility"].median())

    # entropy proxy using both targets
    entropy_short = np.abs(y_short) / (vol + 1e-9)
    entropy_long = np.abs(y_long) / (vol + 1e-9)

    entropy_score = (entropy_short + entropy_long) / 2

    mask = entropy_score > threshold

    X = X.loc[mask].copy()
    y_short = y_short.loc[mask].copy()
    y_long = y_long.loc[mask].copy()

    print("Samples after entropy filter:", len(X))

    return X, y_short, y_long


# ===============================
# Training Pipeline
# ===============================

def train():

    print("Loading dataset...")

    X, y_short, y_long = load_data()

    X, y_short, y_long = entropy_filter(X, y_short, y_long)

    if len(X) < 500:
        raise RuntimeError("Dataset too small")

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

    tscv = TimeSeriesSplit(n_splits=5, gap=12)

    fold_rmse = []
    fold_dir = []

    print("Starting walk-forward validation...")

    # ======================================================
    # Walk Forward Validation (Short Target Primary Signal)
    # ======================================================

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
            np.mean(np.sign(y_val.values) == np.sign(pred))
        )

        print(f"RMSE : {rmse:.6f}")
        print(f"Directional Acc : {fold_dir[-1]:.4f}")

    diagnostic_report(fold_rmse, fold_dir)

    # ======================================================
    # Final Ensemble Training
    # ======================================================

    print("Training regime-aware ensemble models...")

    regime = X["volatility_regime"]

    X_high, y_high_short, X_low, y_low_short = split_regime_data(
        X, y_short
    )

    _, y_high_long, _, y_low_long = split_regime_data(
        X, y_long
    )

    # Models

    MODEL_HIGH_SHORT = XGBRegressor(**MODEL_PARAMS)
    MODEL_HIGH_LONG = XGBRegressor(**MODEL_PARAMS)

    MODEL_LOW_SHORT = XGBRegressor(**MODEL_PARAMS)
    MODEL_LOW_LONG = XGBRegressor(**MODEL_PARAMS)

    print("Training HIGH regime models...")

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

    print("Training LOW regime models...")

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

    # ======================================================
    # Save Ensemble Package Safely
    # ======================================================

    ensemble_package = {
        "high_short": MODEL_HIGH_SHORT,
        "high_long": MODEL_HIGH_LONG,
        "low_short": MODEL_LOW_SHORT,
        "low_long": MODEL_LOW_LONG
    }

    joblib.dump(ensemble_package, MODEL_PATH)

    print("Ensemble models saved:", MODEL_PATH)


# ===============================

if __name__ == "__main__":
    train()