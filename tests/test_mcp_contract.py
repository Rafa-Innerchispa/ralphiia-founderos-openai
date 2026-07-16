import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from quoteops.app import app


class TestQuoteOpsMcpContract(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def rpc(self, method, params=None, request_id=1):
        return self.client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}},
        )

    def test_initialize_and_typed_tool_catalog(self):
        initialized = self.rpc("initialize", {"protocolVersion": "2025-06-18"})
        listed = self.rpc("tools/list")

        self.assertEqual(initialized.status_code, 200)
        self.assertEqual(initialized.json()["result"]["serverInfo"]["name"], "ralphiia-quoteops-staging")
        names = {item["name"] for item in listed.json()["result"]["tools"]}
        self.assertIn("quoteops_start_or_continue_mission", names)
        self.assertIn("quoteops_record_extracted_evidence", names)
        self.assertIn("quoteops_add_supplier_offer", names)
        self.assertIn("quoteops_review_catalog_draft", names)
        self.assertIn("quoteops_select_package", names)
        self.assertIn("quoteops_update_decision_brief", names)
        self.assertIn("quoteops_upsert_configuration_alternative", names)
        self.assertIn("quoteops_review_configuration_alternative", names)
        self.assertIn("quoteops_upsert_commercial_profile", names)
        self.assertIn("quoteops_get_sourcing_recommendations", names)
        self.assertNotIn("shell", names)
        self.assertNotIn("mongo_query", names)

    def test_chatgpt_image_extraction_is_persisted_and_idempotent(self):
        start_key = f"mcp-start-{uuid4()}"
        start = self.rpc(
            "tools/call",
            {
                "name": "quoteops_start_or_continue_mission",
                "arguments": {
                    "idempotency_key": start_key,
                    "language": "es",
                    "source_channel": "chatgpt_mcp",
                    "message": "FEMAR requiere rehabilitar control de acceso en Guayaquil para 2 puertas.",
                    "attachments": [],
                },
            },
        ).json()["result"]["structuredContent"]
        mission_id = start["mission_id"]
        evidence_key = f"mcp-image-{uuid4()}"
        arguments = {
            "mission_id": mission_id,
            "idempotency_key": evidence_key,
            "language": "es",
            "source_file_name": "foto-etiqueta.jpg",
            "media_type": "image/jpeg",
            "extraction_type": "product_label",
            "extracted_by": "chatgpt_mcp",
            "products": [
                {
                    "name": "Controladora visible en imagen",
                    "brand": "Marca leida",
                    "model": "MODEL-01",
                    "confidence": 0.88,
                    "region": "center",
                }
            ],
            "facts": [{"field": "voltage", "value": "12 V", "unit": "V", "confidence": 0.8}],
            "warnings": ["Confirmar el ultimo caracter del modelo"],
        }
        first = self.rpc(
            "tools/call",
            {"name": "quoteops_record_extracted_evidence", "arguments": arguments},
        ).json()["result"]["structuredContent"]
        second = self.rpc(
            "tools/call",
            {"name": "quoteops_record_extracted_evidence", "arguments": arguments},
        ).json()["result"]["structuredContent"]

        self.assertEqual(first["evidence"]["status"], "source_unlinked")
        self.assertIn("original_source_not_archived", first["evidence"]["warnings"])
        self.assertTrue(second["idempotent_replay"])
        self.assertEqual(first["evidence"]["evidence_id"], second["evidence"]["evidence_id"])

    def test_commercial_profile_and_sourcing_read_tools(self):
        mission = self.rpc("tools/call", {"name": "quoteops_start_or_continue_mission", "arguments": {"idempotency_key": f"mcp-commercial-{uuid4()}", "message": "Commercial comparison case."}}).json()["result"]["structuredContent"]
        saved = self.rpc("tools/call", {"name": "quoteops_upsert_commercial_profile", "arguments": {"mission_id": mission["mission_id"], "idempotency_key": f"mcp-profile-{uuid4()}", "profile": {"party_role": "supplier", "party_id": "mcp-supplier", "party_name": "MCP Supplier", "terms": {"credit_status": "historical_observed"}}}}).json()["result"]["structuredContent"]
        read = self.rpc("tools/call", {"name": "quoteops_get_sourcing_recommendations", "arguments": {"mission_id": mission["mission_id"], "language": "en"}}).json()["result"]["structuredContent"]
        self.assertEqual(saved["profile"]["party_id"], "mcp-supplier")
        self.assertEqual(read["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
