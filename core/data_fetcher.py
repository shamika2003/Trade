import MetaTrader5 as mt5
import pandas as pd
from config import SYMBOL


def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")


def get_mtf_data():

    # Get M5 data
    rates_m5 = mt5.copy_rates_from_pos(
        SYMBOL,
        mt5.TIMEFRAME_M5,
        0,
        500
    )

    # Get H1 data
    rates_h1 = mt5.copy_rates_from_pos(
        SYMBOL,
        mt5.TIMEFRAME_H1,
        0,
        500
    )

    df_m5 = pd.DataFrame(rates_m5)
    df_h1 = pd.DataFrame(rates_h1)

    df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')

    return df_m5, df_h1