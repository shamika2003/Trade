# evaluator.py

import pandas as pd
import numpy as np
import joblib
from backtester import run_backtest
from feature_engine import FeatureTransformer
from config import MODEL_PATH, DATA_PATH


def evaluate():

    df = pd.read_csv(DATA_PATH)

    transformer = FeatureTransformer()
    df = transformer.build_features(df)

    features = transformer.get_feature_list()

    model = joblib.load(MODEL_PATH)

    pred_returns = model.predict(df[features])

    run_backtest(df.reset_index(drop=True), pred_returns)

    print("Prediction stats:")
    print(pd.Series(pred_returns).describe())

    corr = np.corrcoef(pred_returns, df["future_return"])[0,1]
    print("Prediction correlation:", corr)


if __name__ == "__main__":
    evaluate()