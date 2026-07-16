import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from quoteops.app import app


class TestConversationApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_conversation_contract_and_idempotency(self):
        key = f"api-{uuid4()}"
        payload = {
            "idempotency_key": key,
            "language": "en",
            "message": "FEMAR needs an access-control system in Quito for 3 doors.",
            "attachments": [],
        }
        first = self.client.post("/api/conversation/messages", json=payload)
        second = self.client.post("/api/conversation/messages", json=payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["mission_id"], second.json()["mission_id"])
        self.assertTrue(second.json()["idempotent_replay"])
        self.assertEqual(first.json()["language"], "en")

    def test_main_page_is_conversation_first_and_bilingual(self):
        response = self.client.get("/")
        body = response.text

        self.assertEqual(response.status_code, 200)
        self.assertIn("Cuéntame qué necesitas construir", body)
        self.assertIn("Tell me what you need to build", body)
        self.assertIn("Codex-built / MCP runtime", body)
        self.assertIn("Asistente para decidir", body)
        self.assertIn("Decision assistant", body)
        self.assertNotIn("Intake Composer", body)
        self.assertNotIn("Preview fallback", body)
        self.assertNotIn("sandbox safe", body)

    def test_cedula_lookup_does_not_call_ruc_provider(self):
        key = f"identity-{uuid4()}"
        mission = self.client.post(
            "/api/conversation/messages",
            json={
                "idempotency_key": key,
                "language": "es",
                "message": "FEMAR necesita control de acceso.",
                "attachments": [],
            },
        ).json()
        response = self.client.post(
            "/api/customer/lookup",
            json={
                "identifier": "1710034065",
                "mission_id": mission["mission_id"],
                "language": "es",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["identifier_type"], "cedula")
        self.assertFalse(response.json()["provider_called"])

    def test_attachment_is_stored_with_hash(self):
        key = f"attachment-{uuid4()}"
        mission = self.client.post(
            "/api/conversation/messages",
            json={
                "idempotency_key": key,
                "language": "en",
                "message": "FEMAR access-control project.",
                "attachments": [{"name": "scope.txt", "media_type": "text/plain", "size_bytes": 13}],
            },
        ).json()
        response = self.client.post(
            f"/api/conversation/missions/{mission['mission_id']}/attachments",
            data={"language": "en"},
            files={"file": ("scope.txt", b"real evidence", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        attachment = response.json()["dossier"]["attachments"][0]
        self.assertEqual(attachment["status"], "stored")
        self.assertEqual(len(attachment["sha256"]), 64)

    def test_validation_error_follows_requested_language(self):
        response = self.client.post(
            "/api/conversation/messages",
            headers={"x-quoteops-language": "en"},
            json={"idempotency_key": "short", "language": "en", "message": ""},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "validation_error")
        self.assertIn("Review", response.json()["detail"]["message"])

    def test_whatsapp_and_chatgpt_continue_the_same_mission_idempotently(self):
        event_id = f"wa-{uuid4()}"
        payload = {
            "channel": "whatsapp",
            "payload": {
                "event_id": event_id,
                "language": "es",
                "name": "FEMAR",
                "phone": "0990000000",
                "text": "Necesitamos revisar el proyecto de control de acceso en Guayaquil.",
            },
        }
        first = self.client.post("/api/conversation/channel-events", json=payload)
        replay = self.client.post("/api/conversation/channel-events", json=payload)
        mission_id = first.json()["mission_id"]
        continued = self.client.post(
            "/api/conversation/messages",
            json={
                "mission_id": mission_id,
                "idempotency_key": f"chatgpt-{uuid4()}",
                "language": "en",
                "source_channel": "chatgpt_mcp",
                "message": "Continue this same case without creating a duplicate.",
            },
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["dossier"]["customer"]["name"], "FEMAR")
        self.assertEqual(first.json()["dossier"]["work_item"]["source_channel"], "whatsapp")
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertTrue(replay.json()["channel_event"]["deduplicated"])
        self.assertEqual(continued.json()["mission_id"], mission_id)
        self.assertEqual(continued.json()["language"], "en")


if __name__ == "__main__":
    unittest.main()
