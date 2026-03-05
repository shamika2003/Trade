# filename: data_fetcher.py

import MetaTrader5 as mt5
import pandas as pd
import time

from config import SYMBOL


# =====================================================
# MT5 Initialization Layer
# =====================================================

def initialize_mt5():

    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")

    terminal = mt5.terminal_info()

    print("MT5 Terminal Connected:", terminal is not None)

    symbol_info = mt5.symbol_info(SYMBOL)

    if symbol_info is None:
        raise RuntimeError(f"Symbol not found: {SYMBOL}")

    if not symbol_info.visible:
        mt5.symbol_select(SYMBOL, True)

    return True


# =====================================================
# Safe Rate Fetcher
# =====================================================

def _fetch_rates(timeframe, n_bars, retry=3):

    for _ in range(retry):

        try:

            rates = mt5.copy_rates_from_pos(
                SYMBOL,
                timeframe,
                0,
                n_bars
            )

            if rates is not None:

                df = pd.DataFrame(rates)

                if not df.empty:
                    df["time"] = pd.to_datetime(df["time"], unit="s")
                    return df

        except Exception as e:
            print("Market data fetch error:", e)

        print("Retry fetching market data...")
        time.sleep(1)

    return None


# =====================================================
# Multi-Timeframe Data Pipeline
# =====================================================

def get_mtf_data():

    df_m5 = _fetch_rates(
        mt5.TIMEFRAME_M5,
        2000
    )

    df_h1 = _fetch_rates(
        mt5.TIMEFRAME_H1,
        2000
    )

    if df_m5 is None or df_h1 is None:
        return None, None

    if df_m5.empty or df_h1.empty:
        return None, None

    return (
        df_m5.sort_values("time").reset_index(drop=True),
        df_h1.sort_values("time").reset_index(drop=True)
    )