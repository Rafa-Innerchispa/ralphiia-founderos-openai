import tempfile
import unittest
import json
from pathlib import Path

from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.settings import Settings


class TestQuoteExecution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = QuoteExecutionService(Settings(quoteops_artifact_root=self.tmp.name, allow_production_writes=False))

    def tearDown(self):
        self.tmp.cleanup()

    def test_approval_pdf_sandbox_delivery_and_owner_guard(self):
        blocked = self.service.approve({"intake": {}, "approved_by": "Rafael", "mode": "sandbox"})
        self.assertEqual(blocked["status"], "blocked")
        approved = self.service.approve({"intake": {"customer_name": "Demo", "contact": "demo@example.com", "original_text": "Control de acceso QR"}, "approved_by": "Rafael", "mode": "sandbox"})
        self.assertEqual(approved["status"], "approved")
        self.assertTrue(self.service.artifact_path(approved["artifact_id"]).read_bytes().startswith(b"%PDF-1.4"))
        delivery = self.service.deliver({"approval_id": approved["approval_id"], "channels": ["whatsapp", "telegram", "chatgpt_mcp"], "mode": "sandbox"})
        self.assertEqual(delivery["status"], "simulated")
        owner = self.service.deliver({"approval_id": approved["approval_id"], "channels": ["whatsapp"], "mode": "owner"})
        self.assertEqual(owner["status"], "blocked")

    def test_registered_delivery_remains_json_safe_when_mongo_mutates_insert(self):
        approved = self.service.approve({"intake": {"customer_name": "FEMAR", "contact": "1710034065", "original_text": "Control de acceso"}, "approved_by": "Rafael", "mode": "judge"})

        class MutatingCollection:
            def insert_one(self, value):
                value["_id"] = object()

        class FakeDb:
            quoteops_deliveries = MutatingCollection()

        self.service.db = FakeDb()
        delivery = self.service.deliver({"approval_id": approved["approval_id"], "channels": ["download"], "mode": "judge"})

        self.assertEqual(delivery["status"], "registered")
        json.dumps(delivery)


if __name__ == "__main__":
    unittest.main()
