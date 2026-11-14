import time
import datetime
import sys
import os
import config
from indicators import check_ema_crossover, calculate_rsi, check_higher_timeframe_trend
from delta_client import (
    get_live_ticker,
    get_candles,
    get_wallet_balance,
    get_open_positions,
    place_order
)
from telegram_bot import (
    notify_buy,
    notify_sell,
    notify_take_profit,
    notify_stop_loss,
    notify_ema_exit,
    notify_bot_started,
    notify_scan_summary
)
import http.server
import socketserver
import threading

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        # Read last 35 lines of trading_bot.log
        logs_html = "Waiting for logs..."
        try:
            if os.path.exists("trading_bot.log"):
                with open("trading_bot.log", "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    last_lines = lines[-35:] if len(lines) > 35 else lines
                    logs_html = "".join(last_lines)
        except Exception as e:
            logs_html = f"Log read error: {e}"

        # Get active position if any
        active_pos_html = '<span style="color:#888;">No Trade (Scanning 9 Coins)</span>'
        try:
            from delta_client import get_open_positions
            positions = get_open_positions()
            if positions:
                for p in positions:
                    sz = float(p.get('size', 0))
                    if sz != 0:
                        sym = p.get('product_symbol')
                        side_txt = "LONG (BUY)" if sz > 0 else "SHORT (SELL)"
                        side_color = "#00e676" if sz > 0 else "#ff5252"
                        entry = float(p.get('entry_price', 0))
                        active_pos_html = f'<strong style="color:{side_color};">{side_txt}</strong> on <strong>{sym}</strong> @ ${entry:,.4f}'
        except:
            pass

        # Balance
        bal_html = "$3.69 USD"
        try:
            from delta_client import get_wallet_balance
            b = get_wallet_balance()
            if b:
                bal_html = f"${b['total_usd']:.4f} USD (~Rs.{b['balance_inr']:.2f})"
        except:
            pass

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Delta Trading Bot - Live Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="5">
    <style>
        body {{ background:#0e1117; color:#f0f2f6; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; margin:0; padding:15px; }}
        .header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #262730; padding-bottom:10px; margin-bottom:15px; }}
        .title {{ font-size:1.3rem; font-weight:bold; color:#00e676; }}
        .badge {{ background:#00e67622; color:#00e676; border:1px solid #00e676; padding:4px 10px; border-radius:20px; font-size:0.8rem; font-weight:bold; }}
        .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin-bottom:15px; }}
        .card {{ background:#1e212b; border:1px solid #2e3346; border-radius:10px; padding:12px; }}
        .card-label {{ color:#888; font-size:0.75rem; text-transform:uppercase; margin-bottom:5px; }}
        .card-val {{ font-size:1.1rem; font-weight:bold; }}
        .terminal-box {{ background:#000; border:1px solid #333; border-radius:8px; padding:12px; font-family:'Courier New',Courier,monospace; font-size:0.78rem; line-height:1.4; color:#00ff66; height:320px; overflow-y:auto; white-space:pre-wrap; word-break:break-all; box-shadow:inset 0 0 10px rgba(0,255,0,0.1); }}
        .footer {{ text-align:center; color:#555; font-size:0.75rem; margin-top:10px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">🤖 Delta Trading Bot</div>
        <div class="badge">● 24/7 CLOUD ACTIVE</div>
    </div>
    <div class="grid">
        <div class="card">
            <div class="card-label">Wallet Balance</div>
            <div class="card-val" style="color:#ffd700;">{bal_html}</div>
        </div>
        <div class="card">
            <div class="card-label">Active Trade</div>
            <div class="card-val" style="font-size:0.95rem;">{active_pos_html}</div>
        </div>
        <div class="card">
            <div class="card-label">Strategy / Risk</div>
            <div class="card-val" style="font-size:0.85rem; color:#64b5f6;">EMA 9/15 | TP +1.2% | SL -1.0%</div>
        </div>
        <div class="card">
            <div class="card-label">Telegram Alerts</div>
            <div class="card-val" style="font-size:0.85rem; color:#29b6f6;">Connected 📱</div>
        </div>
    </div>
    <div style="font-weight:bold; font-size:0.85rem; color:#aaa; margin-bottom:6px;">💻 LIVE CONSOLE LOGS (CMD STYLE - AUTO REFRESH 5s):</div>
    <div class="terminal-box" id="term">{logs_html}</div>
    <div class="footer">Page auto-refreshes every 5s | Cloud hosted on Render 24/7</div>
    <script>
        var term = document.getElementById('term');
        term.scrollTop = term.scrollHeight;
    </script>
</body>
</html>"""
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Suppress HTTP request logs from console

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            print(f"[CLOUD WEB] Web health server listening on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[CLOUD WEB] Server note: {e}")

threading.Thread(target=start_health_server, daemon=True).start()


class LoggerTee:
    """Simultaneously writes to stdout and trading_bot.log with clean UTF-8 encoding"""
    def __init__(self, filename="trading_bot.log"):
        self.terminal = sys.stdout
        self.log_file = open(filename, "a", encoding="utf-8")

    def write(self, message):
        try:
            self.terminal.write(message)
            self.terminal.flush()
        except Exception:
            pass
        try:
            self.log_file.write(message)
            self.log_file.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.terminal.flush()
            self.log_file.flush()
        except Exception:
            pass

sys.stdout = LoggerTee("trading_bot.log")
sys.stderr = sys.stdout

class SafeMicroCryptoBot:
    def __init__(self):
        self.watchlist = config.WATCHLIST
        self.last_summary_time = 0  # For periodic Telegram summaries (every 30 min)
        print("=" * 70)
        print("   DELTA EXCHANGE 24/7 SAFE MICRO-CRYPTO BOT (BUY + SELL + TELEGRAM)")
        print("=" * 70)
        print(f"Safe Micro Coins ({len(self.watchlist)}): {', '.join(self.watchlist)}")
        print(f"Order Size:          {config.ORDER_SIZE} contract per trade (Strictly Micro-Lot)")
        print(f"Max Active Trades:   {config.MAX_ACTIVE_TRADES} at a time (Zero Over-Leveraging)")
        print(f"Strategy:            EMA {config.FAST_EMA} & EMA {config.SLOW_EMA} on {config.TIMEFRAME_MINUTES}m candles")
        print(f"BUY  Signal:         5m EMA9 crosses ABOVE EMA15 + 15m Trend BULLISH")
        print(f"SELL Signal:         5m EMA9 crosses BELOW EMA15 + 15m Trend BEARISH")
        print(f"Take Profit / Stop:  +{config.TAKE_PROFIT_PCT}% / -{config.STOP_LOSS_PCT}%")
        print(f"Telegram Alerts:     ENABLED (DeltaTradingBot)")
        print(f"Check Interval:      {config.CHECK_INTERVAL_SEC} seconds")
        print(f"Dry Run (Test Mode): {'ENABLED (Simulated)' if config.DRY_RUN else 'DISABLED (Live Trading)'}")
        print("=" * 70)

    def get_balance_usd(self):
        try:
            bal = get_wallet_balance()
            if bal:
                return bal['available_usd']
        except:
            pass
        return 0.0

    def get_real_active_position(self):
        """Fetch actual ground truth position from Delta Exchange API"""
        try:
            positions = get_open_positions()
            if positions and len(positions) > 0:
                for p in positions:
                    size = float(p.get('size', 0))
                    if size != 0:
                        return {
                            'symbol': p.get('product_symbol'),
                            'size': size,
                            'entry_price': float(p.get('entry_price', 0)),
                            'unrealized_pnl': float(p.get('unrealized_pnl', 0)),
                            'side': 'buy' if size > 0 else 'sell'
                        }
        except Exception as e:
            print(f"[WARN] Failed checking open positions: {e}")
        return None

    def monitor_active_trade(self, pos):
        """Monitor live confirmed position - handles both BUY/LONG and SELL/SHORT"""
        symbol = pos['symbol']
        ticker = get_live_ticker(symbol)
        if not ticker:
            return

        current_price = ticker['mark_price']
        entry = pos['entry_price']
        side = pos['side']
        size = abs(pos['size'])

        # PnL for both LONG and SHORT
        if side == 'buy':
            pnl_pct = ((current_price - entry) / entry) * 100.0
        else:
            pnl_pct = ((entry - current_price) / entry) * 100.0

        candles = get_candles(symbol, resolution=config.TIMEFRAME_MINUTES, count=30)
        signal, ema9, ema15 = check_ema_crossover(candles, fast_period=config.FAST_EMA, slow_period=config.SLOW_EMA)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        side_label = "LONG" if side == 'buy' else "SHORT"
        pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"
        print(f"[{now_str}] [{side_label} ACTIVE] {symbol} @ ${entry:,.4f} | Now: ${current_price:,.4f} | {pnl_emoji} PnL: {pnl_pct:+.2f}% | EMA9: {ema9} / EMA15: {ema15}")

        balance = self.get_balance_usd()

        # === EXIT CONDITIONS ===
        # 1. Take Profit
        if pnl_pct >= config.TAKE_PROFIT_PCT:
            print(f"\n🎯 [TAKE PROFIT] {symbol} {side_label}: +{pnl_pct:.2f}%! Closing...")
            self.close_position(symbol, size, side, reason=f"Take Profit (+{pnl_pct:.2f}%)")
            notify_take_profit(symbol, side, pnl_pct, balance)

        # 2. Stop Loss
        elif pnl_pct <= -config.STOP_LOSS_PCT:
            print(f"\n🛑 [STOP LOSS] {symbol} {side_label}: {pnl_pct:.2f}%. Closing...")
            self.close_position(symbol, size, side, reason=f"Stop Loss ({pnl_pct:.2f}%)")
            notify_stop_loss(symbol, side, pnl_pct, balance)

        # 3. EMA Reversal Exit
        elif side == 'buy' and signal == 'BEARISH_CROSS':
            print(f"\n⚠️ [EMA REVERSAL] {symbol} LONG: EMA9 crossed BELOW EMA15. Exiting...")
            self.close_position(symbol, size, side, reason="EMA Reversal (Bearish Cross)")
            notify_ema_exit(symbol, side, pnl_pct, balance)

        elif side == 'sell' and signal == 'BULLISH_CROSS':
            print(f"\n⚠️ [EMA REVERSAL] {symbol} SHORT: EMA9 crossed ABOVE EMA15. Exiting...")
            self.close_position(symbol, size, side, reason="EMA Reversal (Bullish Cross)")
            notify_ema_exit(symbol, side, pnl_pct, balance)

    def scan_all_cryptos(self):
        """
        Scan all watchlist cryptos for BUY and SELL signals.
        BUY  = EMA9 crosses ABOVE EMA15 + 15m Bullish (above 50-EMA)
        SELL = EMA9 crosses BELOW EMA15 + 15m Bearish (below 50-EMA)
        """
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scan_summary = []

        for symbol in self.watchlist:
            try:
                ticker = get_live_ticker(symbol)
                if not ticker:
                    continue

                price = ticker['mark_price']
                candles_5m = get_candles(symbol, resolution=config.TIMEFRAME_MINUTES, count=40)
                signal, ema9, ema15 = check_ema_crossover(candles_5m, fast_period=config.FAST_EMA, slow_period=config.SLOW_EMA)
                rsi = calculate_rsi(candles_5m, period=14) if candles_5m else None

                # 15m Higher Timeframe Trend Filter
                htf_bullish = True
                htf_ema50 = 0.0
                if config.USE_TREND_FILTER:
                    candles_15m = get_candles(symbol, resolution=config.TREND_TIMEFRAME_MIN, count=60)
                    htf_bullish, htf_ema50 = check_higher_timeframe_trend(candles_15m, period=config.TREND_EMA_PERIOD)
                htf_bearish = not htf_bullish

                # Scan label
                if signal in ("BULLISH_CROSS", "BULLISH") and htf_bullish:
                    tag = "BUY"
                elif signal in ("BEARISH_CROSS", "BEARISH") and htf_bearish:
                    tag = "SELL"
                else:
                    tag = "WAIT"
                scan_summary.append(f"{symbol.replace('USD','')}:{tag}")

                # === BUY (LONG) SIGNAL ===
                if signal == "BULLISH_CROSS":
                    if config.USE_TREND_FILTER and not htf_bullish:
                        print(f"\n[FILTER] {symbol} BUY blocked - 15m BEARISH (${price:,.4f} < 50EMA ${htf_ema50:,.4f})")
                    elif config.USE_RSI_FILTER and rsi and rsi > config.RSI_MAX_BUY:
                        print(f"\n[FILTER] {symbol} BUY blocked - RSI overbought ({rsi:.1f})")
                    else:
                        print(f"\n🚀 [BUY SIGNAL] {symbol} | EMA9 > EMA15 | 15m BULLISH | ${price:,.4f}")
                        balance = self.get_balance_usd()
                        self.open_position(symbol, price, side="buy")
                        notify_buy(symbol, price, int(config.ORDER_SIZE), balance)
                        return

                # === SELL (SHORT) SIGNAL ===
                elif signal == "BEARISH_CROSS":
                    if config.USE_TREND_FILTER and not htf_bearish:
                        print(f"\n[FILTER] {symbol} SELL blocked - 15m BULLISH (${price:,.4f} > 50EMA ${htf_ema50:,.4f})")
                    else:
                        print(f"\n📉 [SELL SIGNAL] {symbol} | EMA9 < EMA15 | 15m BEARISH | ${price:,.4f}")
                        balance = self.get_balance_usd()
                        self.open_position(symbol, price, side="sell")
                        notify_sell(symbol, price, int(config.ORDER_SIZE), balance)
                        return

            except Exception as e:
                pass

        summary_str = " | ".join(scan_summary)
        print(f"[{now_str}] [SCAN {len(scan_summary)} Coins] {summary_str} | No Trade")

        # Send Telegram summary every 30 minutes
        now_ts = time.time()
        if now_ts - self.last_summary_time >= 1800:
            tg_summary = "\n".join([f"• {s}" for s in scan_summary])
            notify_scan_summary(tg_summary)
            self.last_summary_time = now_ts

    def run_one_cycle(self):
        real_pos = self.get_real_active_position()
        if real_pos:
            self.monitor_active_trade(real_pos)
        else:
            self.scan_all_cryptos()

    def open_position(self, symbol, price, side="buy"):
        qty = int(config.ORDER_SIZE)
        label = "BUY (LONG)" if side == "buy" else "SELL (SHORT)"
        print(f"[ACTION] Placing {label} | {qty} contract | {symbol} @ ~${price:,.4f}")

        if config.DRY_RUN:
            print(f"[DRY RUN] {symbol} simulated {label} opened.")
            return

        place_order(symbol=symbol, side=side, order_type="market", size=qty)
        time.sleep(2)
        real_pos = self.get_real_active_position()
        if real_pos and real_pos['symbol'] == symbol:
            confirmed = "LONG" if real_pos['side'] == 'buy' else "SHORT"
            print(f"[VERIFIED] {symbol} {confirmed} LIVE on Delta Exchange! Entry: ${real_pos['entry_price']:,.4f}")
        else:
            print(f"[STATUS] Order sent. Verifying in next cycle.")

    def close_position(self, symbol, size, side, reason=""):
        exit_side = "sell" if side == "buy" else "buy"
        qty = int(round(abs(size)))
        if qty < 1:
            qty = 1
        label = "SELL to close LONG" if exit_side == "sell" else "BUY to close SHORT"
        print(f"[ACTION] Closing {symbol} | {label} | {qty} contract | {reason}")

        if config.DRY_RUN:
            print(f"[DRY RUN] {symbol} closed.")
            return

        place_order(symbol=symbol, side=exit_side, order_type="market", size=qty)
        time.sleep(2)
        print(f"[CLOSED] {symbol} closed. ({reason})")

    def start(self):
        print("\nChecking Account Balance...")
        bal = get_wallet_balance()
        bal_usd = 0.0
        if bal:
            bal_usd = bal['total_usd']
            print(f"Balance: ${bal['total_usd']:.4f} USD (~Rs.{bal['balance_inr']:.2f} INR) | Free: ${bal['available_usd']:.4f} USD")
        else:
            print("[INFO] Could not fetch balance, proceeding...")

        print(f"\nBot is LIVE - Scanning BUY & SELL signals 24/7. Press Ctrl+C to stop.\n")

        # Send Telegram startup notification
        notify_bot_started(bal_usd)
        self.last_summary_time = time.time()

        while True:
            try:
                self.run_one_cycle()
                time.sleep(config.CHECK_INTERVAL_SEC)
            except KeyboardInterrupt:
                print("\n[STOP] Bot stopped by user.")
                break
            except Exception as e:
                print(f"[ERROR] {e}. Retrying in {config.CHECK_INTERVAL_SEC}s...")
                time.sleep(config.CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    bot = SafeMicroCryptoBot()
    bot.start()
