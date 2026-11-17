import unittest
from unittest.mock import patch

import delta_client


class McpResponseTests(unittest.TestCase):
    def test_wallet_balance_parses_json_encoded_data(self):
        response = {
            "data": '[{"asset_symbol":"USD","balance":"12.5",'
                    '"available_balance":"10","balance_inr":"1037.5"}]'
        }
        with patch.object(delta_client, "call_mcp_tool", return_value=response):
            balance = delta_client.get_wallet_balance()

        self.assertEqual(balance, {
            "total_usd": 12.5,
            "available_usd": 10.0,
            "balance_inr": 1037.5
        })

    def test_wallet_balance_rejects_text_response(self):
        with patch.object(delta_client, "call_mcp_tool", return_value={"data": "Request failed"}):
            balance = delta_client.get_wallet_balance()

        self.assertIsNone(balance)

    def test_failure_response_includes_mcp_error_reason(self):
        response = {"success": False, "message": "Action ID not found"}

        with self.assertRaisesRegex(ValueError, "Action ID not found"):
            delta_client._mcp_records(response, "Wallet balance", ("asset_symbol", "balance"))

    def test_open_positions_parses_nested_records(self):
        response = {
            "data": {
                "positions": '[{"product_symbol":"ETHUSD","size":"2"}]'
            }
        }
        with patch.object(delta_client, "call_mcp_tool", return_value=response):
            positions = delta_client.get_open_positions()

        self.assertEqual(positions, [{"product_symbol": "ETHUSD", "size": "2"}])

    def test_open_positions_does_not_treat_invalid_response_as_empty(self):
        with patch.object(delta_client, "call_mcp_tool", return_value={"data": "Request failed"}):
            with self.assertRaises(ValueError):
                delta_client.get_open_positions()


if __name__ == "__main__":
    unittest.main()
