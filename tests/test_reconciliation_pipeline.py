import unittest

import mongomock

from quoteops.reconciliation_pipeline import generate_candidates, persist_pilot


class TestReconciliationPipeline(unittest.TestCase):
    def setUp(self):
        self.db = mongomock.MongoClient().pcdoctor_swarm
        self.db.contifico_personas.insert_one({"persona_id": "party-1", "nombre": "TORRES BELLINI I-II"})
        self.db.contifico_documents.insert_many([
            {"contifico_id": "fac-1", "persona_id": "party-1", "tipo_documento": "FAC", "fecha_iso": "2026-01-18", "total_num": 250.0, "estado": "P"},
            {"contifico_id": "fac-2", "persona_id": "party-1", "tipo_documento": "FAC", "fecha_iso": "2026-01-20", "total_num": 250.0, "estado": "P"},
        ])
        self.statement = {
            "statement_id": "statement-1",
            "continuity_status": "balanced",
            "source_file": "fixture.pdf",
            "transactions": [{
                "transaction_id": "banktx-1",
                "transaction_date": "2026-01-19",
                "direction": "credit",
                "amount": 500.0,
                "description_normalized": "TRANSFERENCIA TORRES BELLINI I II",
            }],
            "ocr_text_by_page": [],
        }

    def test_split_merge_candidate_is_explainable_and_requires_approval(self):
        candidates = generate_candidates(self.db, self.statement)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["document_ids"], ["fac-1", "fac-2"])
        self.assertIn("split_merge_2_documents", candidates[0]["reasons"])
        self.assertTrue(candidates[0]["requires_human_approval"])

    def test_persistence_is_idempotent_and_does_not_mutate_contifico(self):
        candidates = generate_candidates(self.db, self.statement)
        persist_pilot(self.db, self.statement, candidates)
        persist_pilot(self.db, self.statement, candidates)
        self.assertEqual(self.db.quoteops_bank_transactions.count_documents({}), 1)
        self.assertEqual(self.db.quoteops_reconciliation_candidates.count_documents({}), 1)
        self.assertEqual(self.db.contifico_documents.count_documents({"estado": "P"}), 2)


if __name__ == "__main__":
    unittest.main()
