import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from quoteops.app import app
from quoteops.public_progress import PublicProgressFeed


class _TraceStore:
    def snapshot(self):
        return [
            {
                "integration": "MongoDB",
                "status": "ok",
                "source": "/home/private/database",
                "result": "token=must-not-leak",
            }
        ]


class TestPublicProgress(unittest.TestCase):
    def _feed(self, payload):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "progress.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        feed = PublicProgressFeed(path, trace_store=_TraceStore(), repo_root=Path(temporary.name))
        return temporary, feed

    def test_feed_is_bilingual_and_revision_is_stable(self):
        temporary, feed = self._feed(
            {
                "summary": {
                    "title_es": "Avance verificado",
                    "title_en": "Verified progress",
                    "phase_es": "H2 completo",
                    "phase_en": "H2 complete",
                    "status": "active",
                    "progress_percent": 29,
                },
                "verification": {
                    "tests_passed": 3,
                    "tests_total": 3,
                    "staging_status": "healthy",
                    "commit": "97e06a3",
                },
            }
        )
        self.addCleanup(temporary.cleanup)

        first = feed.snapshot("en")
        second = feed.snapshot("en")

        self.assertEqual(first["summary"]["title"], "Verified progress")
        self.assertEqual(first["language"], "en")
        self.assertEqual(first["revision"], second["revision"])
        self.assertNotEqual(first["generated_at"], "")

    def test_feed_redacts_private_values_and_limits_trace_fields(self):
        temporary, feed = self._feed(
            {
                "summary": {
                    "title_es": "Cliente 0992364866001 en 192.168.1.4",
                    "phase_es": "/home/private token=secret-value",
                    "status": "active",
                    "progress_percent": 10,
                },
                "verification": {
                    "tests_passed": 1,
                    "tests_total": 1,
                    "staging_status": "healthy",
                    "commit": "97e06a3",
                },
                "events": [
                    {
                        "id": "safe-event",
                        "type": "verification",
                        "title_es": "Prueba 1710034065",
                        "summary_es": "Sin datos privados",
                        "status": "completed",
                        "occurred_at": "2026-07-16T00:00:00Z",
                        "evidence": {
                            "commit": "97e06a3",
                            "private_payload": "must-not-leak",
                        },
                    }
                ],
            }
        )
        self.addCleanup(temporary.cleanup)

        payload = feed.snapshot("es")
        serialized = json.dumps(payload, ensure_ascii=False)

        self.assertNotIn("0992364866001", serialized)
        self.assertNotIn("1710034065", serialized)
        self.assertNotIn("192.168.1.4", serialized)
        self.assertNotIn("/home/private", serialized)
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("must-not-leak", serialized)
        self.assertEqual(payload["integrations"], [{"name": "MongoDB", "status": "ok"}])

    def test_public_endpoint_contract_headers_and_privacy(self):
        response = TestClient(app).get("/api/public/progress?language=en")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        self.assertEqual(response.headers["cache-control"], "no-store, max-age=0")
        payload = response.json()
        self.assertEqual(payload["language"], "en")
        self.assertEqual(set(payload["integrations"][0]), {"name", "status"})
        serialized = response.text
        self.assertNotIn("192.168.", serialized)
        self.assertNotIn("/home/", serialized)
        self.assertNotIn("latency_ms", serialized)
        self.assertNotIn("result", serialized)


if __name__ == "__main__":
    unittest.main()
