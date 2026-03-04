import MetaTrader5 as mt5
import pandas as pd

def get_latest_features(symbol, timeframe, n=200):

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)

    df = pd.DataFrame(rates)

    df.rename(columns={"tick_volume": "volume"}, inplace=True)

    return df