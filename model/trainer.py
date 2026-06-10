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
# FIXED TARGET (NO TANH)
# ===============================
def make_signal_target(y, X):
    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    signal = y / (vol + 1e-6)
    signal = np.sign(signal) * np.log1p(np.abs(signal))

    return signal


# ===============================
# BETTER WEIGHTS
# ===============================
def compute_weights(y, X):
    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    weight = np.abs(y) / (vol + 1e-6)
    weight = np.sqrt(weight)

    return weight


# ===============================
# REALISTIC DIRECTIONAL ACC
# ===============================
def directional_accuracy(y_true, y_pred):
    threshold = 1e-5

    true_dir = np.where(np.abs(y_true) < threshold, 0, np.sign(y_true))
    pred_dir = np.where(np.abs(y_pred) < threshold, 0, np.sign(y_pred))

    mask = true_dir != 0

    if np.sum(mask) == 0:
        return 0.0

    return np.mean(true_dir[mask] == pred_dir[mask])


# ===============================
# TRAINING
# ===============================
def train():

    print("\n" + "═" * 80)
    print("🧠  QUANT TRAINING ENGINE INITIALIZED")
    print("═" * 80)
    print("📦 Loading dataset...\n")

    df = load_data()

    print("✔ Dataset loaded successfully")
    print(f"📊 Rows: {len(df)}")
    print("─" * 80)

    feature_engine = FeatureTransformer()
    features = feature_engine.get_feature_list()

    MODEL_PARAMS = dict(
        n_estimators=700,
        learning_rate=0.008,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        tree_method="hist",
        random_state=42
    )

    models = {}
    report = {}

    for symbol in SYMBOLS:

        print("\n" + "═" * 80)
        print(f"📈 SYMBOL PIPELINE: {symbol}")
        print("═" * 80)

        data = df[df["symbol"] == symbol].copy()

        if len(data) < 1200:
            print(f"⚠️  SKIPPED {symbol} | insufficient data ({len(data)})")
            continue

        print(f"📊 Active samples: {len(data)}")
        print("🔧 Preparing feature matrix...")

        X = data[features]
        y = make_signal_target(data["target_short"], X)

        tscv = TimeSeriesSplit(n_splits=5, gap=FUTURE_PERIOD)

        acc_list = []
        rmse_list = []

        for i, (train_idx, val_idx) in enumerate(tscv.split(X)):

            print("\n" + "·" * 60)
            print(f"🔁 FOLD {i+1}/5 ACTIVE")
            print("·" * 60)

            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            model = XGBRegressor(**MODEL_PARAMS)

            model.fit(
                X_train,
                y_train,
                sample_weight=compute_weights(y_train, X_train),
                verbose=False
            )

            pred = model.predict(X_val)
            pred_eval = np.clip(pred, -3, 3)

            rmse = np.sqrt(mean_squared_error(y_val, pred_eval))
            acc = directional_accuracy(y_val.values, pred_eval)

            rmse_list.append(rmse)
            acc_list.append(acc)

            print(f"📉 RMSE        : {rmse:.6f}")
            print(f"🎯 Direction   : {acc:.4f}")

        print("\n" + "─" * 80)
        print(f"📊 SYMBOL RESULT: {symbol}")
        print(f"   RMSE  (avg): {np.mean(rmse_list):.6f}")
        print(f"   ACC   (avg): {np.mean(acc_list):.4f}")
        print("─" * 80)

        final_model = XGBRegressor(**MODEL_PARAMS)

        final_model.fit(
            X,
            y,
            sample_weight=compute_weights(y, X),
            verbose=False
        )

        models[symbol] = final_model

        report[symbol] = {
            "rmse": float(np.mean(rmse_list)),
            "acc": float(np.mean(acc_list))
        }

    print("\n" + "═" * 80)
    print("📊 FINAL SYSTEM REPORT")
    print("═" * 80)

    for k, v in report.items():
        print(f"🔹 {k:<10} | RMSE: {v['rmse']:.6f} | ACC: {v['acc']:.4f}")

    print("\n💾 Saving trained models...")
    joblib.dump(models, MODEL_PATH)

    print("✔ SAVE COMPLETE")
    print(f"📁 Path: {MODEL_PATH}")
    print("═" * 80 + "\n")


if __name__ == "__main__":
    train()