# filename: predictor.py

import joblib
import numpy as np
from config import MODEL_PATH


class Predictor:

    def __init__(self):

        self.models = joblib.load(MODEL_PATH)

        if not isinstance(self.models, dict):
            raise RuntimeError("Model file must contain dictionary of models")

    # =====================================================
    # Regime Selection Helper
    # =====================================================

    def _select_model(self, df):

        if "volatility_regime" not in df.columns:
            return "low"

        regime = df["volatility_regime"].iloc[-1]

        return "high" if regime > 0.75 else "low"

    # =====================================================
    # Prediction Engine
    # =====================================================

    def predict(self, df, feature_list):

        df = df.ffill().dropna()

        if df.empty:
            return np.array([0])

        regime = self._select_model(df)

        model_key = f"{regime}_short"

        # Safety check for model existence
        if model_key not in self.models:
            print(f"Warning: Model {model_key} not found. Using fallback prediction.")
            return np.array([0])

        model = self.models[model_key]

        try:
            pred = model.predict(df[feature_list])
            return np.array(pred)

        except Exception as e:
            print("Prediction error:", e)
            return np.array([0])