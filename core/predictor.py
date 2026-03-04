import joblib
import numpy as np
from model.config import MODEL_PATH

class Predictor:

    def __init__(self):
        self.model = joblib.load(MODEL_PATH)

    def predict(self, feature_df, feature_list):

        pred = self.model.predict(feature_df[feature_list])
        return np.array(pred)