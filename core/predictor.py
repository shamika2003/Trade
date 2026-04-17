# filename: predictor.py

import joblib
import numpy as np
from core.logger import log
from config import CONFIDENCE_WEIGHT


class Predictor:

    def __init__(self, smoothing_window=5):
        try:
            self.models = joblib.load("model/trading_model.pkl")
            log("INFO | Models loaded successfully")
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
            return None

        if symbol not in self.models:
            return None

        try:
            X = df.reindex(columns=feature_list).fillna(0)
        except Exception:
            return None

        model_pack = self.models.get(symbol, {})

        preds = []

        # -------------------------
        # COLLECT MODEL OUTPUTS
        # -------------------------
        for model_key in ["short", "long"]:
            model = model_pack.get(f"low_{model_key}")

            if model is None:
                continue

            try:
                p = model.predict(X)
                preds.append(float(p[-1]))
            except Exception as e:
                log(f"ERROR | Prediction failed {symbol}: {e}")

        if len(preds) == 0:
            return None

        # -------------------------
        # SIGNAL
        # -------------------------
        signal = float(np.mean(preds))
        signal = float(np.clip(signal, -2, 2))
        signal = self._smooth(symbol, signal)

        # -------------------------
        # AGREEMENT (IMPORTANT PART)
        # -------------------------
        if len(preds) >= 2:
            agreement = 1.0 - (abs(preds[0] - preds[1]) / 4.0)
        else:
            agreement = 0.5

        agreement = float(np.clip(agreement, 0, 1))

        # -------------------------
        # CONFIDENCE SCORE
        # -------------------------
        strength = min(1.0, abs(signal) / 2.0)

        confidence = (
            CONFIDENCE_WEIGHT * agreement +
            (1 - CONFIDENCE_WEIGHT) * strength
        )

        return {
            "signal": signal,
            "confidence": confidence,
            "agreement": agreement
        }