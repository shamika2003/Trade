# filename: data_collector.py

import MetaTrader5 as mt5
import pandas as pd
import time


class MarketDataCollector:

    def __init__(self):
        self.connected = False

    def connect(self):

        if self.connected:
            return

        print("\n" + "═" * 80)
        print("📡 MARKET DATA ACQUISITION SERVICE")
        print("═" * 80)
        print("🔄 Establishing MetaTrader 5 connection...")

        if not mt5.initialize(): # type: ignore
            raise RuntimeError(
                f"❌ MT5 initialize failed: {mt5.last_error()}" # type: ignore
            )

        self.connected = True

        print("✔ Connection established")
        print("═" * 80)

    def disconnect(self):

        if self.connected:

            print("\n🔌 Closing MetaTrader 5 connection...")

            mt5.shutdown() # type: ignore

            self.connected = False

            print("✔ Connection closed")

    def fetch_history(
        self,
        symbol: str,
        timeframe,
        total_candles: int = 200000,
        chunk_size: int = 5000,
        retry_delay: float = 1.5
    ) -> pd.DataFrame | None:

        self.connect()

        print("\n" + "─" * 80)
        print(f"📈 DATA REQUEST : {symbol}")
        print(f"📊 Target Candles : {total_candles:,}")
        print(f"📦 Chunk Size     : {chunk_size:,}")
        print("─" * 80)

        all_data = []

        try:

            for start in range(0, total_candles, chunk_size):

                end = min(start + chunk_size, total_candles)

                print(
                    f"📥 Fetching candles "
                    f"{start:,} → {end:,}"
                )

                rates = mt5.copy_rates_from_pos( # type: ignore
                    symbol,
                    timeframe,
                    start,
                    chunk_size
                )

                if rates is None or len(rates) == 0:

                    print(
                        f"⚠️ Fetch warning | "
                        f"{symbol} | {mt5.last_error()}" # type: ignore
                    )

                    time.sleep(retry_delay)
                    continue

                df_chunk = pd.DataFrame(rates)
                df_chunk["symbol"] = symbol

                all_data.append(df_chunk)

                print(
                    f"✔ Chunk received "
                    f"({len(df_chunk):,} candles)"
                )

        except Exception as e:

            print(
                f"❌ Collector failure | "
                f"{symbol} | {e}"
            )

        if not all_data:

            print(
                f"⚠️ No usable data acquired "
                f"for {symbol}"
            )

            return None

        print("\n🧩 Combining data chunks...")

        df = pd.concat(all_data, ignore_index=True)

        print("🧹 Removing duplicate candles...")

        df = df.drop_duplicates(subset=["time"])

        print("🕒 Converting timestamps...")

        df["time"] = pd.to_datetime(df["time"], unit="s")

        print("📊 Sorting market data...")

        df = df.sort_values("time").reset_index(drop=True)

        print("─" * 80)
        print(f"✅ DATA ACQUISITION COMPLETE | {symbol}")
        print(f"📈 Total Candles : {len(df):,}")

        try:
            print(
                f"🕒 Date Range    : "
                f"{df['time'].min()} → {df['time'].max()}"
            )
        except Exception:
            pass

        print("─" * 80)

        return df