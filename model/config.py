# config.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = "model/market_dataset.csv"
MODEL_PATH = "model/trading_model.pkl"

FUTURE_PERIOD = 12

# Strong selective trading
SIGNAL_THRESHOLD = 1.8

SPREAD_COST = 0.0002

BOT_MODE = "AUTO_DEMO"

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]

TIMEFRAME = 5

TRADE_LOT = 0.01
COOLDOWN_SECONDS = 300

MAX_OPEN_TRADES = 1