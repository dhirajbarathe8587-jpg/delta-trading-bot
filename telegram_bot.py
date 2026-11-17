"""
Telegram Notification Module for DeltaTradingBot
Sends trade alerts and handles authorized Telegram commands
"""
import urllib.request
import json
import os
import threading
import time

_warning_logged = False
_listener_thread = None

def _api_request(method, payload, timeout=10):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    url = f"https://api.telegram.org/bot{token}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API request failed"))
    return result.get("result")

def send_message(text, chat_id=None):
    """Send a message to the configured chat or a specified authorized chat."""
    global _warning_logged
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    destination = str(chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip())
    if not token or not destination:
        if not _warning_logged:
            print("[TELEGRAM] Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable Telegram.")
            _warning_logged = True
        return False
    try:
        _api_request("sendMessage", {"chat_id": destination, "text": text})
        return True
    except Exception as e:
        print(f"[TELEGRAM ERROR] Could not send message: {e}")
        return False

def _handle_update(update):
    message = update.get("message") or update.get("edited_message")
    if not message or not message.get("chat"):
        return

    authorized_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    chat_id = str(message["chat"].get("id", ""))
    if not authorized_chat_id or chat_id != authorized_chat_id:
        return

    text = (message.get("text") or "").strip()
    if not text:
        send_message("I can read text commands. Send /help to see available commands.", chat_id)
        return

    command = text.split()[0].split("@")[0].lower()
    if command in ("/start", "/help"):
        reply = (
            "DeltaTradingBot commands:\n"
            "/status - check that the bot is running\n"
            "/balance - get the Delta Exchange account balance\n\n"
            "Account credentials are managed in ViaSocket/Render settings; "
            "do not send API keys or secrets in Telegram."
        )
    elif command == "/status":
        reply = "✅ DeltaTradingBot is running and listening for Telegram commands."
    elif command == "/balance":
        try:
            from delta_client import get_wallet_balance
            balance = get_wallet_balance()
            if not balance:
                reply = "Could not read the account balance. Check the ViaSocket MCP connection and Render logs."
            else:
                reply = (
                    f"Delta Exchange balance:\n"
                    f"Total: ${balance['total_usd']:.4f} USD\n"
                    f"Available: ${balance['available_usd']:.4f} USD\n"
                    f"Approx: Rs.{balance['balance_inr']:.2f}"
                )
        except Exception as e:
            print(f"[TELEGRAM ERROR] Balance command failed: {e}")
            reply = "Could not read the account balance. Check the ViaSocket MCP connection and Render logs."
    else:
        reply = "Message received. Send /help for the available commands."

    send_message(reply, chat_id)

def _poll_updates():
    offset = None
    while True:
        try:
            payload = {"timeout": 25, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            updates = _api_request("getUpdates", payload, timeout=35) or []
            for update in updates:
                offset = update["update_id"] + 1
                _handle_update(update)
        except Exception as e:
            print(f"[TELEGRAM ERROR] Command listener failed: {e}")
            time.sleep(5)

def start_command_listener():
    """Start long polling for commands from the configured Telegram chat."""
    global _listener_thread
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[TELEGRAM] Command listener disabled; set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return
    if _listener_thread and _listener_thread.is_alive():
        return
    _listener_thread = threading.Thread(target=_poll_updates, daemon=True)
    _listener_thread.start()
    print("[TELEGRAM] Command listener started.")

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
