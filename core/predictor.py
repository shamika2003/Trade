# filename: predictor.py

import joblib
import numpy as np
from config import MODEL_PATH


class Predictor:

    def __init__(self):

        self.models = joblib.load(MODEL_PATH)

    # ======================================
    # Regime Selection Helper
    # ======================================

    def _select_model(self, df):

        regime = df["volatility_regime"].iloc[-1]

        if regime > 0.75:
            regime_key = "high"
        else:
            regime_key = "low"

        return regime_key

    # ======================================
    # Prediction Engine
    # ======================================

    def predict(self, df, feature_list):

        df = df.ffill().dropna()

        if df.empty:
            return np.array([0])

        regime = self._select_model(df)

        # Use short horizon trading signal (primary driver)
        model = self.models[f"{regime}_short"]

        pred = model.predict(df[feature_list])

        return np.array(pred)