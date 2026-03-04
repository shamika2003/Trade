# config.py

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = "model/market_dataset.csv"
MODEL_PATH = "model/trading_model.pkl"

# Backtest configuration
FUTURE_PERIOD = 12
SIGNAL_THRESHOLD = 1.2   # stronger selectivity
SPREAD_COST = 0.0002


BOT_MODE = "AUTO_DEMO"   # SEMI or AUTO_DEMO

SYMBOL = "EURUSD"

SIGNAL_THRESHOLD = 1.5

MAX_OPEN_TRADES = 3

TRADE_LOT = 0.01

COOLDOWN_SECONDS = 600