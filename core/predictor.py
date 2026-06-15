# filename: predictor.py

import numpy as np
import joblib
import os

from core.logger import log
from core.feature_engine_live import FeatureTransformerLive


# =====================================================
# PREDICTOR (REGRESSION-BASED TRADING MODEL)
# =====================================================
class Predictor:

    def __init__(self, model_path="model/trading_model.pkl"):

        self.model_path = model_path
        self.models = None

        self.feature_engine = FeatureTransformerLive()
        self.feature_list = self.feature_engine.get_feature_list()

        self._load_model()

    # =================================================
    # LOAD MODEL
    # =================================================
    def _load_model(self):

        try:
            if not os.path.exists(self.model_path):
                log(f"ERROR | Model not found: {self.model_path}")
                self.models = None
                return

            self.models = joblib.load(self.model_path)

            log("INFO | Predictor model loaded")

        except Exception as e:
            log(f"ERROR | Model load failed: {e}")
            self.models = None

    # =================================================
    # FEATURE ALIGNMENT
    # =================================================
    def _prepare_features(self, df):

        try:
            df = df.copy()

            missing = [f for f in self.feature_list if f not in df.columns]

            if missing:
                log(f"WARNING | Missing features: {missing}")
                return None

            X = df[self.feature_list].replace([np.inf, -np.inf], np.nan)
            X = X.fillna(0)

            return X

        except Exception as e:
            log(f"ERROR | Feature prep failed: {e}")
            return None

    # =================================================
    # REGRESSION-BASED PREDICTION ENGINE
    # =================================================
    def _predict_regression(self, model, X):

        pred = model.predict(X)[-1]

        signal_value = float(pred)

        # normalize using simple scaling (NO TANH)
        signal_value = np.clip(signal_value, -0.01, 0.01)

        # confidence based on volatility-aware proxy
        confidence = 0.7 + min(abs(signal_value) * 20, 0.3)

        return signal_value, confidence

    # =================================================
    # MAIN PREDICT FUNCTION
    # =================================================
    def predict(self, df, model_keys, symbol):

        try:

            if self.models is None:
                return None

            X = self._prepare_features(df)

            if X is None or len(X) == 0:
                return None

            # =================================================
            # CASE 1: SINGLE MODEL (MOST COMMON IN YOUR SETUP)
            # =================================================
            if hasattr(self.models, "predict"):

                signal_value, confidence = self._predict_regression(
                    self.models,
                    X
                )

                return {
                    "signal": signal_value,
                    "confidence": confidence
                }

            # =================================================
            # CASE 2: ENSEMBLE MODELS (DICT OF MODELS)
            # =================================================
            elif isinstance(self.models, dict):

                signals = []
                confidences = []

                for name, model in self.models.items():

                    try:
                        sig, conf = self._predict_regression(model, X)

                        signals.append(sig)
                        confidences.append(conf)

                    except Exception as e:
                        log(f"WARNING | Model {name} failed: {e}")

                if len(signals) == 0:
                    return None

                return {
                    "signal": float(np.mean(signals)),
                    "confidence": float(np.mean(confidences))
                }

            else:
                log("ERROR | Unknown model format")
                return None

        except Exception as e:
            log(f"ERROR | Predict failed {symbol}: {e}")
            return None