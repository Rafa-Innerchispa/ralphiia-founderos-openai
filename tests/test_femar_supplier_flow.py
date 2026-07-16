import tempfile
import unittest

from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.contracts import (
    CatalogDraftReviewRequest,
    ConversationMessageRequest,
    EditableQuoteLine,
    EvidenceReviewRequest,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    MultimodalEvidenceCreateRequest,
    PackageSelectionRequest,
    QuoteUpdateRequest,
    SupplierOfferCreateRequest,
    SupplierOfferLineInput,
)
from quoteops.conversation import ConversationService
from quoteops.settings import Settings


class TestFemarSupplierFlow(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            enable_openai=False,
            openai_api_key="",
            mongo_uri="mongodb://127.0.0.1:1/",
            ralfia_api_base="http://127.0.0.1:1",
            ralfia_ops_base_url="http://127.0.0.1:1",
        )
        self.service = ConversationService(self.settings, persist=False)
        self.initial = self.service.message(
            ConversationMessageRequest(
                idempotency_key="femar-supplier-start-0001",
                language="es",
                source_channel="chatgpt_mcp",
                message=(
                    "FEMAR, cedula 1710034065. Rehabilitar control de acceso en Guayaquil "
                    "para 2 puertas y preparar alternativas."
                ),
            )
        )

    def test_mission_creates_real_work_item_and_three_packages(self):
        dossier = self.initial.dossier

        self.assertTrue(dossier.work_item.task_id.startswith("task_"))
        self.assertEqual(dossier.work_item.source_channel, "chatgpt_mcp")
        self.assertEqual([item.code for item in dossier.options], ["A", "B", "C"])
        self.assertEqual([item.status for item in dossier.options], ["needs_costs"] * 3)
        self.assertEqual(dossier.timeline[0].kind, "mission_created")

    def test_multimodal_evidence_offer_package_quote_pdf_and_delivery(self):
        digest = "a" * 64
        self.service.record_attachment(
            self.initial.mission_id,
            {
                "name": "lista-proveedor.pdf",
                "media_type": "application/pdf",
                "size_bytes": 5120,
                "storage_id": "attachment_supplier_pdf",
                "sha256": digest,
                "status": "stored",
            },
            "es",
        )
        extraction_request = MultimodalEvidenceCreateRequest(
            idempotency_key="femar-extraction-0001",
            language="es",
            source_file_name="lista-proveedor.pdf",
            media_type="application/pdf",
            source_attachment_id="attachment_supplier_pdf",
            source_sha256=digest,
            extraction_type="supplier_price_list",
            extracted_by="chatgpt_mcp",
            extracted_text="Tarjeta AC-200, precio unitario USD 42.50",
            products=[
                {
                    "name": "Tarjeta de control AC-200",
                    "brand": "Marca visible",
                    "model": "AC-200",
                    "sku": "AC-200",
                    "confidence": 0.94,
                    "page": 1,
                }
            ],
            supplier_prices=[
                {
                    "supplier_name": "Proveedor autorizado",
                    "supplier_reference": "OF-2026-17",
                    "sku": "AC-200",
                    "description": "Tarjeta de control AC-200",
                    "quantity": 2,
                    "unit_cost": 42.5,
                    "confidence": 0.91,
                    "page": 1,
                }
            ],
        )
        extracted = self.service.record_extracted_evidence(
            self.initial.mission_id,
            extraction_request,
        )
        replayed = self.service.record_extracted_evidence(
            self.initial.mission_id,
            extraction_request,
        )

        self.assertEqual(extracted["evidence"]["status"], "needs_review")
        self.assertTrue(replayed["idempotent_replay"])
        evidence_id = extracted["evidence"]["evidence_id"]
        reviewed = self.service.review_extracted_evidence(
            self.initial.mission_id,
            evidence_id,
            EvidenceReviewRequest(
                idempotency_key="femar-review-0001",
                language="es",
                decision="confirm",
                reviewed_by="Rafael",
                notes="Valores cotejados con el PDF.",
            ),
        )
        self.assertEqual(reviewed["evidence"]["status"], "confirmed")

        offer_request = SupplierOfferCreateRequest(
            idempotency_key="femar-offer-0001",
            language="es",
            supplier_name="Proveedor autorizado",
            supplier_reference="OF-2026-17",
            attachment_storage_id="attachment_supplier_pdf",
            attachment_sha256=digest,
            lines=[
                SupplierOfferLineInput(
                    sku="AC-200",
                    description="Tarjeta de control AC-200",
                    quantity=2,
                    unit="unit",
                    unit_cost=42.5,
                    package_codes=["B", "C"],
                )
            ],
        )
        offer = self.service.add_supplier_offer(self.initial.mission_id, offer_request)
        replayed_offer = self.service.add_supplier_offer(self.initial.mission_id, offer_request)

        self.assertEqual(offer["supplier_offer"]["total_cost"], 85)
        self.assertIsNone(offer["supplier_offer"]["tax_included"])
        self.assertTrue(replayed_offer["idempotent_replay"])
        self.assertEqual(offer["catalog_drafts_created"][0]["status"], "draft")
        self.assertTrue(offer["catalog_drafts_created"][0]["approval_required"])
        draft_id = offer["catalog_drafts_created"][0]["catalog_draft_id"]
        review_request = CatalogDraftReviewRequest(
            idempotency_key="femar-catalog-review-0001",
            language="es",
            decision="approve",
            reviewed_by="Rafael",
            notes="Producto nuevo confirmado contra la oferta.",
        )
        catalog_review = self.service.review_catalog_draft(
            self.initial.mission_id, draft_id, review_request
        )
        catalog_replay = self.service.review_catalog_draft(
            self.initial.mission_id, draft_id, review_request
        )
        self.assertEqual(catalog_review["catalog_draft"]["status"], "approved_staging")
        self.assertTrue(catalog_review["catalog_draft"]["canonical_item_id"].startswith("catalogitem_"))
        self.assertTrue(catalog_replay["idempotent_replay"])

        selected = self.service.select_package(
            self.initial.mission_id,
            PackageSelectionRequest(
                idempotency_key="femar-select-c-0001",
                language="es",
                option_code="C",
            ),
        )
        quote = selected.dossier.quote
        supplier_line = next(line for line in quote.lines if line.sku == "AC-200")
        self.assertEqual(quote.selected_option_code, "C")
        self.assertEqual(quote.supplier_cost_total, 85)
        self.assertEqual(supplier_line.unit_price, 0)
        self.assertEqual(supplier_line.unit_cost, 42.5)

        priced_lines = [
            EditableQuoteLine(
                line_id=line.line_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=90 if line.sku == "AC-200" else 125,
            )
            for line in quote.lines
        ]
        priced = self.service.update_quote(
            self.initial.mission_id,
            QuoteUpdateRequest(
                idempotency_key="femar-selling-prices-0001",
                language="es",
                lines=priced_lines,
                tax_rate=0,
            ),
        )
        preserved = next(line for line in priced.dossier.quote.lines if line.sku == "AC-200")
        self.assertEqual(preserved.unit_cost, 42.5)
        self.assertEqual(preserved.unit_price, 90)
        self.assertEqual(preserved.price_source, "human_entered")
        self.assertEqual(priced.dossier.quote.status, "draft")

        with tempfile.TemporaryDirectory() as artifact_root:
            execution = QuoteExecutionService(
                Settings(
                    quoteops_artifact_root=artifact_root,
                    mongo_uri="mongodb://127.0.0.1:1/",
                    allow_production_writes=False,
                )
            )
            approved = self.service.approve(
                self.initial.mission_id,
                MissionApprovalRequest(
                    idempotency_key="femar-approve-0001",
                    language="es",
                    approved_by="Rafael",
                    access_mode="judge",
                ),
                execution,
            )
            pdf = execution.artifact_path(approved["approval"]["artifact_id"]).read_bytes()
            self.assertTrue(pdf.startswith(b"%PDF-1.4"))
            self.assertIn(b"Selected package: C", pdf)
            self.assertNotIn(b"42.50", pdf)

            delivered = self.service.deliver(
                self.initial.mission_id,
                MissionDeliveryRequest(
                    idempotency_key="femar-delivery-0001",
                    language="es",
                    channels=["download"],
                    access_mode="judge",
                ),
                execution,
            )
            self.assertEqual(delivered["delivery"]["status"], "registered")
            self.assertEqual(delivered["dossier"]["work_item"]["status"], "completed")

    def test_existing_catalog_sku_is_linked_without_duplicate_draft(self):
        self.service._catalog_index = lambda mission: (
            {"sku:ac-200": {"item_id": "inventory_existing_ac200", "sku": "AC-200"}},
            {"source": "read-only-test-catalog", "status": "ok", "items_read": 1},
        )
        result = self.service.add_supplier_offer(
            self.initial.mission_id,
            SupplierOfferCreateRequest(
                idempotency_key="femar-existing-item-0001",
                language="es",
                supplier_name="Proveedor autorizado",
                supplier_reference="OF-EXISTING-01",
                lines=[
                    SupplierOfferLineInput(
                        sku="AC-200",
                        description="Tarjeta de control AC-200",
                        quantity=1,
                        unit_cost=42.5,
                    )
                ],
            ),
        )

        self.assertEqual(result["catalog_drafts_created"], [])
        self.assertEqual(
            result["supplier_offer"]["lines"][0]["canonical_item_id"],
            "inventory_existing_ac200",
        )
        self.assertEqual(result["catalog_lookup"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
