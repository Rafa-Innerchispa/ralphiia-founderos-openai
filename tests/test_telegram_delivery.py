import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from quoteops.adapters.telegram_delivery import TelegramDelivery, TelegramDeliveryError


class TestTelegramDelivery(unittest.TestCase):
    def test_requires_server_side_token(self):
        with self.assertRaisesRegex(TelegramDeliveryError, "telegram_not_configured"):
            TelegramDelivery("").send_message("77", "Hola")

    @patch("quoteops.adapters.telegram_delivery.httpx.Client")
    def test_send_message_never_exposes_token_in_payload(self, client_cls):
        response = httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
        client_cls.return_value.__enter__.return_value.post.return_value = response
        result = TelegramDelivery("secret-token").send_message(77, "Cotización lista")
        self.assertTrue(result["ok"])
        _, kwargs = client_cls.return_value.__enter__.return_value.post.call_args
        self.assertEqual(kwargs["json"], {"chat_id": 77, "text": "Cotización lista"})

    def test_document_path_is_validated_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quote.pdf"
            path.write_bytes(b"%PDF")
            with patch("quoteops.adapters.telegram_delivery.httpx.Client") as client_cls:
                response = httpx.Response(200, json={"ok": True, "result": {"message_id": 2}})
                client_cls.return_value.__enter__.return_value.post.return_value = response
                result = TelegramDelivery("secret-token").send_document(77, path)
                self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
