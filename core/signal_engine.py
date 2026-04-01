# filename: signal_engine.py

from config import SIGNAL_THRESHOLD
from core.logger import log  # <-- custom logger


def decide_signal(pred: float, clamp_range: float = 2.0) -> str | None:
    """
    Decide trade signal based on prediction value.

    :param pred: float prediction from model
    :param clamp_range: maximum absolute value to clamp predictions
    :return: "BUY", "SELL" or None if below threshold
    """
    # Clamp extreme predictions for safety
    pred = max(min(pred, clamp_range), -clamp_range)

    if abs(pred) < SIGNAL_THRESHOLD:
        log(f"INFO | Signal ignored: {pred:.5f} below threshold {SIGNAL_THRESHOLD:.2f}")
        return None

    signal = "BUY" if pred > 0 else "SELL"
    log(f"INFO | Signal decided: {pred:.5f} -> {signal}")
    return signal