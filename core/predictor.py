# filename: predictor.py

import joblib
import numpy as np
import pandas as pd
from config import MODEL_PATH, SIGNAL_THRESHOLD
from core.logger import log  # <-- custom logger

class Predictor:
    """
    Advanced live predictor supporting multi-symbol, multi-regime, and multi-horizon models.
    """

    def __init__(self, smoothing_window=5, ensemble=True):
        """
        :param smoothing_window: number of recent predictions to smooth over
        :param ensemble: if True, average short and long predictions
        """
        try:
            self.models = joblib.load(MODEL_PATH)
            if not isinstance(self.models, dict):
                raise RuntimeError("Model file must contain a dictionary of models")
        except Exception as e:
            log(f"ERROR | Failed to load models from {MODEL_PATH}: {e}")
            self.models = {}

        self.smoothing_window = smoothing_window
        self.ensemble = ensemble
        self.pred_buffer = {}  # per-symbol rolling predictions

    # -----------------------------
    # Symbol-level and regime selection
    # -----------------------------
    def _select_model(self, df, horizon='short'):
        """
        Determine which model to use based on volatility regime.
        :param df: live feature dataframe
        :param horizon: 'short' or 'long'
        :return: model key string
        """
        try:
            if 'volatility_regime' not in df.columns:
                regime = 'low'
            else:
                regime_val = df['volatility_regime'].iloc[-1]
                regime = 'high' if regime_val > 0.75 else 'low'

            model_key = f"{regime}_{horizon}"
            return model_key
        except Exception as e:
            log(f"ERROR | Error selecting model: {e}")
            return f"low_{horizon}"

    # -----------------------------
    # Prediction smoothing
    # -----------------------------
    def _smooth_prediction(self, symbol, pred):
        buf = self.pred_buffer.setdefault(symbol, [])
        buf.append(pred)
        if len(buf) > self.smoothing_window:
            buf.pop(0)
        return float(np.mean(buf))

    # -----------------------------
    # Core prediction
    # -----------------------------
    def predict(self, df, feature_list):
        """
        Predict signal for a single symbol dataframe
        :param df: pandas.DataFrame with live features
        :param feature_list: list of feature names expected by the model
        :return: numpy array with smoothed prediction
        """
        if df is None or df.empty:
            return np.array([0.0])

        df = df.copy().ffill().dropna()
        if df.empty or 'symbol' not in df.columns:
            log("WARNING | Predictor Warning: Invalid dataframe or missing symbol")
            return np.array([0.0])

        symbol = df['symbol'].iloc[-1]
        if symbol not in self.models:
            log(f"WARNING | Predictor Warning: No model found for symbol {symbol}")
            return np.array([0.0])

        X = df.reindex(columns=feature_list).fillna(0)
        if X.empty:
            return np.array([0.0])

        preds = []
        for horizon in ['short', 'long']:
            model_key = self._select_model(df, horizon)
            model = self.models[symbol].get(model_key)
            if model is None:
                continue
            try:
                pred = model.predict(X)
                if len(pred) > 0:
                    preds.append(pred[-1])
            except Exception as e:
                log(f"ERROR | Predictor Error ({symbol}-{model_key}): {e}")
                continue

        if not preds:
            return np.array([0.0])

        # Ensemble averaging or single horizon
        final_pred = float(np.mean(preds)) if self.ensemble else preds[0]

        # Clamp extreme values
        final_pred = np.clip(final_pred, -2, 2)

        # Smooth recent predictions
        smoothed_pred = self._smooth_prediction(symbol, final_pred)
        return np.array([smoothed_pred])

    # -----------------------------
    # Confidence check helper
    # -----------------------------
    def is_confident(self, pred):
        """
        Check if prediction passes the SIGNAL_THRESHOLD
        :param pred: float prediction value
        :return: bool
        """
        return abs(pred) >= SIGNAL_THRESHOLD