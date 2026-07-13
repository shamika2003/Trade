# filename: config_core.py

from pathlib import Path


# =====================================================
# PROJECT PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent


DATA_PATH = "model/market_dataset.csv"

MODEL_PATH = "model/trading_model.pkl"



# =====================================================
# BOT MODE
# =====================================================

# True:
#   CSV replay
#   PaperExecutor
#
# False:
#   MT5 live
#   BrainExecutor

USE_OFFLINE = True



BOT_MODE = "AUTO_DEMO"



# =====================================================
# MARKET SETTINGS
# =====================================================

SYMBOLS = [

    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCNH"

]


TIMEFRAME = 5



# minimum candles needed for indicators

HISTORY_SIZE = 2000




# =====================================================
# BACKTEST SETTINGS
# =====================================================

# execution model:
#
# CANDLE:
#   signal on candle close
#   execute next candle
#
# TICK:
#   future tick simulation

BACKTEST_EXECUTION = "CANDLE"



# replay delay

BACKTEST_DELAY = 0



REPLAY_SPEED = 1




# =====================================================
# MACHINE LEARNING
# =====================================================

FUTURE_PERIOD = 12



MODEL_CONFIDENCE_THRESHOLD = 0.60



SIGNAL_THRESHOLD = 0.0005



MIN_MODEL_AGREEMENT = 0.60


MIN_TRADE_STRENGTH = 0.015



CONFIDENCE_WEIGHT = 0.70




# =====================================================
# COST MODEL
# =====================================================

SPREAD_ENABLED = True


DEFAULT_SPREAD_PIPS = 1.2



COMMISSION_PER_LOT = 7.0



SPREAD_COST = 0.0002




# dynamic spread

SPREAD_WINDOW = 50

SPREAD_MULTIPLIER = 2.5

MIN_SPREAD_FLOOR = 0.00005





# =====================================================
# CAPITAL
# =====================================================

DEFAULT_CAPITAL = 1000.0


TRADE_LOT = 0.01



MAX_OPEN_TRADES = 2


MAX_TOTAL_TRADES = 5



COOLDOWN_SECONDS = 300





# =====================================================
# RISK MANAGEMENT
# =====================================================

# Forex pips

STOP_LOSS_PIPS = 10


TAKE_PROFIT_PIPS = 20



# compatibility aliases
# (old executor code)

STOP_LOSS = STOP_LOSS_PIPS

TAKE_PROFIT = TAKE_PROFIT_PIPS





# ATR protection

USE_ATR_STOPS = True


ATR_SL_MULTIPLIER = 1.5


ATR_TP_MULTIPLIER = 3.0





# =====================================================
# MT5 SETTINGS
# =====================================================

MT5_MAGIC = 123456


DEVIATION = 20



LIVE_INTERVAL = 5





# =====================================================
# EXECUTION SAFETY
# =====================================================

MAX_RETRY_EXECUTION = 3


PRICE_VALIDATION_THRESHOLD = 0.001





# =====================================================
# LOGGING
# =====================================================

LOG_FILE = "logs/trading_bot.log"


TRADE_LOG_FILE = "logs/trades.csv"




# =====================================================
# DEBUG
# =====================================================

DEBUG = True