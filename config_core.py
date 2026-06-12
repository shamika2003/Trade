# filename: config.py

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

# Spread noise protection
SPREAD_COST = 0.0002

# Default Capital
DEFAULT_CAPITAL = 1000.0  # USD

# Bot Mode
BOT_MODE = "AUTO_DEMO"   # AUTO_DEMO or SEMI

# Market Settings
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCNH"]
TIMEFRAME = 5   # M5 timeframe

# ================================
# Execution Risk Control
# ================================
TRADE_LOT = 0.01
COOLDOWN_SECONDS = 300

MAX_OPEN_TRADES = 2
MAX_TOTAL_TRADES = 5

# IMPORTANT: Always POSITIVE values
STOP_LOSS = 1.0        # max loss per trade (USD)
TAKE_PROFIT = 1.0      # target profit per trade (USD)

# ================================
# Safety / Miscellaneous
# ================================
MAX_RETRY_EXECUTION = 3
PRICE_VALIDATION_THRESHOLD = 0.001

# ================================
# Dynamic Spread Control
# ================================
SPREAD_WINDOW = 50              # number of ticks to track
SPREAD_MULTIPLIER = 2.5         # allowed spike factor
MIN_SPREAD_FLOOR = 0.00005      # absolute minimum (avoid zero issues)

# ================================
# ML Confidence Control
# ================================

MIN_MODEL_AGREEMENT = 0.6     # short vs long agreement
MIN_TRADE_STRENGTH = 0.015     # replaces weak SIGNAL_THRESHOLD usage
CONFIDENCE_WEIGHT = 0.7       # how much agreement matters