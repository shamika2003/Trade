import joblib
import numpy as np
from config import MODEL_PATH

class Predictor:

    def __init__(self):
        self.model = joblib.load(MODEL_PATH)

    def predict(self, df, feature_list):
        pred = self.model.predict(df[feature_list])
        return np.array(pred)