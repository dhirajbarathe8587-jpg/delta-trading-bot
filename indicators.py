# Technical Indicators implemented in pure Python (no external dependencies needed)

def _extract_closes(data):
    """Helper to extract close prices whether input is list of floats or list of candle dicts"""
    if not data:
        return []
    if isinstance(data[0], dict):
        return [float(x.get('close', 0.0)) for x in data if 'close' in x]
    return [float(x) for x in data]


def calculate_ema_series(data, period):
    """
    Calculate full Exponential Moving Average (EMA) series matching input length.
    Returns list of same length as data, with None for indices before period.
    """
    prices = _extract_closes(data)
    if not prices or len(prices) < period:
        return [None] * len(prices)

    result = [None] * (period - 1)
    sma = sum(prices[:period]) / period
    result.append(round(sma, 4))

    multiplier = 2.0 / (period + 1)
    current_ema = sma
    for price in prices[period:]:
        current_ema = (price - current_ema) * multiplier + current_ema
        result.append(round(current_ema, 4))

    return result


def check_ema_crossover(data, fast_period=9, slow_period=15):
    """
    Check for EMA Crossover on the latest 2 closed candles.
    Returns:
        signal: 'BULLISH_CROSS', 'BEARISH_CROSS', 'BULLISH', 'BEARISH'
        curr_fast: latest fast EMA
        curr_slow: latest slow EMA
    """
    prices = _extract_closes(data)
    if len(prices) < slow_period + 2:
        return None, None, None

    fast_series = calculate_ema_series(prices, fast_period)
    slow_series = calculate_ema_series(prices, slow_period)

    curr_fast = fast_series[-1]
    curr_slow = slow_series[-1]
    prev_fast = fast_series[-2]
    prev_slow = slow_series[-2]

    if None in (curr_fast, curr_slow, prev_fast, prev_slow):
        return None, curr_fast, curr_slow

    signal = None
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        signal = "BULLISH_CROSS"  # Fresh Buy Crossover
    elif prev_fast >= prev_slow and curr_fast < curr_slow:
        signal = "BEARISH_CROSS"  # Fresh Sell Crossover
    elif curr_fast > curr_slow:
        signal = "BULLISH"
    else:
        signal = "BEARISH"

    return signal, curr_fast, curr_slow


def check_higher_timeframe_trend(candles_15m, period=50):
    """
    Higher Timeframe (15-Minute) 50 EMA Trend Filter.
    - Returns True if price is ABOVE 50 EMA (Safe Bullish Market to Buy)
    - Returns False if price is BELOW 50 EMA (Downtrend / Bearish, Prevents buying traps)
    """
    prices = _extract_closes(candles_15m)
    if not prices or len(prices) < period:
        return True, 0.0

    ema_series = calculate_ema_series(prices, period)
    ema50 = ema_series[-1]
    last_price = prices[-1]

    if ema50 is None:
        return True, 0.0

    is_bullish = last_price >= ema50
    return is_bullish, ema50


def calculate_rsi(data, period=14):
    """Calculate Relative Strength Index (RSI)"""
    prices = _extract_closes(data)
    if len(prices) < period + 1:
        return None

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)
