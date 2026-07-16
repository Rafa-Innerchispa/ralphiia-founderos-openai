import unittest

from pydantic import ValidationError

from quoteops.contracts import (
    CatalogDraftReviewRequest,
    ConfigurationAlternativeUpsertRequest,
    ConfigurationLineInput,
    ConfigurationReviewRequest,
    ConversationMessageRequest,
    DecisionBriefUpdateRequest,
    EvidenceReviewRequest,
    MultimodalEvidenceCreateRequest,
    PackageSelectionRequest,
    SupplierOfferCreateRequest,
    SupplierOfferLineInput,
    TechnicalRequirementInput,
)
from quoteops.conversation import ConversationService
from quoteops.settings import Settings


class TestDecisionWorkspace(unittest.TestCase):
    def setUp(self):
        self.service = ConversationService(
            Settings(
                enable_openai=False,
                openai_api_key="",
                mongo_uri="mongodb://127.0.0.1:1/",
                ralfia_ops_base_url="http://127.0.0.1:1",
            ),
            persist=False,
        )
        self.initial = self.service.message(
            ConversationMessageRequest(
                idempotency_key="decision-start-0001",
                language="es",
                source_channel="chatgpt_mcp",
                message=(
                    "FEMAR, cedula 1710034065. Proyecto de control de acceso en Guayaquil "
                    "para 2 puertas."
                ),
            )
        )

    def _confirmed_source_line(self):
        evidence = self.service.record_extracted_evidence(
            self.initial.mission_id,
            MultimodalEvidenceCreateRequest(
                idempotency_key="decision-evidence-0001",
                language="es",
                source_file_name="ficha-confirmada.pdf",
                extraction_type="technical_document",
                extracted_by="manual",
                facts=[
                    {
                        "field": "credential_support",
                        "value": "QR, face, fingerprint, card",
                        "confidence": 1,
                    }
                ],
            ),
        )["evidence"]
        self.service.review_extracted_evidence(
            self.initial.mission_id,
            evidence["evidence_id"],
            EvidenceReviewRequest(
                idempotency_key="decision-evidence-review-0001",
                language="es",
                decision="confirm",
                reviewed_by="Rafael",
            ),
        )
        offer = self.service.add_supplier_offer(
            self.initial.mission_id,
            SupplierOfferCreateRequest(
                idempotency_key="decision-offer-0001",
                language="es",
                supplier_name="Proveedor verificado",
                supplier_reference="OF-DECISION-01",
                lines=[
                    SupplierOfferLineInput(
                        sku="TEST-QR-01",
                        description="Terminal de acceso para prueba",
                        quantity=1,
                        unit_cost=145,
                        package_codes=[],
                    )
                ],
            ),
        )
        draft = offer["catalog_drafts_created"][0]
        self.service.review_catalog_draft(
            self.initial.mission_id,
            draft["catalog_draft_id"],
            CatalogDraftReviewRequest(
                idempotency_key="decision-catalog-review-0001",
                language="es",
                decision="approve",
                reviewed_by="Rafael",
            ),
        )
        refreshed = self.service.get(self.initial.mission_id, "es")
        line = refreshed.dossier.supplier_offers[0].lines[0]
        return line.line_id, evidence["evidence_id"]

    def test_requirements_are_shared_idempotent_and_bilingual(self):
        request = DecisionBriefUpdateRequest(
            idempotency_key="decision-brief-0001",
            language="es",
            source_channel="whatsapp",
            channel_event_id="wa-requirements-1",
            updated_by="Rafael",
            requirements=[
                TechnicalRequirementInput(
                    category="legacy",
                    text="Los equipos heredados no se pueden reutilizar.",
                ),
                TechnicalRequirementInput(
                    category="credential",
                    text="La entrada principal requiere QR, rostro, huella y tarjeta.",
                ),
            ],
            open_questions=["Confirmar la cantidad final de puertas."],
        )
        first = self.service.update_decision_brief(self.initial.mission_id, request)
        replay = self.service.update_decision_brief(self.initial.mission_id, request)
        english = self.service.get(self.initial.mission_id, "en")

        self.assertEqual(first["dossier"]["decision_workspace"]["last_channel"], "whatsapp")
        self.assertEqual(len(first["dossier"]["decision_workspace"]["requirements"]), 2)
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(english.language, "en")
        self.assertIn("Confirmar la cantidad final de puertas.", english.dossier.questions)

    def test_alternative_uses_source_cost_requires_review_and_builds_quote(self):
        line_id, evidence_id = self._confirmed_source_line()
        alternative_result = self.service.upsert_configuration_alternative(
            self.initial.mission_id,
            ConfigurationAlternativeUpsertRequest(
                idempotency_key="decision-alternative-0001",
                language="es",
                source_channel="chatgpt_mcp",
                code="A",
                title="Alternativa de prueba",
                objective="Validar el canal, no recomendar una solución real.",
                lines=[
                    ConfigurationLineInput(
                        offer_line_id=line_id,
                        quantity=2,
                        role="main_entrance",
                        compatibility_status="verified",
                        evidence_ids=[evidence_id],
                    )
                ],
                coverage=["Entrada principal"],
                generated_by="chatgpt_mcp",
                selected_model="Modelo seleccionado por el operador",
                updated_by="Rafael",
            ),
        )
        alternative = alternative_result["alternative"]

        self.assertEqual(alternative["supplier_cost_total"], 290)
        self.assertEqual(alternative["status"], "ready_for_review")
        self.assertEqual(alternative_result["runtime_label"], "Codex-built / MCP runtime")
        with self.assertRaisesRegex(ValueError, "configuration_review_required"):
            self.service.select_package(
                self.initial.mission_id,
                PackageSelectionRequest(
                    idempotency_key="decision-select-before-review-0001",
                    language="es",
                    option_code="A",
                ),
            )
        self.service.review_configuration_alternative(
            self.initial.mission_id,
            "A",
            ConfigurationReviewRequest(
                idempotency_key="decision-alternative-review-0001",
                language="es",
                decision="approve",
                reviewed_by="Rafael",
            ),
        )
        quote = self.service.select_package(
            self.initial.mission_id,
            PackageSelectionRequest(
                idempotency_key="decision-select-after-review-0001",
                language="es",
                option_code="A",
            ),
        ).dossier.quote

        source_line = next(item for item in quote.lines if item.sku == "TEST-QR-01")
        self.assertEqual(source_line.unit_cost, 145)
        self.assertEqual(source_line.quantity, 2)
        self.assertEqual(quote.supplier_cost_total, 290)
        self.assertTrue(all(item.unit_price == 0 for item in quote.lines))

        edited = self.service.upsert_configuration_alternative(
            self.initial.mission_id,
            ConfigurationAlternativeUpsertRequest(
                idempotency_key="decision-alternative-edit-0001",
                language="es",
                source_channel="whatsapp",
                code="A",
                title="Alternativa de prueba editada",
                lines=[
                    ConfigurationLineInput(
                        offer_line_id=line_id,
                        quantity=1,
                        role="main_entrance",
                        compatibility_status="verified",
                        evidence_ids=[evidence_id],
                    )
                ],
                updated_by="Rafael",
            ),
        )
        self.assertIsNone(edited["dossier"]["quote"])
        self.assertEqual(edited["alternative"]["supplier_cost_total"], 145)

    def test_unknown_duplicate_and_caller_supplied_cost_are_rejected(self):
        with self.assertRaises(ValidationError):
            ConfigurationLineInput.model_validate(
                {"sku": "TEST-QR-01", "quantity": 1, "unit_cost": 0.01}
            )
        with self.assertRaisesRegex(ValueError, "configuration_item_not_found"):
            self.service.upsert_configuration_alternative(
                self.initial.mission_id,
                ConfigurationAlternativeUpsertRequest(
                    idempotency_key="decision-unknown-item-0001",
                    language="es",
                    code="B",
                    title="Alternativa inválida",
                    lines=[ConfigurationLineInput(sku="DOES-NOT-EXIST")],
                    updated_by="Rafael",
                ),
            )


if __name__ == "__main__":
    unittest.main()
