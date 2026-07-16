import unittest
from unittest.mock import MagicMock, patch

from quoteops.operations_dashboard import OperationsDashboardService


class TestOperationsDashboard(unittest.TestCase):
    @patch("quoteops.operations_dashboard.MongoClient")
    def test_snapshot_is_read_only_and_exposes_real_operational_sections(self, client_cls):
        db = MagicMock()
        client_cls.return_value.__getitem__.return_value = db
        db.ralfia_iess_vouchers.count_documents.side_effect = [24, 1, 14]
        db.accounting_payments.find_one.return_value = {"payment_id": "payment_iess_1067762", "amount": 108.0}
        db.quoteops_bank_statements.count_documents.side_effect = [1, 1]
        db.quoteops_bank_transactions.count_documents.return_value = 57
        db.quoteops_reconciliation_candidates.count_documents.side_effect = [3, 0]
        db.whatsapp_pending_actions.count_documents.return_value = 0
        db.quoteops_bank_statements.find_one.return_value = {
            "statement_id": "statement_demo", "continuity_status": "exception"
        }
        db.ralfia_iess_vouchers.find.return_value.sort.return_value.limit.return_value = []
        db.quoteops_reconciliation_candidates.find.return_value.sort.return_value.limit.return_value = []

        result = OperationsDashboardService("mongodb://test").snapshot()

        self.assertTrue(result["ok"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["environment"], "staging")
        self.assertEqual(result["iess"]["paid_verified"], 1)
        self.assertEqual(result["bank"]["transaction_count"], 57)
        self.assertEqual(result["bank"]["candidate_count"], 3)
        db.ralfia_iess_vouchers.update_one.assert_not_called()
        db.quoteops_reconciliation_candidates.update_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
