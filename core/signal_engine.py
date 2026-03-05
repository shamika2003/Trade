# filename: signal_engine.py

from config import SIGNAL_THRESHOLD


def decide_signal(pred):

    # Safety clamp
    pred = max(min(pred, 2), -2)

    if abs(pred) < SIGNAL_THRESHOLD:
        return None

    return "BUY" if pred > 0 else "SELL"