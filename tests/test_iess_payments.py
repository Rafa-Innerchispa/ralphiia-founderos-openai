import unittest

from quoteops.iess_payments import parse_iess_payment_ocr


class TestIessPaymentParser(unittest.TestCase):
    def test_extracts_bank_receipt_and_plan(self):
        text = """Pago realizado
        Hector, haspagado$108.00aIESS(030-PLANI
        -PAGODEPLANILLAS:0000000216009271:003:S)
        Miercoles,15jul.2026-18:03
        Numerodecomprobante:1067762"""
        result = parse_iess_payment_ocr(text)
        self.assertEqual(result["amount"], 108.0)
        self.assertEqual(result["plan_code"], "0000000216009271")
        self.assertEqual(result["plan_type"], "003")
        self.assertEqual(result["bank_receipt"], "1067762")
        self.assertTrue(result["paid_at"].startswith("2026-07-15T18:03"))

    def test_incomplete_text_does_not_invent_fields(self):
        result = parse_iess_payment_ocr("Pago IESS")
        self.assertEqual(result["amount"], 0.0)
        self.assertEqual(result["plan_code"], "")
        self.assertEqual(result["bank_receipt"], "")


if __name__ == "__main__":
    unittest.main()
