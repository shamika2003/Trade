# filename: config.py

from pathlib import Path

# ================================
# Project Paths
# ================================
BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = str(BASE_DIR / "model/market_dataset.csv")
MODEL_PATH = str(BASE_DIR / "model/trading_model.pkl")


# ================================
# Market Settings
# ================================
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDCNH"]

TIMEFRAME = 5  # MT5 M5 timeframe
FUTURE_PERIOD = 12


# ================================
# Signal Settings
# ================================
SIGNAL_THRESHOLD = 0.02

# spread filter
SPREAD_COST = 0.0002
MAX_SPREAD_ALLOWED = 0.0005


# ================================
# Capital Settings
# ================================
DEFAULT_CAPITAL = 1000.0

# % risk per trade
RISK_PER_TRADE = 0.01   # 1%

# lot sizing
BASE_LOT = 0.01
LOT_STEP = 0.01


# ================================
# Trade Management
# ================================
COOLDOWN_SECONDS = 300

MAX_OPEN_TRADES = 2
MAX_TOTAL_TRADES = 5


# ================================
# Stop Loss / Take Profit
# ================================
STOP_LOSS = 20
TAKE_PROFIT = 40

TRAILING_START = 15
TRAILING_STEP = 5


# ================================
# Execution Safety
# ================================
MAX_RETRY_EXECUTION = 3
PRICE_VALIDATION_THRESHOLD = 0.0005


# ================================
# Bot Mode
# ================================
BOT_MODE = "AUTO_DEMO"   # AUTO_DEMO | SEMI


# ================================
# Logging
# ================================
LOG_LEVEL = "INFO"
LOG_FILE = "bot_log.txt"