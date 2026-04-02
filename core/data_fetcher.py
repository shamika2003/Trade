# filename: data_fetcher.py

import MetaTrader5 as mt5
import pandas as pd
import time

from config import SYMBOLS


# =====================================================
# MT5 Initialization Layer
# =====================================================

def initialize_mt5():

    if not mt5.initialize():  # type: ignore
        raise RuntimeError("MT5 initialization failed")

    terminal = mt5.terminal_info()  # type: ignore

    if terminal is None:
        raise RuntimeError("MT5 terminal not reachable")

    print("MT5 Terminal Connected:", True)

    # Enable configured symbols
    for symbol in SYMBOLS:

        symbol_info = mt5.symbol_info(symbol)  # type: ignore

        if symbol_info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")

        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)  # type: ignore

        print(f"Symbol enabled: {symbol}")

    return True


# =====================================================
# Safe Rate Fetcher
# =====================================================

def _fetch_rates(symbol, timeframe, n_bars, retry=3):

    for attempt in range(retry):

        try:

            rates = mt5.copy_rates_from_pos(  # type: ignore
                symbol,
                timeframe,
                0,
                n_bars
            )

            if rates is not None and len(rates) > 0:

                df = pd.DataFrame(rates)

                df["time"] = pd.to_datetime(df["time"], unit="s")
                df["symbol"] = symbol

                return df

        except Exception as e:
            print(f"Market data fetch error ({symbol}) attempt {attempt+1}:", e)

        time.sleep(1)

    print(f"Failed fetching market data: {symbol}")
    return None


# =====================================================
# Multi-Timeframe Data Pipeline
# =====================================================

def get_mtf_data(symbol):

    df_m5 = _fetch_rates(
        symbol,
        mt5.TIMEFRAME_M5,
        2000
    )

    df_h1 = _fetch_rates(
        symbol,
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