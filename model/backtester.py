# backtester.py

import numpy as np
from config import FUTURE_PERIOD, SPREAD_COST, SIGNAL_THRESHOLD


def run_backtest(df, predictions):

    df = df.reset_index(drop=True)
    predictions = np.array(predictions)

    # ==============================
    # 1. Normalize signal (z-score)
    # ==============================
    pred_mean = predictions.mean()
    pred_std = predictions.std() + 1e-9
    z = (predictions - pred_mean) / pred_std

    pnl = np.zeros(len(z))
    trades = []

    N = len(z) - FUTURE_PERIOD

    for i in range(N):

        signal = z[i]

        if abs(signal) < SIGNAL_THRESHOLD:
            continue

        price_now = df["close"].iloc[i]
        price_future = df["close"].iloc[i + FUTURE_PERIOD]

        # Return-based PnL
        raw_return = (price_future - price_now) / price_now
        spread_return = SPREAD_COST / price_now

        # Position sizing (confidence scaling)
        position_size = np.clip(abs(signal) / 3, 0, 1)

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

    # Annualized Sharpe (assuming M5 bars ~ 288 per day)
    sharpe_annual = sharpe * np.sqrt(288 * 252)

    # Max Drawdown
    cumulative = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    max_drawdown = drawdown.min()

    trade_count = len(trades)
    trade_frequency = trade_count / N

    print("========== BACKTEST RESULTS ==========")
    print("Total Return:", total_return)
    print("Win Rate:", win_rate)
    print("Sharpe Ratio:", sharpe)
    print("Annualized Sharpe:", sharpe_annual)
    print("Max Drawdown:", max_drawdown)
    print("Number of Trades:", trade_count)
    print("Trade Frequency:", trade_frequency)
    print("======================================")

    return pnl