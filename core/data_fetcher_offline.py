# filename: data_fetcher.py (offline mode)

import pandas as pd
from config_core import DATA_PATH
from core.logger import log


class CSVDataFeed:

    def __init__(self, file_path=DATA_PATH):
        self.df = pd.read_csv(file_path)

        self.df["time"] = pd.to_datetime(self.df["time"])
        self.df = self.df.sort_values(["symbol", "time"]).reset_index(drop=True)

        self.symbols = self.df["symbol"].unique()

        self.index_map = {s: 0 for s in self.symbols}

        log("INFO | CSV Data Feed initialized")

    def get_next(self, symbol, window=500):

        data = self.df[self.df["symbol"] == symbol]

        idx = self.index_map[symbol]

        if idx + window >= len(data):
            return None

        chunk = data.iloc[idx: idx + window].copy()

        self.index_map[symbol] += 1   # move forward 1 step (LIVE simulation)

        return chunk