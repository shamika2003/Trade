import MetaTrader5 as mt5
import pandas as pd
import time


class MarketDataCollector:

    def __init__(self):
        self.connected = False

    def connect(self):
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        self.connected = True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def fetch_history(
        self,
        symbol: str,
        timeframe,
        total_candles: int = 200000,
        chunk_size: int = 5000,
        retry_delay: float = 1.5
    ) -> pd.DataFrame | None:

        if not self.connected:
            self.connect()

        all_data = []

        try:
            for start in range(0, total_candles, chunk_size):

                rates = mt5.copy_rates_from_pos(
                    symbol,
                    timeframe,
                    start,
                    chunk_size
                )

                if rates is None or len(rates) == 0:
                    print("Fetch warning:", mt5.last_error())
                    time.sleep(retry_delay)
                    continue

                df_chunk = pd.DataFrame(rates)
                all_data.append(df_chunk)

        except Exception as e:
            print("Collector error:", e)

        finally:
            self.disconnect()

        if not all_data:
            return None

        # Combine chunks
        df = pd.concat(all_data, ignore_index=True)

        # Remove duplicate candles (VERY IMPORTANT for ML training)
        df = df.drop_duplicates(subset=["time"])

        # Convert timestamp
        df["time"] = pd.to_datetime(df["time"], unit="s")

        # Sort chronologically
        df = df.sort_values("time").reset_index(drop=True)

        return df