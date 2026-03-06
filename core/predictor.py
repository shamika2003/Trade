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
    # Regime Selector
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

        if df is None or df.empty:
            return np.array([0])

        df = df.copy()

        if "symbol" not in df.columns:
            print("Warning: Symbol missing in live dataframe")
            return np.array([0])

        df = df.ffill().dropna()

        if df.empty:
            return np.array([0])

        symbol = df["symbol"].iloc[-1]

        # ⭐ Symbol-level model routing (CRITICAL FIX)
        if symbol not in self.models:
            print(f"Warning: Model for {symbol} not found")
            return np.array([0])

        regime = self._select_model(df)

        model_key = f"{regime}_short"

        if model_key not in self.models[symbol]:
            print(f"Warning: Model {model_key} not found for {symbol}")
            return np.array([0])

        model = self.models[symbol][model_key]

        try:

            X = df[feature_list]

            if X.empty:
                return np.array([0])

            pred = model.predict(X)

            return np.array(pred)

        except Exception as e:
            print("Prediction error:", e)
            return np.array([0])