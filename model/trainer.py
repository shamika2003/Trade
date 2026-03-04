# filename: trainer.py

import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error

from xgboost import XGBRegressor

from config import DATA_PATH, MODEL_PATH
from feature_engine import FeatureTransformer


# ============================================================
# Diagnostics
# ============================================================

def diagnostic_check(fold_scores, y, fold_direction_scores):

    print("\n========== MODEL HEALTH CHECK ==========")

    if len(fold_scores) == 0:
        print("No fold results available.")
        return

    mean_rmse = np.mean(fold_scores)
    std_rmse = np.std(fold_scores)

    target_std = np.std(y)

    print(f"CV RMSE Mean : {mean_rmse:.6f}")
    print(f"CV RMSE Std  : {std_rmse:.6f}")
    print(f"Target Std Scale : {target_std:.6f}")

    signal_ratio = target_std / (mean_rmse + 1e-9)

    print(f"Alpha Strength Ratio : {signal_ratio:.3f}")

    if signal_ratio < 1.2:
        print("Signal may be weak for deployment.")

    elif signal_ratio > 2.5:
        print("Strong predictive signal detected.")

    if len(fold_direction_scores) > 0:
        print(f"Directional Accuracy Mean : {np.mean(fold_direction_scores):.4f}")

    if std_rmse > mean_rmse * 0.5:
        print("WARNING: Possible model instability across folds.")

    print("========================================\n")


# ============================================================
# Data Loader
# ============================================================

def load_data():

    df = pd.read_csv(DATA_PATH)

    if "time" in df.columns:
        df = df.drop(columns=["time"])

    transformer = FeatureTransformer()
    feature_list = transformer.get_feature_list()

    missing_features = [f for f in feature_list if f not in df.columns]

    if missing_features:
        raise RuntimeError(f"Missing features: {missing_features}")

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    X = df[feature_list]
    y = df["future_return"]

    return X, y


# ============================================================
# Training Pipeline
# ============================================================

def train():

    print("Loading dataset...")

    X, y = load_data()

    if len(X) < 500:
        raise RuntimeError("Dataset too small")

    print("Building model...")

    MODEL_PARAMS = dict(
        n_estimators=800,
        learning_rate=0.01,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        objective="reg:pseudohubererror",
        gamma=0.9,
        random_state=42,
        tree_method="hist"
    )

    tscv = TimeSeriesSplit(n_splits=5, gap=12)

    fold_scores = []
    fold_direction_scores = []

    transformer = FeatureTransformer()
    feature_list = transformer.get_feature_list()

    print("Training cross-validation folds...")

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):

        print(f"\nFold {fold+1}")

        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        if len(X_train) < 50:
            continue

        # Noise-aware sample weighting
        sample_weight = np.clip(
            np.abs(y_train) * 800 + 1e-6,
            1e-6,
            5
        )

        model = XGBRegressor(**MODEL_PARAMS)

        model.fit(
            X_train,
            y_train,
            sample_weight=sample_weight,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        pred = model.predict(X_val)

        rmse = np.sqrt(mean_squared_error(y_val, pred))
        fold_scores.append(rmse)

        direction_acc = np.mean(
            np.sign(y_val.values) == np.sign(pred)
        )

        fold_direction_scores.append(direction_acc)

        print(f"Fold RMSE: {rmse:.6f}")
        print(f"Directional Accuracy: {direction_acc:.4f}")

    print("\nCross-Validation RMSE:", np.mean(fold_scores))

    diagnostic_check(fold_scores, y, fold_direction_scores)

    # ====================================================
    # Final Training
    # ====================================================

    print("Training final model on full dataset...")

    final_model = XGBRegressor(**MODEL_PARAMS)

    sample_weight_full = np.clip(
        np.abs(y) * 800 + 1e-6,
        1e-6,
        5
    )

    final_model.fit(
        X,
        y,
        sample_weight=sample_weight_full,
        verbose=False
    )

    joblib.dump(final_model, MODEL_PATH)

    print("Model saved to:", MODEL_PATH)


# ============================================================

if __name__ == "__main__":
    train()