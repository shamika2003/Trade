import numpy as np
from model.config import SIGNAL_THRESHOLD

def decide_signal(pred):

    z = (pred - np.mean(pred)) / (np.std(pred) + 1e-9)

    if abs(z) < SIGNAL_THRESHOLD:
        return None

    return "BUY" if z > 0 else "SELL"