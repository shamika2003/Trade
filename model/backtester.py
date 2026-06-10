# filename: backtester.py

import numpy as np
from config import FUTURE_PERIOD, SPREAD_COST, SIGNAL_THRESHOLD


def run_backtest(df, predictions):

    df = df.reset_index(drop=True)
    predictions = np.array(predictions)

    if len(df) != len(predictions):
        raise RuntimeError("Backtester: prediction length mismatch")

    predictions = np.nan_to_num(predictions)

    pred_mean = predictions.mean()
    pred_std = predictions.std() + 1e-9

    z_signal = (predictions - pred_mean) / pred_std

    pnl = []
    trades = []

    N = len(z_signal) - FUTURE_PERIOD - 1

    for i in range(max(N, 0)):

        signal = z_signal[i]

        if abs(signal) < SIGNAL_THRESHOLD:
            continue

        entry_price = df["open"].iloc[i + 1]
        exit_price = df["close"].iloc[i + 1 + FUTURE_PERIOD]

        raw_return = (exit_price - entry_price) / entry_price

        spread_cost = SPREAD_COST

        position_size = np.clip(abs(signal) / 3.0, 0, 1)

        if signal > 0:
            trade_pnl = position_size * (raw_return - spread_cost)
        else:
            trade_pnl = position_size * (-raw_return - spread_cost)

        pnl.append(trade_pnl)
        trades.append(trade_pnl)

    pnl = np.array(pnl)
    trades = np.array(trades)

    if len(pnl) == 0:
        print("No trades executed.")
        return {}

    total_return = pnl.sum()
    win_rate = (trades > 0).mean()

    sharpe = 0
    if trades.std() > 0:
        sharpe = trades.mean() / (trades.std() + 1e-9)

    sharpe_annual = sharpe * np.sqrt(288 * 252)

    cumulative = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max

    max_drawdown = drawdown.min()

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