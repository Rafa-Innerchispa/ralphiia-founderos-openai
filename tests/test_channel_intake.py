import unittest
from quoteops.adapters.channel_intake import ChannelIntakeRouter


class TestChannelIntake(unittest.TestCase):
    def test_whatsapp_and_telegram_share_contract_and_dedupe(self):
        router = ChannelIntakeRouter()
        wa = router.ingest("whatsapp", {"event_id": "wa-1", "name": "Ana", "phone": "099", "text": "Cotizar"})
        repeat = router.ingest("whatsapp", {"event_id": "wa-1", "name": "Ana", "phone": "099", "text": "Cotizar"})
        tg = router.ingest("telegram", {"update_id": "tg-1", "from_name": "Luis", "username": "luis", "text": "Revisar red"})
        self.assertEqual(wa["intake"]["source_channel"], "whatsapp")
        self.assertTrue(repeat["deduplicated"])
        self.assertEqual(tg["intake"]["source_channel"], "telegram")
        self.assertEqual(set(wa["intake"]), set(tg["intake"]))


if __name__ == "__main__":
    unittest.main()
