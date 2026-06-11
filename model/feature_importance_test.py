# filename: feature_importance_test.py

import pandas as pd
import numpy as np

from xgboost import XGBRegressor

from config import DATA_PATH, SYMBOLS
from feature_engine import FeatureTransformer


def load_data():

    print("\n" + "═" * 80)
    print("🔬 FEATURE IMPORTANCE ANALYSIS ENGINE")
    print("═" * 80)
    print("📂 Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    print(f"✔ Dataset loaded | Rows: {len(df):,}")

    feature_engine = FeatureTransformer()
    features = feature_engine.get_feature_list()

    print(f"🧠 Features detected: {len(features)}")
    print("─" * 80)

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    print("🧹 Dataset cleaned (NaN / Inf removed)")
    print(f"📊 Clean rows: {len(df):,}")
    print("═" * 80)

    return df, features


def make_signal_target(y, X):

    vol = X["volatility"].replace(0, np.nan)
    vol = vol.fillna(vol.median())

    signal = y / (vol + 1e-6)
    signal = np.tanh(signal * 5)

    return signal


def train_feature_importance():

    df, features = load_data()

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

    print("\n🚀 Starting feature importance training...\n")

    for symbol in SYMBOLS:

        print("\n" + "═" * 80)
        print(f"📈 SYMBOL ANALYSIS: {symbol}")
        print("═" * 80)

        data = df[df["symbol"] == symbol].copy()

        if len(data) < 1000:
            print(f"⚠️ Skipped {symbol} (insufficient data: {len(data):,})")
            continue

        print(f"📊 Training samples: {len(data):,}")
        print("🧠 Preparing feature matrix...")

        X = data[features]

        y = make_signal_target(
            data["target_short"],
            X
        )

        print("⚙️ Training XGBoost model...")

        model = XGBRegressor(**MODEL_PARAMS)

        model.fit(
            X,
            y,
            verbose=False
        )

        print("✔ Model trained successfully")
        print("📊 Extracting feature importance...")

        importance = pd.Series(
            model.feature_importances_,
            index=features
        )

        importance = importance.sort_values(ascending=False)

        print("\n" + "─" * 80)
        print("🏆 TOP 20 FEATURES")
        print("─" * 80)

        top20 = importance.head(20)

        for i, (feat, val) in enumerate(top20.items(), 1):
            print(f"{i:02d}. {feat:<30} {val:.6f}")

        print("─" * 80)
        print(f"✔ Analysis complete for {symbol}")
        print("═" * 80)


if __name__ == "__main__":
    train_feature_importance()