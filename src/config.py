#  MARKET DATA

# Biance.com block us users so we will defualt to binance.us for US users
KLINES_URL = "https://api.binance.us/api/v3/klines"

# The  API max per request is 1000
MAX_CANDLES_PER_REQUEST = 1000

# Short pause between page requests. Binance.US allows 6,000 weight
# per minute and a klines call costs 1, so we're nowhere near the limit.
# We still pause to be a polite API client
REQUEST_PAUSE_SECONDS = 0.2

# Timeframes the UI lets the user pick. A subset of the intervals
# Binance.US supports (1m to 1M), chosen so a few months of data
# stays a reasonable size.
SUPPORTED_TIMEFRAMES = ["15m", "1h", "4h", "1d"]

#Downladed candles are saved so we don't have to redownload them every time we run the app
CACHE_DIR = "data/cache"

#  SWING DETECTION

# A candle must have the highest high (or lowest low) within this many
# candles on each side to count as a swing point.
SWING_LOOKBACK = 2

#  TRADE SIMULATION RULES

# 0.05% room past the wick, so tiny noise doesn't knock the stop out.
STOP_BUFFER_PCT = 0.0005

# Take profit at this many times the risk. 2.0 means risk $1 to make $2.
RR_TARGET = 2.0

# Round-trip trading fee as a fraction (0.001 = 0.1%). Ignoring fees makes
# every backtest look better than reality.
FEE_PCT = 0.001

# Trend label for each trade: "up" if price is above its N-candle average.
# Lets the LLM say things like "the setup worked better in uptrends".
TREND_SMA_PERIOD = 50
