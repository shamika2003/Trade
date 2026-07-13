# filename: predictor.py

import numpy as np
import joblib
import os

from core.logger import log
from core.feature_engine import FeatureTransformer


# =====================================================
# PREDICTOR (SYMBOL BASED REGRESSION MODEL)
# =====================================================

class Predictor:


    def __init__(
        self,
        model_path="model/trading_model.pkl"
    ):

        self.model_path = model_path

        self.models = None

        self.feature_engine = FeatureTransformer()

        self.feature_list = (
            self.feature_engine
            .get_feature_list()
        )

        self._load_model()



    # =================================================
    # LOAD MODEL
    # =================================================

    def _load_model(self):

        try:

            if not os.path.exists(self.model_path):

                log(
                    f"ERROR | Model not found: {self.model_path}"
                )

                return


            self.models = joblib.load(
                self.model_path
            )


            log(
                "INFO | Predictor model loaded"
            )


        except Exception as e:

            log(
                f"ERROR | Model load failed: {e}"
            )

            self.models = None




    # =================================================
    # FEATURE PREPARATION
    # =================================================

    def _prepare_features(self, df):

        try:

            df = df.copy()


            missing = [
                f
                for f in self.feature_list
                if f not in df.columns
            ]


            if missing:

                log(
                    f"WARNING | Missing features: {missing}"
                )

                return None



            X = df[
                self.feature_list
            ].copy()

            if X.columns.duplicated().any():

                log(
                    f"ERROR | Duplicate columns found: {X.columns[X.columns.duplicated()]}"
                )

                return None


            # convert everything numeric
            for col in X.columns:

                X[col] = (
                    np
                    .asarray(
                        X[col],
                        dtype=np.float32
                    )
                )



            X = X.replace(
                [
                    np.inf,
                    -np.inf
                ],
                np.nan
            )


            X = X.fillna(0)



            return X



        except Exception as e:

            log(
                f"ERROR | Feature preparation failed: {e}"
            )

            return None





    # =================================================
    # MODEL PREDICTION
    # =================================================

    def _predict_model(
        self,
        model,
        X
    ):


        prediction = (
            model
            .predict(X)
        )


        value = float(
            prediction[-1]
        )


        # keep regression output stable

        value = np.clip(
            value,
            -0.01,
            0.01
        )


        confidence = (
            0.7
            +
            min(
                abs(value) * 20,
                0.3
            )
        )


        return (
            value,
            confidence
        )





    # =================================================
    # MAIN PREDICT
    # =================================================

    def predict(
        self,
        df,
        model_keys,
        symbol
    ):


        try:


            if self.models is None:

                return None




            X = self._prepare_features(
                df
            )


            if X is None or X.empty:

                return None




            # =========================================
            # SYMBOL MODEL SELECTION
            # =========================================

            if isinstance(
                self.models,
                dict
            ):


                if symbol not in self.models:

                    log(
                        f"ERROR | No model for {symbol}"
                    )

                    return None



                model = (
                    self.models[symbol]
                )



            else:

                # single model fallback

                model = self.models




            signal_value, confidence = (
                self._predict_model(
                    model,
                    X
                )
            )



            return {

                "signal": signal_value,

                "confidence": confidence

            }




        except Exception as e:


            log(
                f"ERROR | Predict failed {symbol}: {e}"
            )


            return None