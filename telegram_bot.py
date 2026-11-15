"""
Telegram Notification Module for DeltaTradingBot
Sends real-time trade alerts to your mobile phone
"""
import urllib.request
import json
import ssl

TELEGRAM_TOKEN = "8051880123:AAFc1R43dq1M0svYHtCyJkpYX7KEVOKZ1GY"
TELEGRAM_CHAT_ID = "5029569407"

def _ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def send_message(text):
    """Send a plain text message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, context=_ssl_ctx(), timeout=10)
    except Exception as e:
        print(f"[TELEGRAM ERROR] Could not send message: {e}")

def notify_active_trade_update(symbol, side, entry, current_price, pnl_pct, balance_usd, balance_inr, ema9, ema15, time_ist):
    side_label = "LONG (BUY) 🟢" if side == "buy" else "SHORT (SELL) 🔴"
    pnl_emoji = "🟢" if pnl_pct >= 0 else "🔴"
    msg = (
        f"📊 LIVE TRADE STATUS UPDATE\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⏰ Time: {time_ist}\n"
        f"🪙 Coin: {symbol}\n"
        f"📌 Trade: {side_label}\n"
        f"💵 Entry: ${entry:,.4f}\n"
        f"📈 Current: ${current_price:,.4f}\n"
        f"{pnl_emoji} Live PnL: {pnl_pct:+.2f}%\n"
        f"💰 Balance: ${balance_usd:.4f} USD (~Rs.{balance_inr:.2f})\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 Strategy: EMA 9/15 | TP +1.2% | SL -1.0%\n"
        f"📐 EMA9: {ema9} | EMA15: {ema15}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🤖 Status: 24/7 Cloud Active on Render"
    )
    send_message(msg)

def notify_buy(symbol, price, qty, balance):
    msg = (
        f"🚀 BUY (LONG) SIGNAL!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Coin: {symbol}\n"
        f"Entry Price: ${price:,.4f}\n"
        f"Quantity: {qty} contract\n"
        f"Balance: ${balance:.4f} USD\n"
        f"━━━━━━━━━━━━━━━\n"
        f"TP: +1.2% | SL: -1.0%\n"
        f"Strategy: EMA9 > EMA15 + 15m Bullish Trend"
    )
    send_message(msg)

def notify_sell(symbol, price, qty, balance):
    msg = (
        f"📉 SELL (SHORT) SIGNAL!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Coin: {symbol}\n"
        f"Entry Price: ${price:,.4f}\n"
        f"Quantity: {qty} contract\n"
        f"Balance: ${balance:.4f} USD\n"
        f"━━━━━━━━━━━━━━━\n"
        f"TP: +1.2% | SL: -1.0%\n"
        f"Strategy: EMA9 < EMA15 + 15m Bearish Trend"
    )
    send_message(msg)

def notify_take_profit(symbol, side, pnl_pct, balance):
    side_label = "LONG" if side == "buy" else "SHORT"
    msg = (
        f"🎯 TAKE PROFIT HIT!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Coin: {symbol} ({side_label})\n"
        f"Profit: +{pnl_pct:.2f}%\n"
        f"Balance: ${balance:.4f} USD\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Position closed successfully!"
    )
    send_message(msg)

def notify_stop_loss(symbol, side, pnl_pct, balance):
    side_label = "LONG" if side == "buy" else "SHORT"
    msg = (
        f"🛑 STOP LOSS HIT!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Coin: {symbol} ({side_label})\n"
        f"Loss: {pnl_pct:.2f}%\n"
        f"Balance: ${balance:.4f} USD\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Capital protected. Waiting for next signal..."
    )
    send_message(msg)

def notify_ema_exit(symbol, side, pnl_pct, balance):
    side_label = "LONG" if side == "buy" else "SHORT"
    msg = (
        f"⚠️ EMA REVERSAL EXIT\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Coin: {symbol} ({side_label})\n"
        f"PnL: {pnl_pct:+.2f}%\n"
        f"Balance: ${balance:.4f} USD\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Trend reversed - Exited safely!"
    )
    send_message(msg)

def notify_bot_started(balance):
    msg = (
        f"🤖 DeltaTradingBot STARTED!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Status: LIVE & ACTIVE\n"
        f"Balance: ${balance:.4f} USD\n"
        f"Coins: XRP, SUI, ADA, XLM, WIF, HBAR, OP, TRUMP, BTC\n"
        f"━━━━━━━━━━━━━━━\n"
        f"BUY: EMA9 > EMA15 + 15m Bullish\n"
        f"SELL: EMA9 < EMA15 + 15m Bearish\n"
        f"TP: +1.2% | SL: -1.0%\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Bot is scanning 24/7. You'll get alerts here!"
    )
    send_message(msg)

def notify_scan_summary(coin_lines):
    """Send periodic scan summary every 30 minutes"""
    msg = (
        f"📡 Bot Status Update (30 min)\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{coin_lines}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Bot is active & watching for signals!"
    )
    send_message(msg)
