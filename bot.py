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
        html = """<!DOCTYPE html>
<html>
<head><title>Delta Trading Bot</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family:sans-serif; background:#121212; color:#fff; padding:20px; text-align:center;">
    <h2>🤖 Delta Trading Bot is LIVE</h2>
    <p style="color:#00e676; font-size:1.3rem; font-weight:bold;">● 24/7 Cloud Active</p>
    <p>Strategy: EMA 9 & 15 Crossover + 15m Trend Filter (BUY & SELL)</p>
    <p>Coins: XRP, SUI, ADA, XLM, WIF, HBAR, OP, TRUMP, BTC</p>
    <p style="color:#aaa;">Alerts sent directly to Telegram!</p>
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
