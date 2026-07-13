# filename: data_fetcher.py (offline mode)

import pandas as pd

from config_core import DATA_PATH
from core.logger import log

# =====================================================
# CSV DATA FEED (OFFLINE REPLAY)
# =====================================================
class CSVDataFeed:

    def __init__(self, file_path=DATA_PATH):

        self.df = pd.read_csv(file_path)

        # -----------------------------
        # TIME CLEAN
        # -----------------------------
        self.df["time"] = pd.to_datetime(
            self.df["time"]
        )

        self.df = (
            self.df
            .sort_values(
                [
                    "symbol",
                    "time"
                ]
            )
            .reset_index(drop=True)
        )

        # -----------------------------
        # CACHE SYMBOL DATA
        # -----------------------------
        self.symbol_data = {}

        for symbol in self.df["symbol"].unique():

            self.symbol_data[symbol] = (
                self.df[
                    self.df["symbol"] == symbol
                ]
                .reset_index(drop=True)
            )

        self.symbols = list(
            self.symbol_data.keys()
        )

        # -----------------------------
        # REPLAY POINTER
        # -----------------------------
        self.index_map = {
            symbol: 0
            for symbol in self.symbols
        }


        log(
            "INFO | CSV Data Feed initialized"
        )

    # =================================================
    # GET DATA WINDOW
    # =================================================
    def _get_window(
            self,
            symbol,
            window=2000
    ):

        if symbol not in self.symbol_data:
            log(
                f"ERROR | Unknown symbol {symbol}"
            )
            return None


        data = self.symbol_data[symbol]

        idx = self.index_map[symbol]


        if idx + window >= len(data):
            return None


        chunk = (
            data
            .iloc[
                idx:
                idx + window
            ]
            .copy()
        )


        # move forward like live candle update
        self.index_map[symbol] += 1


        return chunk

    # =================================================
    # MULTI TIMEFRAME PIPELINE
    # SAME OUTPUT AS ONLINE MODE
    # =================================================
    def get_mtf_data(self, symbol):


        # ---------------------------------
        # OFFLINE SIMULATION
        #
        # CSV should contain M5 data
        #
        # H1 is generated from M5
        # exactly like market aggregation
        # ---------------------------------

        df_m5 = self._get_window(
            symbol,
            window=2000
        )


        if df_m5 is None:
            return None, None



        # -----------------------------
        # CREATE H1 FROM M5
        # -----------------------------

        df_h1 = (
            df_m5
            .set_index("time")
            .resample("1h")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "tick_volume": "sum",
                    "spread": "mean",
                    "real_volume": "sum"
                }
            )
            .dropna()
            .reset_index()
        )


        df_h1["symbol"] = symbol



        if len(df_h1) < 100:
            return None, None



        return df_m5, df_h1