# filename: feature_importance_test.py

import pandas as pd
import numpy as np

from xgboost import XGBRegressor

from config import DATA_PATH, SYMBOLS
from feature_engine import FeatureTransformer


def load_data():

    df = pd.read_csv(DATA_PATH)

    feature_engine = FeatureTransformer()
    features = feature_engine.get_feature_list()

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

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

    for symbol in SYMBOLS:

        print("\n" + "=" * 60)
        print(symbol)
        print("=" * 60)

        data = df[df["symbol"] == symbol].copy()

        if len(data) < 1000:
            continue

        X = data[features]

        y = make_signal_target(
            data["target_short"],
            X
        )

        model = XGBRegressor(**MODEL_PARAMS)

        model.fit(
            X,
            y,
            verbose=False
        )

        importance = pd.Series(
            model.feature_importances_,
            index=features
        )

        importance = importance.sort_values(
            ascending=False
        )

        print("\nTOP 20 FEATURES\n")

        print(
            importance.head(20)
        )


if __name__ == "__main__":
    train_feature_importance()