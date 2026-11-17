import os
import unittest
from unittest.mock import patch

import telegram_bot


class TelegramCommandTests(unittest.TestCase):
    def test_status_reply_for_authorized_chat(self):
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "/status"
            }
        }
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "12345"}):
            with patch.object(telegram_bot, "send_message") as send_message:
                telegram_bot._handle_update(update)

        send_message.assert_called_once_with(
            "✅ DeltaTradingBot is running and listening for Telegram commands.",
            "12345"
        )

    def test_ignores_unauthorized_chat(self):
        update = {
            "message": {
                "chat": {"id": 99999},
                "text": "/status"
            }
        }
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "12345"}):
            with patch.object(telegram_bot, "send_message") as send_message:
                telegram_bot._handle_update(update)

        send_message.assert_not_called()

    def test_balance_reply_uses_mcp_balance(self):
        update = {
            "message": {
                "chat": {"id": 12345},
                "text": "/balance"
            }
        }
        balance = {
            "total_usd": 12.5,
            "available_usd": 10.0,
            "balance_inr": 1037.5
        }
        with patch.dict(os.environ, {"TELEGRAM_CHAT_ID": "12345"}):
            with patch("delta_client.get_wallet_balance", return_value=balance):
                with patch.object(telegram_bot, "send_message") as send_message:
                    telegram_bot._handle_update(update)

        send_message.assert_called_once_with(
            "Delta Exchange balance:\n"
            "Total: $12.5000 USD\n"
            "Available: $10.0000 USD\n"
            "Approx: Rs.1037.50",
            "12345"
        )


if __name__ == "__main__":
    unittest.main()
