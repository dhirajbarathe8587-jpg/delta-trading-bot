import urllib.request
import json
import time
import uuid
import config

HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream',
    'User-Agent': 'curl/8.4.0'
}

def call_mcp_tool(action_name, instructions):
    """Call Delta Exchange action via Viasocket MCP Endpoint"""
    if not config.MCP_URL:
        raise RuntimeError("MCP_URL is not configured")

    thread_id = str(uuid.uuid4())[:8]
    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time()),
        "method": "tools/call",
        "params": {
            "name": "Delta_Exchange",
            "arguments": {
                "thread_id": f"bot_{thread_id}",
                "action_name": action_name,
                "instructions": instructions
            }
        }
    }
    
    req = urllib.request.Request(
        config.MCP_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=HEADERS
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode('utf-8')
        for line in content.split('\n'):
            if line.startswith('data: '):
                event_data = json.loads(line[6:])
                text_content = event_data['result']['content'][0]['text']
                return json.loads(text_content)
    return None


def _decode_mcp_value(value, context):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"{context} returned text instead of JSON") from e
    return value


def _mcp_records(response, context, record_fields):
    value = _decode_mcp_value(response, context)
    if isinstance(value, dict):
        if value.get('success') is False:
            raise ValueError(f"{context} action reported failure")
        if 'data' in value:
            value = value['data']
        elif 'result' in value and not any(field in value for field in record_fields):
            value = value['result']

    value = _decode_mcp_value(value, context)
    if isinstance(value, dict):
        if any(field in value for field in record_fields):
            return [value]
        for key in ('data', 'result', 'items', 'balances', 'positions'):
            if key in value:
                return _mcp_records(value[key], context, record_fields)
        raise ValueError(f"{context} response has an unexpected object shape")

    if not isinstance(value, list):
        raise ValueError(f"{context} response must contain a list of records")

    records = []
    for item in value:
        item = _decode_mcp_value(item, context)
        if not isinstance(item, dict):
            raise ValueError(f"{context} response contains a non-object record")
        records.append(item)
    return records


def get_all_tickers():
    """Fetch all live tickers in one API call for fast scanning"""
    url = f"{config.DELTA_API_BASE}/v2/tickers"
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.4.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = {}
            for t in data.get('result', []):
                sym = t.get('symbol')
                if sym:
                    result[sym] = {
                        'symbol': sym,
                        'mark_price': float(t.get('mark_price') or 0),
                        'close': float(t.get('close') or 0),
                        'high': float(t.get('high') or 0),
                        'low': float(t.get('low') or 0),
                        'volume': float(t.get('volume') or 0)
                    }
            return result
    except Exception:
        return {}


def get_live_ticker(symbol=None):
    """Fetch live ticker and mark price directly from Delta India API"""
    if symbol is None:
        symbol = config.SYMBOL
    url = f"{config.DELTA_API_BASE}/v2/tickers"
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.4.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for t in data.get('result', []):
                if t.get('symbol') == symbol:
                    return {
                        'symbol': symbol,
                        'mark_price': float(t.get('mark_price') or 0),
                        'close': float(t.get('close') or 0),
                        'high': float(t.get('high') or 0),
                        'low': float(t.get('low') or 0),
                        'volume': float(t.get('volume') or 0)
                    }
    except Exception:
        pass
    return None


def get_candles(symbol=None, resolution=None, count=50):
    """
    Fetch recent historical OHLCV candles from Delta Exchange API.
    Returns: list of dicts [{'time', 'open', 'high', 'low', 'close', 'volume'}, ...]
    """
    if symbol is None:
        symbol = config.SYMBOL
    if resolution is None:
        resolution = config.TIMEFRAME_MINUTES
    to_time = int(time.time())
    from_time = to_time - (resolution * 60 * (count + 20))
    url = f"{config.DELTA_API_BASE}/v2/chart/history?symbol={symbol}&resolution={resolution}&from={from_time}&to={to_time}"
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.4.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            res = data.get('result', {})
            if res and 'c' in res and 'o' in res:
                candles = []
                c_len = len(res['c'])
                for i in range(c_len):
                    candles.append({
                        'time': res['t'][i] if 't' in res and i < len(res['t']) else 0,
                        'open': float(res['o'][i]),
                        'high': float(res['h'][i]),
                        'low': float(res['l'][i]),
                        'close': float(res['c'][i]),
                        'volume': float(res['v'][i]) if 'v' in res and i < len(res['v']) else 0.0
                    })
                return candles
    except Exception as e:
        pass
    return []


def get_wallet_balance():
    """Fetch live account balance via MCP"""
    try:
        res = call_mcp_tool("rowveq1gvjzz", "Get current wallet balances")
        for item in _mcp_records(res, "Wallet balance", ('asset_symbol', 'balance')):
            if item.get('asset_symbol') == 'USD':
                return {
                    'total_usd': float(item.get('balance', 0)),
                    'available_usd': float(item.get('available_balance', 0)),
                    'balance_inr': float(item.get('balance_inr', 0))
                }
    except Exception as e:
        print(f"[ERROR] Failed to fetch balance: {e}")
    return None


def get_open_positions():
    """Fetch currently active positions via MCP"""
    try:
        res = call_mcp_tool("rowickixv4on", "Get all open positions")
        return _mcp_records(res, "Open positions", ('product_symbol', 'size'))
    except Exception as e:
        print(f"[ERROR] Failed to fetch positions: {e}")
        raise


def place_order(symbol=None, side="buy", order_type="market", size=1, price=None):
    """Place an order on Delta Exchange via MCP"""
    if symbol is None:
        symbol = config.SYMBOL
    instructions = f"Place a {order_type} {side} order for {size} contract of {symbol}"
    if price and order_type.lower() == "limit":
        instructions += f" at price {price}"
    
    print(f"[ORDER ATTEMPT] {instructions}")
    try:
        res = call_mcp_tool("rowxvuezrvvi", instructions)
        return res
    except Exception as e:
        print(f"[ERROR] Failed to place order: {e}")
        return None
