# filename: predictor.py

import joblib
import numpy as np
import pandas as pd
from config import MODEL_PATH, SIGNAL_THRESHOLD

class Predictor:
    def __init__(self, smoothing_window=5, ensemble=True):
        """
        Advanced live predictor supporting multi-symbol, multi-regime, and multi-horizon models.
        :param smoothing_window: number of recent predictions to smooth over
        :param ensemble: if True, average short and long predictions
        """
        self.models = joblib.load(MODEL_PATH)
        if not isinstance(self.models, dict):
            raise RuntimeError("Model file must contain a dictionary of models")

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
        """
        if 'volatility_regime' not in df.columns:
            regime = 'low'
        else:
            regime_val = df['volatility_regime'].iloc[-1]
            regime = 'high' if regime_val > 0.75 else 'low'

        model_key = f"{regime}_{horizon}"
        return model_key

    # -----------------------------
    # Prediction smoothing
    # -----------------------------
    def _smooth_prediction(self, symbol, pred):
        if symbol not in self.pred_buffer:
            self.pred_buffer[symbol] = []
        buf = self.pred_buffer[symbol]
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
        :return: float prediction value
        """
        if df is None or df.empty:
            return np.array([0])

        df = df.copy().ffill().dropna()
        if df.empty or 'symbol' not in df.columns:
            print("Predictor Warning: Invalid dataframe or missing symbol")
            return np.array([0])

        symbol = df['symbol'].iloc[-1]

        if symbol not in self.models:
            print(f"Predictor Warning: No model found for symbol {symbol}")
            return np.array([0])

        X = df.reindex(columns=feature_list).fillna(0)
        if X.empty:
            return np.array([0])

        preds = []
        for horizon in ['short', 'long']:
            model_key = self._select_model(df, horizon)
            if model_key not in self.models[symbol]:
                continue
            model = self.models[symbol][model_key]
            try:
                pred = model.predict(X)
                if len(pred) > 0:
                    preds.append(pred[-1])
            except Exception as e:
                print(f"Predictor Error ({symbol}-{model_key}):", e)
                continue

        if not preds:
            return np.array([0])

        # Optional ensemble averaging
        final_pred = float(np.mean(preds)) if self.ensemble else preds[0]

        # Clamp extreme values for safety
        final_pred = np.clip(final_pred, -2, 2)

        # Smooth over recent predictions
        smoothed_pred = self._smooth_prediction(symbol, final_pred)

        return np.array([smoothed_pred])

    # -----------------------------
    # Confidence check helper
    # -----------------------------
    def is_confident(self, pred):
        """
        Check if prediction passes the SIGNAL_THRESHOLD
        """
        return abs(pred) >= SIGNAL_THRESHOLD