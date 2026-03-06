# filename: backtester.py

import numpy as np
from config import FUTURE_PERIOD, SPREAD_COST, SIGNAL_THRESHOLD


def run_backtest(df, predictions):

    df = df.reset_index(drop=True)
    predictions = np.array(predictions)

    if len(df) != len(predictions):
        raise RuntimeError("Backtester: prediction length mismatch")

    # ==============================
    # Signal Normalization (Local Z-score)
    # ==============================

    pred_std = predictions.std() + 1e-9
    pred_mean = predictions.mean()

    z_signal = (predictions - pred_mean) / pred_std

    pnl = np.zeros(len(z_signal))
    trades = []

    N = len(z_signal) - FUTURE_PERIOD

    for i in range(N):

        signal = z_signal[i]

        if abs(signal) < SIGNAL_THRESHOLD:
            continue

        price_now = df["close"].iloc[i]
        price_future = df["close"].iloc[i + FUTURE_PERIOD]

        raw_return = (price_future - price_now) / price_now

        spread_return = SPREAD_COST / price_now

        # Confidence scaled position sizing
        position_size = np.clip(abs(signal) / 3.0, 0, 1)

        if signal > 0:
            trade_pnl = position_size * (raw_return - spread_return)
        else:
            trade_pnl = position_size * (-raw_return - spread_return)

        pnl[i] = trade_pnl
        trades.append(trade_pnl)

    pnl = np.array(pnl)
    trades = np.array(trades)

    # ==============================
    # Metrics
    # ==============================

    total_return = pnl.sum()

    win_rate = (trades > 0).mean() if len(trades) > 0 else 0

    sharpe = 0
    if pnl.std() > 0:
        sharpe = pnl.mean() / (pnl.std() + 1e-9)

    # M5 bars assumption
    sharpe_annual = sharpe * np.sqrt(288 * 252)

    cumulative = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    max_drawdown = drawdown.min() if len(drawdown) > 0 else 0

    trade_count = len(trades)
    trade_frequency = trade_count / max(N, 1)

    print("========== BACKTEST RESULTS ==========")
    print(f"Total Return      : {total_return:.6f}")
    print(f"Win Rate          : {win_rate:.4f}")
    print(f"Sharpe Ratio      : {sharpe:.6f}")
    print(f"Annual Sharpe     : {sharpe_annual:.6f}")
    print(f"Max Drawdown      : {max_drawdown:.6f}")
    print(f"Number of Trades  : {trade_count}")
    print(f"Trade Frequency   : {trade_frequency:.6f}")
    print("======================================")

    return {
        "pnl": pnl,
        "total_return": total_return,
        "win_rate": win_rate,
        "sharpe": sharpe,
        "annual_sharpe": sharpe_annual,
        "max_drawdown": max_drawdown,
        "trade_count": trade_count,
        "trade_frequency": trade_frequency
    }