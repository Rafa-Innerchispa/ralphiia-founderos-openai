import unittest

from quoteops.iess_payments import IessPaymentService


class TestIessPaymentSecurity(unittest.TestCase):
    def test_sender_comparison_accepts_same_whatsapp_identity(self):
        self.assertTrue(
            IessPaymentService._same_sender(
                "593999059000@s.whatsapp.net",
                "+593 999 059 000",
            )
        )

    def test_sender_comparison_rejects_other_or_empty_identity(self):
        self.assertFalse(IessPaymentService._same_sender("593999059000@s.whatsapp.net", "593111111111"))
        self.assertFalse(IessPaymentService._same_sender("", "593999059000"))


if __name__ == "__main__":
    unittest.main()
