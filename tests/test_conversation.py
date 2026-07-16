import tempfile
import unittest

from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.conversation import ConversationService
from quoteops.contracts import (
    ConversationAttachment,
    ConversationMessageRequest,
    EditableQuoteLine,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    QuoteUpdateRequest,
)
from quoteops.settings import Settings


class TestConversationService(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            enable_openai=False,
            openai_api_key="",
            mongo_uri="mongodb://127.0.0.1:1/",
        )
        self.service = ConversationService(self.settings, persist=False)

    def test_femar_builds_progressive_dossier_with_real_attachment_metadata(self):
        result = self.service.message(
            ConversationMessageRequest(
                idempotency_key="femar-initial-0001",
                language="es",
                message=(
                    "Proyecto FEMAR: necesitamos cambiar o rehabilitar el sistema de control "
                    "de acceso existente. El sitio está en Guayaquil y tenemos documentación técnica."
                ),
                attachments=[
                    ConversationAttachment(
                        name="levantamiento.pdf",
                        media_type="application/pdf",
                        size_bytes=2048,
                    )
                ],
            )
        )

        self.assertEqual(result.dossier.customer.name, "FEMAR")
        self.assertEqual(result.dossier.site.location, "Guayaquil")
        self.assertTrue(result.dossier.confirmed_scope)
        self.assertTrue(result.dossier.risks)
        self.assertEqual(result.dossier.attachments[0].name, "levantamiento.pdf")
        self.assertEqual(result.runtime_label, "Codex-built / MCP runtime")

    def test_message_idempotency_replays_same_mission(self):
        request = ConversationMessageRequest(
            idempotency_key="same-message-0001",
            language="es",
            message="FEMAR requiere un sistema de control de acceso.",
        )
        first = self.service.message(request)
        second = self.service.message(request)

        self.assertEqual(first.mission_id, second.mission_id)
        self.assertEqual(first.dossier.progress, second.dossier.progress)
        self.assertTrue(second.idempotent_replay)

    def test_language_switch_translates_questions_and_reply(self):
        first = self.service.message(
            ConversationMessageRequest(
                idempotency_key="language-switch-0001",
                language="es",
                message="FEMAR necesita control de acceso.",
            )
        )
        english = self.service.get(first.mission_id, "en")

        self.assertEqual(english.language, "en")
        self.assertIn("national ID", english.dossier.questions[0])
        self.assertIn("case file", english.assistant_message)

    def test_quote_transition_approval_pdf_and_registered_delivery(self):
        initial = self.service.message(
            ConversationMessageRequest(
                idempotency_key="quote-flow-initial-0001",
                language="es",
                message=(
                    "FEMAR, cédula 1710034065. Proyecto de control de acceso en Guayaquil "
                    "para 2 puertas; debemos rehabilitar el sistema existente."
                ),
            )
        )
        drafted = self.service.message(
            ConversationMessageRequest(
                mission_id=initial.mission_id,
                idempotency_key="quote-flow-draft-0001",
                language="es",
                message="Preparar cotización editable.",
            )
        )
        self.assertEqual(drafted.dossier.quote.status, "needs_pricing")
        self.assertTrue(all(line.unit_price == 0 for line in drafted.dossier.quote.lines))

        priced = self.service.update_quote(
            initial.mission_id,
            QuoteUpdateRequest(
                idempotency_key="quote-flow-prices-0001",
                language="es",
                lines=[
                    EditableQuoteLine(line_id="assessment", description="Levantamiento", quantity=1, unit_price=100),
                    EditableQuoteLine(line_id="equipment", description="Equipos", quantity=2, unit_price=250),
                    EditableQuoteLine(line_id="implementation", description="Instalación", quantity=1, unit_price=300),
                ],
            ),
        )
        self.assertEqual(priced.dossier.quote.status, "draft")
        self.assertEqual(priced.dossier.quote.total, 900)

        with tempfile.TemporaryDirectory() as artifact_root:
            execution = QuoteExecutionService(
                Settings(
                    quoteops_artifact_root=artifact_root,
                    mongo_uri="mongodb://127.0.0.1:1/",
                    allow_production_writes=False,
                )
            )
            approved = self.service.approve(
                initial.mission_id,
                MissionApprovalRequest(
                    idempotency_key="quote-flow-approve-0001",
                    language="es",
                    approved_by="Rafael",
                    access_mode="judge",
                ),
                execution,
            )
            artifact = execution.artifact_path(approved["approval"]["artifact_id"])
            self.assertTrue(artifact.read_bytes().startswith(b"%PDF-1.4"))

            with self.assertRaisesRegex(ValueError, "approved_quote_locked"):
                self.service.update_quote(
                    initial.mission_id,
                    QuoteUpdateRequest(
                        idempotency_key="quote-flow-locked-update-0001",
                        language="es",
                        lines=priced.dossier.quote.lines,
                    ),
                )

            delivered = self.service.deliver(
                initial.mission_id,
                MissionDeliveryRequest(
                    idempotency_key="quote-flow-deliver-0001",
                    language="es",
                    channels=["download"],
                    access_mode="judge",
                ),
                execution,
            )
            self.assertEqual(delivered["delivery"]["status"], "registered")
            self.assertEqual(delivered["dossier"]["progress"], 100)


if __name__ == "__main__":
    unittest.main()
