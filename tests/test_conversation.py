import tempfile
import unittest

from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.conversation import ConversationService
from quoteops.contracts import (
    CommercialPartyProfile,
    CommercialPaymentTerms,
    CommercialProfileUpsertRequest,
    ConversationAttachment,
    ConversationMessageRequest,
    EditableQuoteLine,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    QuoteUpdateRequest,
    SupplierOfferCreateRequest,
    SupplierOfferLineInput,
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

    def test_commercial_profiles_are_idempotent_and_confirmed_credit_is_projected(self):
        mission = self.service.message(ConversationMessageRequest(idempotency_key="commercial-mission-0001", message="Need a sourced item."))
        profile_request = CommercialProfileUpsertRequest(
            idempotency_key="commercial-profile-0001", language="en",
            max_credit_premium_pct=4,
            profile=CommercialPartyProfile(party_role="supplier", party_id="supplier-1", party_name="Acme Supply", party_type="distributor", category="preferred", terms=CommercialPaymentTerms(payment_mode="net", credit_days=30, credit_status="current_confirmed", confirmation_source="signed terms", confirmed_date="2026-07-16")),
        )
        first = self.service.upsert_commercial_profile(mission.mission_id, profile_request)
        replay = self.service.upsert_commercial_profile(mission.mission_id, profile_request)
        self.assertFalse(first["idempotent_replay"])
        self.assertTrue(replay["idempotent_replay"])
        self.service.add_supplier_offer(mission.mission_id, SupplierOfferCreateRequest(
            idempotency_key="commercial-offer-0001", language="en", supplier_name="Acme Supply", supplier_party_id="supplier-1", supplier_reference="A-1", tax_amount=0, tax_status="known", shipping_cost=0, other_cost=0, availability="available", lines=[SupplierOfferLineInput(sku="X-1", description="Exact item", quantity=1, unit_cost=100)]
        ))
        results = self.service.get_sourcing_recommendations(mission.mission_id)["recommendations"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["best_confirmed_credit_offer"]["supplier_party_id"], "supplier-1")
        self.assertEqual(results[0]["recommended_offer"]["supplier_party_id"], "supplier-1")
        self.assertEqual(results[0]["policy_max_credit_premium_pct"], "4.0")

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
        self.assertEqual(result.dossier.project.kind, "access_control")
        self.assertEqual(result.dossier.site.location, "Guayaquil")
        self.assertTrue(result.dossier.confirmed_scope)
        self.assertTrue(result.dossier.risks)
        self.assertEqual(result.dossier.attachments[0].name, "levantamiento.pdf")
        self.assertEqual(result.runtime_label, "Codex-built / MCP runtime")

    def test_photo_workshop_uses_its_own_case_questions_options_and_quote(self):
        initial = self.service.message(
            ConversationMessageRequest(
                idempotency_key="photo-workshop-initial-0001",
                language="es",
                source_channel="chatgpt_mcp",
                customer_name="Joshua Degel",
                message=(
                    "Crear el expediente del taller fotográfico. Necesita organizar sus colecciones, "
                    "entregar archivos a clientes desde un servidor local, evaluar IA local y "
                    "organizar los cobros. No asumir precios ni infraestructura."
                ),
            )
        )

        self.assertEqual(initial.dossier.project.kind, "photo_workshop")
        self.assertEqual(initial.dossier.project.title, "Taller fotográfico de Joshua Degel")
        self.assertIn("Organizar colecciones", " ".join(initial.dossier.confirmed_scope))
        self.assertNotIn("puertas", " ".join(initial.dossier.questions).lower())
        self.assertEqual(initial.dossier.options[0].title, "Organización esencial")
        self.assertEqual(initial.dossier.work_item.title, initial.dossier.project.title)

        drafted = self.service.message(
            ConversationMessageRequest(
                mission_id=initial.mission_id,
                idempotency_key="photo-workshop-quote-0001",
                language="es",
                message="Preparar cotización editable sin inventar precios.",
            )
        )

        line_ids = {line.line_id for line in drafted.dossier.quote.lines}
        self.assertIn("photo_collections", line_ids)
        self.assertIn("photo_delivery", line_ids)
        self.assertIn("photo_billing", line_ids)
        self.assertTrue(all(line.unit_price == 0 for line in drafted.dossier.quote.lines))

    def test_photo_workshop_language_switch_and_progressive_facts(self):
        initial = self.service.message(
            ConversationMessageRequest(
                idempotency_key="photo-workshop-language-0001",
                language="es",
                customer_name="Joshua Degel",
                message="Laboratorio fotográfico con colecciones, entrega local, IA local y cobros.",
            )
        )
        continued = self.service.message(
            ConversationMessageRequest(
                mission_id=initial.mission_id,
                idempotency_key="photo-workshop-facts-0001",
                language="es",
                message=(
                    "Volumen del archivo: 4 TB. Servidor actual: NAS local. "
                    "Flujo de entrega: enlace privado por cliente."
                ),
            )
        )

        self.assertEqual(continued.dossier.project.facts["archive_volume"], "4 TB")
        self.assertEqual(continued.dossier.project.facts["current_server"], "NAS local")
        self.assertNotIn("Cuánto ocupa", " ".join(continued.dossier.questions))

        english = self.service.get(initial.mission_id, "en")
        self.assertEqual(english.dossier.project.title, "Joshua Degel photography workshop")
        self.assertIn("Organize photography", " ".join(english.dossier.confirmed_scope))
        self.assertIn("payments", " ".join(english.dossier.questions).lower())
        self.assertNotIn("doors", " ".join(english.dossier.questions).lower())

        quoted = self.service.message(
            ConversationMessageRequest(
                mission_id=initial.mission_id,
                idempotency_key="photo-workshop-language-quote-0001",
                language="es",
                message="Preparar cotización editable.",
            )
        )
        self.assertEqual(quoted.dossier.quote.lines[0].description, "Levantamiento del flujo y arquitectura")
        translated_quote = self.service.get(initial.mission_id, "en")
        self.assertEqual(translated_quote.dossier.quote.lines[0].description, "Workflow assessment and architecture")

    def test_general_project_never_inherits_femar_or_access_questions(self):
        result = self.service.message(
            ConversationMessageRequest(
                idempotency_key="general-project-initial-0001",
                language="es",
                customer_name="Cliente nuevo",
                message="Quiero organizar un nuevo proyecto y conversar para definir el alcance.",
            )
        )

        self.assertEqual(result.dossier.project.kind, "general")
        self.assertEqual(result.dossier.project.title, "Proyecto de Cliente nuevo")
        self.assertNotIn("FEMAR", result.dossier.work_item.title)
        self.assertNotIn("puertas", " ".join(result.dossier.questions).lower())

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
