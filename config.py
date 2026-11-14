# Configuration for Delta Exchange Automated 24/7 Safe Micro-Crypto Bot

MCP_URL = "https://mcp.viasocket.com/mcp/6af360c8e54464112ba88f7e-85776"
DELTA_API_BASE = "https://api.india.delta.exchange"

# Safe Micro-Contract Cryptos:
# Only cryptos where 1 contract notional value is tiny ($0.01 to $1.00 USD)
# This eliminates over-leveraging risk and protects small accounts ($0.30 - $2.00)!
WATCHLIST = [
    "XRPUSD",    # 1 Contract = ~$1.01 USD (Margin: ~$0.02)
    "SUIUSD",    # 1 Contract = ~$0.78 USD (Margin: ~$0.015)
    "ADAUSD",    # 1 Contract = ~$0.17 USD (Margin: ~$0.003)
    "XLMUSD",    # 1 Contract = ~$0.14 USD (Margin: ~$0.003)
    "WIFUSD",    # 1 Contract = ~$0.15 USD (Margin: ~$0.003)
    "HBARUSD",   # 1 Contract = ~$0.06 USD (Margin: ~$0.001)
    "OPUSD",     # 1 Contract = ~$0.01 USD (Margin: ~$0.0002)
    "TRUMPUSD",  # 1 Contract = ~$0.11 USD (Margin: ~$0.002)
    "BTCUSD"     # 1 Contract = ~$69 USD (Tested only when balance allows)
]

ORDER_SIZE = 1           # 1 contract per trade (strictly micro-sized)
MAX_ACTIVE_TRADES = 1    # Max 1 active trade at a time

# Strategy Settings
FAST_EMA = 9             # Fast EMA period (5-minute candle)
SLOW_EMA = 15            # Slow EMA period (5-minute candle)
TIMEFRAME_MINUTES = 5    # 5-minute candles for entry/exit

# Higher Timeframe Trend Filter (Crucial Safety Feature)
USE_TREND_FILTER = True      # Enable 15-Minute 50-EMA Trend Filter
TREND_TIMEFRAME_MIN = 15     # 15-minute timeframe
TREND_EMA_PERIOD = 50        # Only BUY if 15m price is ABOVE 50 EMA (No buying in downtrends)

# RSI Confirmation
USE_RSI_FILTER = True
RSI_MAX_BUY = 65.0       # Don't buy if RSI > 65 (prevents buying at peak)

# Risk Management
TAKE_PROFIT_PCT = 1.2    # 1.2% quick target profit
STOP_LOSS_PCT = 1.0      # 1.0% strict stop loss protection

# Bot Settings
CHECK_INTERVAL_SEC = 30  # Scan every 30 seconds
DRY_RUN = False          # Set to True for simulated paper trading
