import joblib
import numpy as np
from core.logger import log


class Predictor:

    def __init__(self, smoothing_window=5):
        try:
            self.models = joblib.load("model/trading_model.pkl")
        except Exception as e:
            log(f"ERROR | Model load failed: {e}")
            self.models = {}

        self.window = smoothing_window
        self.buffer = {}

    def _smooth(self, symbol, val):
        buf = self.buffer.setdefault(symbol, [])
        buf.append(val)

        if len(buf) > self.window:
            buf.pop(0)

        return float(np.mean(buf))

    def predict(self, df, feature_list, symbol):
        if df is None or df.empty:
            return np.array([0.0])

        if not symbol or symbol == "UNKNOWN":
            log("ERROR | Invalid symbol passed to predictor")
            return np.array([0.0])

        if symbol not in self.models:
            log(f"WARNING | No model for symbol: {symbol}")
            return np.array([0.0])

        X = df.reindex(columns=feature_list).fillna(0)

        model_pack = self.models.get(symbol, {})

        preds = []

        for model_key in ["short", "long"]:
            model = model_pack.get(f"low_{model_key}")
            if model is None:
                continue

            try:
                p = model.predict(X)
                preds.append(p[-1])
            except Exception as e:
                log(f"ERROR | Prediction failed {symbol}: {e}")

        if not preds:
            return np.array([0.0])

        final = float(np.mean(preds))
        final = float(np.clip(final, -2, 2))

        final = self._smooth(symbol, final)

        return np.array([final])