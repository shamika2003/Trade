# filename: demo_bot.py

import time
import numpy as np
import MetaTrader5 as mt5
import signal
import sys

from config import (
    COOLDOWN_SECONDS,
    BOT_MODE,
    SYMBOLS,
    SIGNAL_THRESHOLD,
    DEFAULT_CAPITAL,
    TRADE_LOT,
    STOP_LOSS,
    TAKE_PROFIT,
    MAX_OPEN_TRADES,
    MAX_TOTAL_TRADES
)
from core.data_fetcher import initialize_mt5, get_mtf_data
from core.predictor import Predictor
from core.executor import BrainExecutor
from core.feature_engine_live import FeatureTransformerLive
from core.trade_manager import TradeManager
from core.logger import log

# ======================
# Prediction Memory
# ======================
prediction_buffers = {}

def smooth_prediction(symbol, pred, window=5):
    buf = prediction_buffers.setdefault(symbol, [])
    buf.append(pred)
    if len(buf) > window:
        buf.pop(0)
    return float(np.mean(buf))

# ======================
# Capital input
# ======================
def ask_capital():
    try:
        capital = float(input("Enter Trading Capital (USD): "))
        if capital > 0:
            return capital
    except Exception:
        pass
    log(f"WARNING | Invalid capital input. Using default {DEFAULT_CAPITAL} USD")
    return DEFAULT_CAPITAL

# ======================
# Signal-safe shutdown
# ======================
running = True
def stop_bot(sig, frame):
    global running
    running = False
    log("INFO | Bot received shutdown signal. Exiting gracefully...")
signal.signal(signal.SIGINT, stop_bot)
signal.signal(signal.SIGTERM, stop_bot)

# ======================
# Risk protection
# ======================
def can_open_trade(symbol):
    if not mt5.terminal_info():
        log("WARNING | MT5 terminal disconnected")
        return False

    positions_symbol = mt5.positions_get(symbol=symbol) or []
    if len(positions_symbol) >= MAX_OPEN_TRADES:
        return False

    positions_all = mt5.positions_get() or []
    if len(positions_all) >= MAX_TOTAL_TRADES:
        log("WARNING | Trade blocked: portfolio trade limit reached")
        return False

    return True

# ======================
# Main bot loop
# ======================
def main():
    initialize_mt5()
    capital = ask_capital()

    predictor = Predictor()
    transformer = FeatureTransformerLive()
    executor = BrainExecutor(capital=capital)  # <- pass capital now

    trade_managers = {s: TradeManager() for s in SYMBOLS}
    active_symbols = set()
    last_trade_times = {s: 0 for s in SYMBOLS}

    log("INFO | Autonomous Multi-Symbol Brain Bot Started...")

    while running:
        loop_start = time.time()
        for symbol in SYMBOLS:
            try:
                if not mt5.symbol_select(symbol, True):
                    log(f"WARNING | {symbol} not enabled in MT5")
                    continue

                if not mt5.terminal_info():
                    log("WARNING | MT5 disconnected. Waiting to reconnect...")
                    time.sleep(5)
                    continue

                df_m5, df_h1 = get_mtf_data(symbol)
                if df_m5 is None or df_h1 is None:
                    continue

                df = transformer.build_multi_timeframe_features(df_m5, df_h1)
                if df is None or df.empty:
                    continue

                df["symbol"] = symbol
                feature_list = transformer.get_feature_list()
                raw_pred_arr = predictor.predict(df, feature_list)
                if raw_pred_arr is None or len(raw_pred_arr) == 0:
                    continue

                raw_pred = raw_pred_arr[-1]
                pred = smooth_prediction(symbol, raw_pred)

                if abs(pred) < SIGNAL_THRESHOLD:
                    log(f"INFO | {symbol} confidence: {pred:.5f}")
                    continue

                signal_type = "BUY" if pred > 0 else "SELL"
                log(f"INFO | {symbol} Prediction: {pred:.5f} | Signal: {signal_type}")

                now = time.time()
                positions = mt5.positions_get(symbol=symbol) or []
                trade_manager = trade_managers[symbol]

                # ENTRY
                if not positions:
                    if symbol in active_symbols:
                        continue
                    if now - last_trade_times[symbol] > COOLDOWN_SECONDS and BOT_MODE.startswith("AUTO"):
                        if can_open_trade(symbol):
                            if executor.open_trade(symbol, signal_type, lot=TRADE_LOT, tp=TAKE_PROFIT, sl=STOP_LOSS):
                                trade_manager.reset()
                                active_symbols.add(symbol)
                                last_trade_times[symbol] = now

                # EXIT
                else:
                    for pos in positions:
                        profit = float(pos.profit)
                        trade_manager.update(profit)
                        close, reason = trade_manager.should_close(profit)

                        if profit >= TAKE_PROFIT or profit <= -STOP_LOSS:
                            close = True
                            reason = "TP/SL reached"

                        if close:
                            log(f"INFO | {symbol} Closing trade: {reason}")
                            if executor.close_position(pos):
                                trade_manager.reset()
                                active_symbols.discard(symbol)
                                last_trade_times[symbol] = now

            except Exception as e:
                log(f"ERROR | Error in symbol {symbol} loop: {e}")
                time.sleep(1)

        elapsed = time.time() - loop_start
        time.sleep(max(1, 5 - elapsed))

    log("INFO | Bot stopped gracefully.")

if __name__ == "__main__":
    main()