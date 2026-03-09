# config.py

from pathlib import Path

# ================================
# Project Paths
# ================================

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = str(BASE_DIR / "model/market_dataset.csv")
MODEL_PATH = str(BASE_DIR / "model/trading_model.pkl")

# ================================
# Trading Brain Settings
# ================================

FUTURE_PERIOD = 12

# Signal selectivity threshold
SIGNAL_THRESHOLD = 0.025

# Spread noise protection
SPREAD_COST = 0.0002

# Bot Mode
BOT_MODE = "AUTO_DEMO"   # AUTO_DEMO or SEMI

# Market Settings
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCNH"]
TIMEFRAME = 5   # M5 timeframe

# Execution Risk Control
TRADE_LOT = 0.01
COOLDOWN_SECONDS = 300
MAX_OPEN_TRADES = 2
MAX_TOTAL_TRADES = 5

# Safety caps (added)
MAX_RETRY_EXECUTION = 3
PRICE_VALIDATION_THRESHOLD = 0