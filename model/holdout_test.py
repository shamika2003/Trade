# filename: holdout_test.py

import pandas as pd
import numpy as np

from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor

from config_model import DATA_PATH, SYMBOLS
from feature_engine import FeatureTransformer


# ===============================
# Load Data
# ===============================

def load_data():

    print("\n" + "═" * 80)
    print("🧪  HOLDOUT VALIDATION ENGINE")
    print("═" * 80)
    print("📂 Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    print(f"✔ Dataset loaded | Rows: {len(df):,}")

    feature_engine = FeatureTransformer()
    features = feature_engine.get_feature_list()

    missing = [f for f in features if f not in df.columns]

    if missing:
        raise RuntimeError(f"Missing features: {missing}")

    print(f"🧠 Feature set loaded | Features: {len(features)}")

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    print(f"🧹 Cleaned dataset | Rows: {len(df):,}")
    print("═" * 80)

    return df


# ===============================
# Same target as trainer
# ===============================

def make_signal_target(y, X):

    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    signal = y / (vol + 1e-6)
    signal = np.tanh(signal * 5)

    return signal


# ===============================
# Same directional accuracy
# ===============================

def directional_accuracy(y_true, y_pred):

    threshold = 0.00005

    true_dir = np.where(
        np.abs(y_true) < threshold,
        0,
        np.sign(y_true)
    )

    pred_dir = np.where(
        np.abs(y_pred) < threshold,
        0,
        np.sign(y_pred)
    )

    mask = true_dir != 0

    if mask.sum() == 0:
        return 0

    return np.mean(true_dir[mask] == pred_dir[mask])


# ===============================
# Same weights
# ===============================

def compute_weights(y, X):

    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    weight = np.abs(y) / (vol + 1e-6)

    return np.clip(weight, 0.3, 2.0)


# ===============================
# Holdout Test
# ===============================

def run_holdout():

    print("\n" + "═" * 80)
    print("🚀 STARTING HOLDOUT EVALUATION PIPELINE")
    print("═" * 80)

    df = load_data()

    transformer = FeatureTransformer()
    features = transformer.get_feature_list()

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

    summary = {}

    for symbol in SYMBOLS:

        print("\n" + "═" * 80)
        print(f"📈 SYMBOL HOLDOUT: {symbol}")
        print("═" * 80)

        symbol_df = df[df["symbol"] == symbol].copy()

        if len(symbol_df) < 2000:
            print(f"⚠️ Skip {symbol} | insufficient rows ({len(symbol_df):,})")
            continue

        if "time" in symbol_df.columns:
            symbol_df = symbol_df.sort_values("time")

        symbol_df = symbol_df.reset_index(drop=True)

        split_index = int(len(symbol_df) * 0.8)

        train_df = symbol_df.iloc[:split_index]
        test_df = symbol_df.iloc[split_index:]

        print(f"📊 Train rows : {len(train_df):,}")
        print(f"📊 Test rows  : {len(test_df):,}")

        X_train = train_df[features]
        X_test = test_df[features]

        y_train = make_signal_target(train_df["target_short"], X_train)
        y_test = make_signal_target(test_df["target_short"], X_test)

        model = XGBRegressor(**MODEL_PARAMS)

        print("🧠 Training model...")

        model.fit(
            X_train,
            y_train,
            sample_weight=compute_weights(y_train, X_train),
            verbose=False
        )

        print("📊 Generating predictions...")

        predictions = model.predict(X_test)
        predictions = np.clip(predictions, -1, 1)

        rmse = np.sqrt(
            mean_squared_error(
                y_test,
                predictions
            )
        )

        acc = directional_accuracy(
            y_test.values,
            predictions
        )

        corr = np.corrcoef(
            predictions,
            y_test
        )[0, 1]

        print("\n" + "─" * 80)
        print(f"📊 RESULTS | {symbol}")
        print("─" * 80)

        print(f"📉 RMSE : {rmse:.6f}")
        print(f"🎯 ACC  : {acc:.4f}")
        print(f"📈 CORR : {corr:.4f}")

        print("─" * 80)

        summary[symbol] = {
            "rmse": float(rmse),
            "acc": float(acc),
            "corr": float(corr)
        }

    print("\n" + "═" * 80)
    print("📊 FINAL HOLDOUT SUMMARY")
    print("═" * 80)

    for symbol, stats in summary.items():

        print(f"🔹 {symbol}")

        print(
            f"RMSE={stats['rmse']:.6f} "
            f"ACC={stats['acc']:.4f} "
            f"CORR={stats['corr']:.4f}"
        )

        print()

    print("✔ Holdout evaluation completed successfully")
    print("═" * 80 + "\n")


if __name__ == "__main__":
    run_holdout()