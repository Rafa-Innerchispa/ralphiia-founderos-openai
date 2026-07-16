from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import re
from threading import RLock
from typing import Any
import unicodedata

import httpx
from pymongo import MongoClient

from quoteops.adapters.taxpayer_registry import TaxpayerRegistryError, normalize_ec_identifier
from quoteops.contracts import (
    CommercialPartyProfile,
    CommercialProfileUpsertRequest,
    ContextDossier,
    CatalogDraftReviewRequest,
    ConfigurationAlternative,
    ConfigurationAlternativeUpsertRequest,
    ConfigurationLine,
    ConfigurationReviewRequest,
    ConversationMessageRequest,
    ConversationReply,
    DecisionBriefUpdateRequest,
    DecisionWorkspace,
    DossierCustomer,
    DossierOption,
    DossierSite,
    EditableQuote,
    EditableQuoteLine,
    EvidenceReviewRequest,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    MultimodalEvidence,
    MultimodalEvidenceCreateRequest,
    PackageSelectionRequest,
    QuoteUpdateRequest,
    SupplierOffer,
    SupplierOfferCreateRequest,
)
from quoteops.supplier_sourcing import SupplierOffer as SourcingOffer, recommend_offer, normalize_name


TEXT = {
    "es": {
        "scope": "Cambio o rehabilitación del sistema de control de acceso",
        "assumption": "Se evaluará qué componentes existentes pueden conservarse antes de reemplazarlos.",
        "risk": "La compatibilidad del sistema existente debe verificarse en sitio.",
        "option_a": "Rehabilitación selectiva",
        "option_a_summary": "Conservar componentes compatibles y sustituir únicamente los puntos críticos.",
        "option_b": "Modernización híbrida",
        "option_b_summary": "Combinar componentes compatibles con una modernización controlada de los puntos prioritarios.",
        "option_c": "Renovación integral",
        "option_c_summary": "Diseñar una plataforma nueva con migración controlada del sistema actual.",
        "question_customer": "¿Cuál es la cédula o RUC del cliente?",
        "question_site": "¿Dónde está el sitio y cuántos accesos o puertas incluye?",
        "question_existing": "¿Qué marca, modelo y estado tiene el sistema actual?",
        "question_schedule": "¿Qué restricciones operativas y fecha objetivo debemos considerar?",
        "question_general_scope": "¿Qué resultado debe entregar el proyecto y cómo sabremos que quedó completo?",
        "question_general_site": "¿Dónde se ejecutará el proyecto y qué infraestructura existe hoy?",
        "general_option_a": "Alcance esencial",
        "general_option_a_summary": "Resolver el resultado prioritario con la menor complejidad validada.",
        "general_option_b": "Flujo automatizado",
        "general_option_b_summary": "Conectar el proceso principal con automatización y trazabilidad operativa.",
        "general_option_c": "Operación integrada",
        "general_option_c_summary": "Integrar el flujo completo por etapas, con controles y aprobación humana.",
        "photo_title": "Taller fotográfico de {customer}",
        "photo_summary": "Organización de colecciones, entrega privada, automatización local y gestión de cobros.",
        "photo_scope_collections": "Organizar colecciones fotográficas y sus metadatos.",
        "photo_scope_delivery": "Entregar archivos a clientes desde un servidor local con acceso controlado.",
        "photo_scope_ai": "Evaluar procesamiento o generación local con IA sin asumir capacidad de hardware.",
        "photo_scope_billing": "Organizar cobros y su seguimiento dentro del flujo del taller.",
        "photo_risk_server": "Capacidad, respaldo, conectividad y seguridad del servidor local deben verificarse antes de diseñar la entrega.",
        "photo_risk_ai": "Hardware disponible, privacidad y derechos de uso deben validarse antes de activar IA local.",
        "photo_question_volume": "¿Cuánto ocupa el archivo actual, cuánto crece al mes y qué formatos conserva?",
        "photo_question_server": "¿Qué servidor, almacenamiento, respaldo, red y conexión a internet existen hoy?",
        "photo_question_delivery": "¿Cómo entrega hoy cada colección, cuántos clientes atiende y qué permisos o vencimientos necesita?",
        "photo_question_billing": "¿Cómo registra cotizaciones, anticipos, saldos, pagos y comprobantes actualmente?",
        "photo_question_ai": "¿Qué tareas de IA local quiere automatizar y qué CPU o GPU tiene disponible?",
        "photo_question_schedule": "¿Cuál es el presupuesto, la prioridad y la fecha objetivo para la primera etapa?",
        "photo_option_a": "Organización esencial",
        "photo_option_a_summary": "Ordenar el archivo y habilitar entregas privadas con la automatización mínima necesaria.",
        "photo_option_b": "Flujo automatizado",
        "photo_option_b_summary": "Integrar ingreso, clasificación, entrega, notificaciones y seguimiento de cobros.",
        "photo_option_c": "Operación integrada",
        "photo_option_c_summary": "Orquestar el taller de extremo a extremo e incorporar IA local solo con infraestructura validada.",
        "reply_progress": "Ya incorporé la información al expediente. Para avanzar necesito: {questions}",
        "reply_ready": "El expediente tiene contexto suficiente. Puedes pedirme preparar la cotización editable.",
        "reply_design": "El espacio de decisión está actualizado. Las alternativas deben usar productos y costos con fuente real antes de revisión humana.",
        "reply_quote": "Preparé un borrador editable sin inventar precios. Completa los valores reales antes de enviarlo a aprobación.",
        "reply_approved": "La aprobación humana quedó registrada y el PDF real está listo.",
        "reply_delivered": "La entrega quedó registrada con su identificador y trazabilidad.",
        "task_next_input": "Completar identidad, sitio, alcance y evidencia de costos.",
        "general_task_next_input": "Completar identidad, alcance, infraestructura y evidencia de costos.",
        "photo_task_next_input": "Completar identidad, volumen, servidor, entrega, cobros y evidencia de costos.",
        "task_next_quote": "Seleccionar un paquete y confirmar precios de venta.",
        "task_next_design": "Completar y revisar las alternativas técnicas con evidencia real.",
        "task_next_approval": "Revisar la cotización y registrar aprobación humana.",
        "task_next_delivery": "Registrar la entrega aprobada.",
        "task_done": "Entrega registrada.",
    },
    "en": {
        "scope": "Replace or rehabilitate the access-control system",
        "assumption": "Existing components will be assessed for reuse before replacement.",
        "risk": "Compatibility with the existing system must be verified on site.",
        "option_a": "Selective rehabilitation",
        "option_a_summary": "Keep compatible components and replace only critical access points.",
        "option_b": "Hybrid modernization",
        "option_b_summary": "Combine compatible components with a controlled modernization of priority access points.",
        "option_c": "Full renewal",
        "option_c_summary": "Design a new platform with a controlled migration from the current system.",
        "question_customer": "What is the customer's national ID or RUC?",
        "question_site": "Where is the site and how many doors or access points are included?",
        "question_existing": "What are the brand, model, and condition of the current system?",
        "question_schedule": "Which operating constraints and target date should we consider?",
        "question_general_scope": "What must the project deliver, and how will we know it is complete?",
        "question_general_site": "Where will the project run, and what infrastructure is available today?",
        "general_option_a": "Essential scope",
        "general_option_a_summary": "Deliver the priority outcome with the least validated complexity.",
        "general_option_b": "Automated workflow",
        "general_option_b_summary": "Connect the primary process with automation and operational traceability.",
        "general_option_c": "Integrated operation",
        "general_option_c_summary": "Integrate the complete workflow in stages, with controls and human approval.",
        "photo_title": "{customer} photography workshop",
        "photo_summary": "Collection organization, private delivery, local automation, and payment management.",
        "photo_scope_collections": "Organize photography collections and their metadata.",
        "photo_scope_delivery": "Deliver files to clients from a local server with controlled access.",
        "photo_scope_ai": "Evaluate local AI processing or generation without assuming hardware capacity.",
        "photo_scope_billing": "Organize payment tracking within the workshop workflow.",
        "photo_risk_server": "Local server capacity, backup, connectivity, and security must be verified before designing delivery.",
        "photo_risk_ai": "Available hardware, privacy, and usage rights must be validated before enabling local AI.",
        "photo_question_volume": "How large is the current archive, how much does it grow monthly, and which formats are retained?",
        "photo_question_server": "Which server, storage, backup, network, and internet connection are available today?",
        "photo_question_delivery": "How is each collection delivered today, how many clients are served, and which permissions or expirations are needed?",
        "photo_question_billing": "How are quotes, deposits, balances, payments, and receipts tracked today?",
        "photo_question_ai": "Which local AI tasks should be automated, and which CPU or GPU is available?",
        "photo_question_schedule": "What are the budget, priority, and target date for the first stage?",
        "photo_option_a": "Essential organization",
        "photo_option_a_summary": "Organize the archive and enable private deliveries with the minimum required automation.",
        "photo_option_b": "Automated workflow",
        "photo_option_b_summary": "Integrate intake, classification, delivery, notifications, and payment tracking.",
        "photo_option_c": "Integrated operation",
        "photo_option_c_summary": "Orchestrate the workshop end to end and add local AI only after infrastructure is validated.",
        "reply_progress": "I added the information to the case file. To continue I need: {questions}",
        "reply_ready": "The case file has enough context. You can ask me to prepare the editable quote.",
        "reply_design": "The decision workspace is updated. Alternatives must use products and costs from real sources before human review.",
        "reply_quote": "I prepared an editable draft without inventing prices. Enter the real values before human approval.",
        "reply_approved": "Human approval was recorded and the real PDF is ready.",
        "reply_delivered": "Delivery was registered with its identifier and trace.",
        "task_next_input": "Complete identity, site, scope, and cost evidence.",
        "general_task_next_input": "Complete identity, scope, infrastructure, and cost evidence.",
        "photo_task_next_input": "Complete identity, volume, server, delivery, billing, and cost evidence.",
        "task_next_quote": "Select a package and confirm selling prices.",
        "task_next_design": "Complete and review the technical alternatives with real evidence.",
        "task_next_approval": "Review the quote and record human approval.",
        "task_next_delivery": "Register delivery of the approved quote.",
        "task_done": "Delivery registered.",
    },
}

QUOTE_LINE_TEXT = {
    "es": {
        "assessment": "Levantamiento técnico y diseño",
        "equipment": "Equipos y materiales de control de acceso",
        "implementation": "Instalación, configuración y capacitación",
        "photo_discovery": "Levantamiento del flujo y arquitectura",
        "photo_collections": "Organización de colecciones y metadatos",
        "photo_delivery": "Entrega privada desde servidor local",
        "photo_billing": "Automatización de cobros y seguimiento",
        "photo_ai": "IA local sujeta a validación de infraestructura",
        "photo_implementation": "Implementación, migración y capacitación",
    },
    "en": {
        "assessment": "Technical assessment and design",
        "equipment": "Access-control equipment and materials",
        "implementation": "Installation, configuration, and training",
        "photo_discovery": "Workflow assessment and architecture",
        "photo_collections": "Collection and metadata organization",
        "photo_delivery": "Private delivery from the local server",
        "photo_billing": "Billing and payment-tracking automation",
        "photo_ai": "Local AI subject to infrastructure validation",
        "photo_implementation": "Implementation, migration, and training",
    },
}


class ConversationService:
    """Deterministic, staging-safe mission state for the conversation-first flow."""

    def __init__(self, settings, *, persist: bool = True) -> None:
        self.settings = settings
        self.runtime_label = (
            f"OpenAI API / {settings.openai_model}"
            if settings.enable_openai and settings.openai_api_key
            else "Codex-built / MCP runtime"
        )
        self._lock = RLock()
        self._missions: dict[str, dict[str, Any]] = {}
        self._responses: dict[str, dict[str, Any]] = {}
        self.mongo_client = None
        self.collection = None
        self.operations = None
        self.tasks = None
        self.catalog = None
        self.commercial_profiles = None
        if persist:
            self._connect_mongo()

    @property
    def mongo_connected(self) -> bool:
        return self.collection is not None

    def _connect_mongo(self) -> None:
        client = None
        try:
            client = MongoClient(self.settings.mongo_uri, serverSelectionTimeoutMS=800)
            client.admin.command("ping")
            db = client[self.settings.quoteops_mongo_db]
            self.collection = db["conversation_missions"]
            self.operations = db["conversation_operations"]
            self.tasks = db["conversation_tasks"]
            self.catalog = db["conversation_catalog"]
            self.commercial_profiles = db["conversation_commercial_profiles"]
            self.collection.create_index("mission_id", unique=True)
            self.operations.create_index("idempotency_key", unique=True)
            self.tasks.create_index("task_id", unique=True)
            self.catalog.create_index("canonical_item_id", unique=True)
            self.commercial_profiles.create_index([("mission_id", 1), ("party_role", 1), ("profile_id", 1)], unique=True)
            self.mongo_client = client
        except Exception:
            if client is not None:
                client.close()

    def close(self) -> None:
        if self.mongo_client is not None:
            self.mongo_client.close()
            self.mongo_client = None

    def message(self, request: ConversationMessageRequest) -> ConversationReply:
        if not request.message and not request.attachments:
            raise ValueError("message_or_attachment_required")
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                replay["idempotent_replay"] = True
                return ConversationReply.model_validate(replay)

            mission_id = request.mission_id or self._mission_id(request.idempotency_key)
            mission = self._load_mission(mission_id) or self._new_mission(mission_id, request.language)
            mission["language"] = request.language
            self._refresh_project_profile(mission)
            if mission["dossier"].get("work_item"):
                mission["dossier"]["work_item"]["source_channel"] = request.source_channel
            workspace = mission["dossier"].setdefault("decision_workspace", {})
            workspace["last_channel"] = request.source_channel
            mission["messages"].append(
                {
                    "role": "user",
                    "text": request.message,
                    "attachments": [item.model_dump() for item in request.attachments],
                    "at": self._now(),
                }
            )
            self._add_event(
                mission,
                "message_received",
                f"Conversation input recorded from {request.source_channel}",
            )
            if request.channel_event_id:
                self._add_event(
                    mission,
                    "channel_event_received",
                    f"{request.source_channel} event {request.channel_event_id} recorded",
                )
            self._apply_message(mission, request)
            reply = self._reply(mission)
            mission["messages"].append({"role": "assistant", "text": reply, "at": self._now()})
            self._save_mission(mission)
            response = self._response(mission, reply)
            self._save_operation(request.idempotency_key, mission_id, "message", response)
            return ConversationReply.model_validate(response)

    def get(self, mission_id: str, language: str | None = None) -> ConversationReply:
        with self._lock:
            mission = self._load_mission(mission_id)
            if mission is None:
                raise KeyError("mission_not_found")
            if language in TEXT:
                mission["language"] = language
                self._refresh_project_profile(mission)
                self._refresh_questions(mission)
                self._refresh_options(mission)
                self._sync_work_item(mission)
            reply = self._reply(mission)
            return ConversationReply.model_validate(self._response(mission, reply))

    def update_quote(self, mission_id: str, request: QuoteUpdateRequest) -> ConversationReply:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                replay["idempotent_replay"] = True
                return ConversationReply.model_validate(replay)
            mission = self._require_mission(mission_id)
            current = EditableQuote.model_validate(mission["dossier"].get("quote") or {})
            if current.status in {"approved", "delivered"}:
                raise ValueError("approved_quote_locked")
            previous = {line.line_id: line for line in current.lines}
            merged_lines: list[EditableQuoteLine] = []
            for line in request.lines:
                old = previous.get(line.line_id)
                merged_lines.append(
                    line.model_copy(
                        update={
                            "unit_cost": old.unit_cost if old and not line.unit_cost else line.unit_cost,
                            "sku": line.sku or (old.sku if old else ""),
                            "kind": line.kind or (old.kind if old else ""),
                            "supplier_offer_id": line.supplier_offer_id or (old.supplier_offer_id if old else ""),
                            "price_source": "human_entered" if line.unit_price > 0 else "unpriced",
                        }
                    )
                )
            subtotal = round(sum(line.quantity * line.unit_price for line in merged_lines), 2)
            tax = round(subtotal * request.tax_rate, 2)
            quote = EditableQuote(
                status="draft" if subtotal > 0 and all(line.unit_price > 0 for line in merged_lines) else "needs_pricing",
                lines=merged_lines,
                subtotal=subtotal,
                tax=tax,
                total=round(subtotal + tax, 2),
                selected_option_code=current.selected_option_code,
                supplier_cost_total=round(sum(line.quantity * line.unit_cost for line in merged_lines), 2),
            )
            mission["language"] = request.language
            mission["dossier"]["quote"] = quote.model_dump()
            mission["phase"] = "quote"
            mission["dossier"]["progress"] = max(mission["dossier"]["progress"], 82)
            self._add_event(mission, "quote_priced", "Selling prices updated by a human")
            self._refresh_options(mission)
            self._sync_work_item(mission)
            self._save_mission(mission)
            response = self._response(mission, self._reply(mission))
            self._save_operation(request.idempotency_key, mission_id, "quote_update", response)
            return ConversationReply.model_validate(response)

    def add_supplier_offer(
        self,
        mission_id: str,
        request: SupplierOfferCreateRequest,
    ) -> dict[str, Any]:
        """Record exact supplier costs and create staging-only catalog drafts."""
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            offer_id = "offer_" + sha256(request.idempotency_key.encode()).hexdigest()[:18]
            if request.attachment_storage_id or request.attachment_sha256:
                evidence = mission["dossier"].get("attachments", [])
                matched = any(
                    (not request.attachment_storage_id or item.get("storage_id") == request.attachment_storage_id)
                    and (not request.attachment_sha256 or item.get("sha256") == request.attachment_sha256)
                    for item in evidence
                )
                if not matched:
                    raise ValueError("attachment_evidence_not_found")
            lines = []
            catalog_drafts = mission["dossier"].setdefault("catalog_drafts", [])
            catalog_index, catalog_lookup = self._catalog_index(mission)
            for index, raw in enumerate(request.lines):
                seed = f"{offer_id}:{index}:{raw.sku}:{raw.description}"
                line_id = "offerline_" + sha256(seed.encode()).hexdigest()[:16]
                catalog_key = self._catalog_key(raw.sku, raw.description)
                canonical = self._find_catalog_match(catalog_index, raw.sku, raw.description)
                draft = next(
                    (item for item in catalog_drafts if item.get("catalog_key") == catalog_key),
                    None,
                )
                if canonical is None and draft is None:
                    draft = {
                        "catalog_draft_id": "catalogdraft_" + sha256(catalog_key.encode()).hexdigest()[:18],
                        "catalog_key": catalog_key,
                        "sku": raw.sku,
                        "name": raw.description,
                        "kind": raw.kind,
                        "unit": raw.unit,
                        "status": "draft",
                        "source_offer_id": offer_id,
                        "source_line_id": line_id,
                        "canonical_item_id": "",
                        "approval_required": True,
                    }
                    catalog_drafts.append(draft)
                line_cost = round(raw.quantity * raw.unit_cost, 2)
                lines.append(
                    {
                        "line_id": line_id,
                        "sku": raw.sku,
                        "description": raw.description,
                        "kind": raw.kind,
                        "quantity": raw.quantity,
                        "unit": raw.unit,
                        "unit_cost": raw.unit_cost,
                        "line_cost": line_cost,
                        "package_codes": list(dict.fromkeys(raw.package_codes)),
                        "catalog_draft_id": draft["catalog_draft_id"] if draft else "",
                        "canonical_item_id": self._canonical_item_id(canonical),
                    }
                )
            evidence_status = "reference"
            if request.attachment_sha256:
                evidence_status = "reference_and_attachment" if request.supplier_reference else "attachment"
            offer = SupplierOffer(
                offer_id=offer_id,
                supplier_name=request.supplier_name,
                supplier_party_id=request.supplier_party_id,
                supplier_reference=request.supplier_reference,
                currency=request.currency,
                tax_included=request.tax_included,
                effective_at=request.effective_at,
                valid_until=request.valid_until,
                attachment_storage_id=request.attachment_storage_id,
                attachment_sha256=request.attachment_sha256,
                notes=request.notes,
                payment_mode=request.payment_mode,
                credit_days=request.credit_days,
                credit_status=request.credit_status,
                credit_source=request.credit_source,
                credit_confirmed_date=request.credit_confirmed_date,
                tax_amount=request.tax_amount,
                tax_status=request.tax_status,
                shipping_cost=request.shipping_cost,
                other_cost=request.other_cost,
                availability=request.availability,
                stock_quantity=request.stock_quantity,
                lead_time_days=request.lead_time_days,
                total_cost=round(sum(item["line_cost"] for item in lines), 2),
                evidence_status=evidence_status,
                lines=lines,
            ).model_dump()
            mission["language"] = request.language
            mission["dossier"].setdefault("supplier_offers", []).append(offer)
            self._refresh_sourcing_recommendations(mission)
            self._add_event(mission, "supplier_offer_added", f"Supplier evidence {offer_id} recorded")
            self._refresh_options(mission)
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            response = {
                **self._response(mission, self._reply(mission)),
                "supplier_offer": offer,
                "catalog_drafts_created": [
                    item for item in catalog_drafts if item.get("source_offer_id") == offer_id
                ],
                "catalog_lookup": catalog_lookup,
            }
            self._save_operation(request.idempotency_key, mission_id, "supplier_offer", response)
            return response

    def upsert_commercial_profile(self, mission_id: str, request: CommercialProfileUpsertRequest) -> dict[str, Any]:
        """Idempotently store commercial terms only in the mission and QuoteOps staging."""
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            profile = request.profile.model_dump()
            profile["profile_id"] = profile["profile_id"] or self._profile_id(profile)
            profiles = mission["dossier"].setdefault("commercial_profiles", [])
            profiles[:] = [item for item in profiles if item.get("profile_id") != profile["profile_id"]]
            profiles.append(profile)
            profiles.sort(key=lambda item: (item.get("party_role", ""), item.get("profile_id", "")))
            if profile["party_role"] == "customer":
                customer = mission["dossier"].setdefault("customer", {})
                if profile.get("party_name") and not customer.get("name"):
                    customer["name"] = profile["party_name"]
                if profile.get("party_id") and not customer.get("identifier"):
                    customer["identifier"] = profile["party_id"]
                    customer["source"] = customer.get("source") or "commercial_profile"
            if self.commercial_profiles is not None:
                self.commercial_profiles.replace_one(
                    {"mission_id": mission_id, "party_role": profile["party_role"], "profile_id": profile["profile_id"]},
                    {"mission_id": mission_id, **profile}, upsert=True,
                )
            mission["language"] = request.language
            if request.max_credit_premium_pct is not None:
                mission["dossier"]["sourcing_policy_max_credit_premium_pct"] = request.max_credit_premium_pct
            self._refresh_sourcing_recommendations(mission)
            self._save_mission(mission)
            response = {"ok": True, "mission_id": mission_id, "profile": profile, "dossier": mission["dossier"], "idempotent_replay": False}
            self._save_operation(request.idempotency_key, mission_id, "commercial_profile", response)
            return response

    def get_sourcing_recommendations(self, mission_id: str, language: str = "es") -> dict[str, Any]:
        with self._lock:
            mission = self._require_mission(mission_id)
            self._refresh_sourcing_recommendations(mission)
            return {"ok": True, "mission_id": mission_id, "language": language, "policy_max_credit_premium_pct": mission["dossier"].get("sourcing_policy_max_credit_premium_pct", 5), "recommendations": mission["dossier"].get("sourcing_recommendations", [])}

    def record_extracted_evidence(
        self,
        mission_id: str,
        request: MultimodalEvidenceCreateRequest,
    ) -> dict[str, Any]:
        """Persist model-extracted facts without treating them as confirmed business data."""
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            attachments = mission["dossier"].get("attachments", [])
            linked = False
            if request.source_attachment_id or request.source_sha256:
                linked = any(
                    (not request.source_attachment_id or item.get("storage_id") == request.source_attachment_id)
                    and (not request.source_sha256 or item.get("sha256") == request.source_sha256)
                    for item in attachments
                )
                if not linked:
                    raise ValueError("attachment_evidence_not_found")
            evidence_id = "evidence_" + sha256(request.idempotency_key.encode()).hexdigest()[:18]
            evidence = MultimodalEvidence(
                evidence_id=evidence_id,
                source_file_name=request.source_file_name,
                media_type=request.media_type,
                source_attachment_id=request.source_attachment_id,
                source_sha256=request.source_sha256,
                extraction_type=request.extraction_type,
                extracted_by=request.extracted_by,
                extracted_text=request.extracted_text,
                facts=request.facts,
                products=request.products,
                supplier_prices=request.supplier_prices,
                warnings=(
                    list(request.warnings)
                    if linked
                    else [*request.warnings, "original_source_not_archived"]
                ),
                status="needs_review" if linked else "source_unlinked",
                extracted_at=self._now(),
            ).model_dump()
            mission["language"] = request.language
            mission["dossier"].setdefault("extracted_evidence", []).append(evidence)
            self._add_event(mission, "evidence_extracted", f"Structured evidence {evidence_id} recorded")
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            response = {**self._response(mission, self._reply(mission)), "evidence": evidence}
            self._save_operation(request.idempotency_key, mission_id, "evidence_extract", response)
            return response

    def review_extracted_evidence(
        self,
        mission_id: str,
        evidence_id: str,
        request: EvidenceReviewRequest,
    ) -> dict[str, Any]:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            evidence = next(
                (
                    item
                    for item in mission["dossier"].get("extracted_evidence", [])
                    if item.get("evidence_id") == evidence_id
                ),
                None,
            )
            if evidence is None:
                raise ValueError("evidence_not_found")
            evidence.update(
                {
                    "status": "confirmed" if request.decision == "confirm" else "rejected",
                    "reviewed_by": request.reviewed_by,
                    "review_notes": request.notes,
                }
            )
            mission["language"] = request.language
            self._add_event(mission, "evidence_reviewed", f"Evidence {evidence_id} {evidence['status']}")
            self._save_mission(mission)
            response = {**self._response(mission, self._reply(mission)), "evidence": evidence}
            self._save_operation(request.idempotency_key, mission_id, "evidence_review", response)
            return response

    def review_catalog_draft(
        self,
        mission_id: str,
        catalog_draft_id: str,
        request: CatalogDraftReviewRequest,
    ) -> dict[str, Any]:
        """Approve a new item only inside the isolated QuoteOps staging catalog."""
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            draft = next(
                (
                    item
                    for item in mission["dossier"].get("catalog_drafts", [])
                    if item.get("catalog_draft_id") == catalog_draft_id
                ),
                None,
            )
            if draft is None:
                raise ValueError("catalog_draft_not_found")
            if request.decision == "approve":
                canonical_item_id = draft.get("canonical_item_id") or (
                    "catalogitem_" + sha256(catalog_draft_id.encode()).hexdigest()[:18]
                )
                draft.update(
                    {
                        "status": "approved_staging",
                        "canonical_item_id": canonical_item_id,
                        "approval_required": False,
                        "reviewed_by": request.reviewed_by,
                        "review_notes": request.notes,
                    }
                )
                for offer in mission["dossier"].get("supplier_offers", []):
                    for line in offer.get("lines", []):
                        if line.get("catalog_draft_id") == catalog_draft_id:
                            line["canonical_item_id"] = canonical_item_id
                if self.catalog is not None:
                    self.catalog.replace_one(
                        {"canonical_item_id": canonical_item_id},
                        {
                            "canonical_item_id": canonical_item_id,
                            "sku": draft.get("sku", ""),
                            "name": draft.get("name", ""),
                            "kind": draft.get("kind", "equipment"),
                            "unit": draft.get("unit", "unit"),
                            "source_mission_id": mission_id,
                            "source_offer_id": draft.get("source_offer_id", ""),
                            "approved_by": request.reviewed_by,
                            "created_at": self._now(),
                            "persistence_target": "quoteops_staging",
                        },
                        upsert=True,
                    )
            else:
                draft.update(
                    {
                        "status": "rejected",
                        "approval_required": False,
                        "reviewed_by": request.reviewed_by,
                        "review_notes": request.notes,
                    }
                )
            mission["language"] = request.language
            self._add_event(mission, "catalog_reviewed", f"Catalog draft {catalog_draft_id} {draft['status']}")
            self._refresh_sourcing_recommendations(mission)
            self._save_mission(mission)
            response = {**self._response(mission, self._reply(mission)), "catalog_draft": draft}
            self._save_operation(request.idempotency_key, mission_id, "catalog_review", response)
            return response

    def update_decision_brief(
        self,
        mission_id: str,
        request: DecisionBriefUpdateRequest,
    ) -> dict[str, Any]:
        """Update shared requirements without generating or selecting a proposal."""
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            workspace = self._workspace(mission)
            existing = [] if request.replace_requirements else list(workspace["requirements"])
            removals = set(request.remove_requirement_ids)
            existing = [item for item in existing if item.get("requirement_id") not in removals]
            by_id = {item["requirement_id"]: item for item in existing}
            by_key = {
                self._requirement_key(item.get("category", "other"), item.get("text", "")): item
                for item in existing
            }
            for raw in request.requirements:
                requirement_key = self._requirement_key(raw.category, raw.text)
                current = by_id.get(raw.requirement_id) if raw.requirement_id else by_key.get(requirement_key)
                requirement_id = raw.requirement_id or (
                    current.get("requirement_id")
                    if current
                    else "requirement_" + sha256(requirement_key.encode()).hexdigest()[:18]
                )
                value = {
                    **raw.model_dump(),
                    "requirement_id": requirement_id,
                    "source_channel": request.source_channel,
                    "source_event_id": request.channel_event_id,
                    "updated_by": request.updated_by,
                    "updated_at": self._now(),
                }
                if current:
                    by_key.pop(
                        self._requirement_key(
                            current.get("category", "other"),
                            current.get("text", ""),
                        ),
                        None,
                    )
                    position = existing.index(current)
                    existing[position] = value
                    by_id.pop(current.get("requirement_id", ""), None)
                else:
                    existing.append(value)
                by_id[requirement_id] = value
                by_key[requirement_key] = value

            questions = [] if request.replace_open_questions else list(workspace["open_questions"])
            for question in request.open_questions:
                clean = str(question or "").strip()
                if clean and clean not in questions:
                    questions.append(clean)
            requirements_changed = existing != workspace["requirements"]
            quote = mission["dossier"].get("quote") or {}
            if requirements_changed and quote.get("status") in {"approved", "delivered"}:
                raise ValueError("approved_quote_locked")
            workspace.update(
                {
                    "requirements": existing,
                    "open_questions": questions,
                    "last_channel": request.source_channel,
                    "selected_model": request.selected_model or workspace.get("selected_model", ""),
                    "revision": workspace.get("revision", 0) + 1,
                }
            )
            if requirements_changed:
                mission["dossier"]["quote"] = None
                for alternative in workspace["alternatives"]:
                    if alternative.get("status") in {"ready_for_review", "approved"}:
                        alternative["status"] = "needs_validation"
                        alternative["reviewed_by"] = ""
                        alternative["review_notes"] = ""
            mission["language"] = request.language
            self._refresh_decision_workspace(workspace)
            self._add_event(
                mission,
                "requirements_updated",
                f"Decision requirements updated from {request.source_channel}",
            )
            self._refresh_questions(mission)
            self._refresh_options(mission)
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            response = {**self._response(mission, self._reply(mission)), "decision_workspace": workspace}
            self._save_operation(request.idempotency_key, mission_id, "decision_brief", response)
            return response

    def upsert_configuration_alternative(
        self,
        mission_id: str,
        request: ConfigurationAlternativeUpsertRequest,
    ) -> dict[str, Any]:
        """Resolve every configuration line from mission evidence; caller costs are never accepted."""
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            quote = mission["dossier"].get("quote") or {}
            if quote.get("status") in {"approved", "delivered"}:
                raise ValueError("approved_quote_locked")
            workspace = self._workspace(mission)
            resolved_lines: list[ConfigurationLine] = []
            used_offer_lines: set[str] = set()
            for raw in request.lines:
                offer, line = self._resolve_offer_line(mission["dossier"], raw.offer_line_id, raw.sku)
                source_line_id = str(line.get("line_id") or "")
                if source_line_id in used_offer_lines:
                    raise ValueError("configuration_item_duplicated")
                used_offer_lines.add(source_line_id)
                evidence_ids = list(dict.fromkeys(raw.evidence_ids))
                evidence = self._resolve_evidence(mission["dossier"], evidence_ids)
                if raw.compatibility_status == "verified":
                    if not evidence_ids:
                        raise ValueError("configuration_evidence_required")
                    if any(item.get("status") != "confirmed" for item in evidence):
                        raise ValueError("configuration_evidence_not_confirmed")
                    if not line.get("canonical_item_id"):
                        raise ValueError("configuration_catalog_review_required")
                quantity = raw.quantity
                unit_cost = float(line.get("unit_cost") or 0)
                resolved_lines.append(
                    ConfigurationLine(
                        line_id="configline_"
                        + sha256(f"{request.code}:{source_line_id}:{raw.role}".encode()).hexdigest()[:18],
                        source_offer_id=str(offer.get("offer_id") or ""),
                        source_offer_line_id=source_line_id,
                        supplier_name=str(offer.get("supplier_name") or ""),
                        canonical_item_id=str(line.get("canonical_item_id") or ""),
                        sku=str(line.get("sku") or ""),
                        description=str(line.get("description") or ""),
                        kind=str(line.get("kind") or "equipment"),
                        unit=str(line.get("unit") or "unit"),
                        quantity=quantity,
                        unit_cost=unit_cost,
                        line_cost=round(quantity * unit_cost, 2),
                        role=raw.role,
                        compatibility_status=raw.compatibility_status,
                        rationale=raw.rationale,
                        evidence_ids=evidence_ids,
                    )
                )
            previous = next(
                (item for item in workspace["alternatives"] if item.get("code") == request.code),
                None,
            )
            needs_validation = bool(request.gaps) or any(
                line.compatibility_status != "verified" for line in resolved_lines
            )
            alternative = ConfigurationAlternative(
                code=request.code,
                title=request.title,
                objective=request.objective,
                status="needs_validation" if needs_validation else "ready_for_review",
                lines=resolved_lines,
                supplier_cost_total=round(sum(item.line_cost for item in resolved_lines), 2),
                coverage=request.coverage,
                gaps=request.gaps,
                assumptions=request.assumptions,
                risks=request.risks,
                generated_by=request.generated_by,
                selected_model=request.selected_model,
                updated_by=request.updated_by,
                updated_at=self._now(),
                revision=(int(previous.get("revision", 0)) + 1 if previous else 1),
            ).model_dump()
            if previous:
                workspace["alternatives"][workspace["alternatives"].index(previous)] = alternative
            else:
                workspace["alternatives"].append(alternative)
            mission["dossier"]["quote"] = None
            workspace.update(
                {
                    "last_channel": request.source_channel,
                    "selected_model": request.selected_model or workspace.get("selected_model", ""),
                    "revision": workspace.get("revision", 0) + 1,
                }
            )
            mission["language"] = request.language
            self._refresh_decision_workspace(workspace)
            self._add_event(
                mission,
                "alternative_updated",
                f"Alternative {request.code} updated from {request.source_channel}",
            )
            self._refresh_options(mission)
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            response = {**self._response(mission, self._reply(mission)), "alternative": alternative}
            self._save_operation(request.idempotency_key, mission_id, "alternative_upsert", response)
            return response

    def review_configuration_alternative(
        self,
        mission_id: str,
        code: str,
        request: ConfigurationReviewRequest,
    ) -> dict[str, Any]:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            workspace = self._workspace(mission)
            alternative = next(
                (item for item in workspace["alternatives"] if item.get("code") == code),
                None,
            )
            if alternative is None:
                raise ValueError("configuration_alternative_not_found")
            if request.decision == "approve":
                if alternative.get("status") != "ready_for_review":
                    raise ValueError("configuration_validation_required")
                alternative["status"] = "approved"
            else:
                alternative["status"] = "rejected"
                quote = mission["dossier"].get("quote") or {}
                if quote.get("selected_option_code") == code:
                    if quote.get("status") in {"approved", "delivered"}:
                        raise ValueError("approved_quote_locked")
                    mission["dossier"]["quote"] = None
            alternative.update(
                {
                    "reviewed_by": request.reviewed_by,
                    "review_notes": request.notes,
                    "updated_at": self._now(),
                }
            )
            workspace["revision"] = workspace.get("revision", 0) + 1
            mission["language"] = request.language
            self._refresh_decision_workspace(workspace)
            self._add_event(
                mission,
                "alternative_reviewed",
                f"Alternative {code} {alternative['status']} by {request.reviewed_by}",
            )
            self._refresh_options(mission)
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            response = {**self._response(mission, self._reply(mission)), "alternative": alternative}
            self._save_operation(request.idempotency_key, mission_id, "alternative_review", response)
            return response

    def select_package(
        self,
        mission_id: str,
        request: PackageSelectionRequest,
    ) -> ConversationReply:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                replay["idempotent_replay"] = True
                return ConversationReply.model_validate(replay)
            mission = self._require_mission(mission_id)
            current_quote = mission["dossier"].get("quote") or {}
            if current_quote.get("status") in {"approved", "delivered"}:
                raise ValueError("approved_quote_locked")
            mission["language"] = request.language
            quote = self._quote_for_package(mission["dossier"], request.language, request.option_code)
            mission["dossier"]["quote"] = quote.model_dump()
            mission["phase"] = "quote"
            mission["dossier"]["progress"] = max(mission["dossier"].get("progress", 0), 82)
            self._add_event(mission, "package_selected", f"Package {request.option_code} selected")
            self._refresh_options(mission)
            self._sync_work_item(mission)
            self._save_mission(mission)
            response = self._response(mission, self._reply(mission))
            self._save_operation(request.idempotency_key, mission_id, "package_select", response)
            return ConversationReply.model_validate(response)

    def approve(self, mission_id: str, request: MissionApprovalRequest, execution_service) -> dict[str, Any]:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            quote = EditableQuote.model_validate(mission["dossier"].get("quote") or {})
            customer = mission["dossier"]["customer"]
            if quote.status != "draft" or quote.total <= 0:
                raise ValueError("quote_pricing_required")
            if not customer.get("identifier"):
                raise ValueError("customer_identity_required")
            summary = "\n".join(
                f"{line.description}: {line.quantity:g} x USD {line.unit_price:.2f}"
                for line in quote.lines
            )
            result = execution_service.approve(
                {
                    "mission_id": mission_id,
                    "intake": {
                        "customer_name": customer.get("name") or customer["identifier"],
                        "contact": customer["identifier"],
                        "original_text": summary,
                    },
                    "approved_by": request.approved_by,
                    "mode": request.access_mode,
                    "quote": quote.model_dump(),
                }
            )
            if result.get("status") != "approved":
                raise ValueError("approval_blocked")
            quote.status = "approved"
            quote.approval_id = result["approval_id"]
            quote.artifact_id = result["artifact_id"]
            quote.pdf_url = result["pdf_url"]
            mission["language"] = request.language
            mission["phase"] = "approval"
            mission["dossier"]["quote"] = quote.model_dump()
            mission["dossier"]["progress"] = 94
            self._add_event(mission, "quote_approved", f"Human approval {result['approval_id']} recorded")
            self._sync_work_item(mission)
            mission["messages"].append(
                {"role": "assistant", "text": TEXT[request.language]["reply_approved"], "at": self._now()}
            )
            self._save_mission(mission)
            response = {**self._response(mission, TEXT[request.language]["reply_approved"]), "approval": result}
            self._save_operation(request.idempotency_key, mission_id, "approve", response)
            return response

    def deliver(self, mission_id: str, request: MissionDeliveryRequest, execution_service) -> dict[str, Any]:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                return {**replay, "idempotent_replay": True}
            mission = self._require_mission(mission_id)
            quote = EditableQuote.model_validate(mission["dossier"].get("quote") or {})
            if quote.status != "approved" or not quote.approval_id:
                raise ValueError("approval_required")
            result = execution_service.deliver(
                {
                    "approval_id": quote.approval_id,
                    "channels": request.channels,
                    "mode": request.access_mode,
                }
            )
            if result.get("status") not in {"registered", "queued"}:
                raise ValueError("delivery_blocked")
            quote.status = "delivered"
            quote.delivery_id = result["delivery_id"]
            mission["language"] = request.language
            mission["phase"] = "delivery"
            mission["dossier"]["quote"] = quote.model_dump()
            mission["dossier"]["progress"] = 100
            self._add_event(mission, "delivery_registered", f"Delivery {result['delivery_id']} registered")
            self._sync_work_item(mission)
            mission["messages"].append(
                {"role": "assistant", "text": TEXT[request.language]["reply_delivered"], "at": self._now()}
            )
            self._save_mission(mission)
            response = {**self._response(mission, TEXT[request.language]["reply_delivered"]), "delivery": result}
            self._save_operation(request.idempotency_key, mission_id, "deliver", response)
            return response

    def set_customer_identity(
        self,
        mission_id: str,
        *,
        identifier: str,
        identifier_type: str,
        name: str,
        verification_status: str,
        source: str,
    ) -> None:
        if not mission_id:
            return
        with self._lock:
            mission = self._load_mission(mission_id)
            if mission is None:
                return
            mission["dossier"]["customer"].update(
                {
                    "identifier": identifier,
                    "identifier_type": identifier_type,
                    "name": name or mission["dossier"]["customer"].get("name", ""),
                    "verification_status": verification_status,
                    "source": source,
                }
            )
            self._add_event(mission, "customer_verified", f"Identity verified through {source}")
            self._refresh_questions(mission)
            self._set_progress_and_phase(mission)
            self._save_mission(mission)

    def record_attachment(self, mission_id: str, attachment: dict[str, Any], language: str) -> ConversationReply:
        with self._lock:
            mission = self._require_mission(mission_id)
            mission["language"] = language if language in TEXT else mission["language"]
            items = mission["dossier"]["attachments"]
            existing = next((item for item in items if item.get("name") == attachment.get("name")), None)
            if existing is not None:
                existing.update(attachment)
            else:
                items.append(attachment)
            self._add_event(mission, "attachment_stored", f"Attachment {attachment.get('storage_id') or attachment.get('name')} stored")
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            return ConversationReply.model_validate(self._response(mission, self._reply(mission)))

    def _apply_message(self, mission: dict[str, Any], request: ConversationMessageRequest) -> None:
        text = request.message
        lower = text.lower()
        dossier = mission["dossier"]
        if request.customer_name:
            dossier["customer"]["name"] = request.customer_name
        if re.search(r"\bfemar\b", lower):
            dossier["customer"]["name"] = "FEMAR"
        generic_name = re.search(r"(?:cliente|customer)\s*[:\-]\s*([^\n,.]{2,80})", text, re.IGNORECASE)
        if generic_name and not dossier["customer"]["name"]:
            dossier["customer"]["name"] = generic_name.group(1).strip()

        project = dossier.setdefault("project", {})
        detected_kind = self._detect_project_kind(text)
        if detected_kind != "general" or not project.get("kind"):
            project["kind"] = detected_kind

        for candidate in re.findall(r"(?<!\d)(?:\d{13}|\d{10})(?!\d)", text):
            try:
                identifier, identifier_type = normalize_ec_identifier(candidate)
            except TaxpayerRegistryError:
                continue
            dossier["customer"].update(
                {
                    "identifier": identifier,
                    "identifier_type": identifier_type,
                    "verification_status": "locally_valid",
                    "source": "local_validation",
                }
            )
            break

        access_terms = ("control de acceso", "sistema de acceso", "access control", "access-control")
        if any(term in lower for term in access_terms):
            self._append_unique(dossier["confirmed_scope"], TEXT[request.language]["scope"])
        if any(term in lower for term in ("rehabil", "conservar", "existente", "existing", "reuse")):
            self._append_unique(dossier["assumptions"], TEXT[request.language]["assumption"])
            self._append_unique(dossier["risks"], TEXT[request.language]["risk"])

        if project.get("kind") == "photo_workshop":
            normalized_lower = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
            photo_scope_terms = {
                "photo_scope_collections": ("coleccion", "archivo fotograf", "organizar", "catalog", "collection", "photo archive"),
                "photo_scope_delivery": ("entrega", "mandar los archivos", "servidor local", "deliver", "client files", "local server"),
                "photo_scope_ai": ("ia local", "inteligencia artificial local", "generacion local", "local ai", "local generation"),
                "photo_scope_billing": ("cobro", "pago", "factur", "billing", "payment", "collection tracking"),
            }
            for text_key, terms in photo_scope_terms.items():
                if any(term in normalized_lower for term in terms):
                    self._append_unique(dossier["confirmed_scope"], TEXT[request.language][text_key])
            if any(term in normalized_lower for term in ("servidor local", "local server", "entrega", "deliver")):
                self._append_unique(dossier["risks"], TEXT[request.language]["photo_risk_server"])
            if any(term in normalized_lower for term in ("ia local", "local ai", "generacion local", "local generation")):
                self._append_unique(dossier["risks"], TEXT[request.language]["photo_risk_ai"])
            self._extract_photo_facts(project, text)

        location = re.search(
            r"(?:ubicaci[oó]n|sitio|location|site)\s*[:\-]\s*([^\n.]{2,120})",
            text,
            re.IGNORECASE,
        )
        if location:
            dossier["site"]["location"] = location.group(1).strip()
        elif "guayaquil" in lower:
            dossier["site"]["location"] = "Guayaquil"
        elif "quito" in lower:
            dossier["site"]["location"] = "Quito"
        access_count = re.search(r"(\d{1,4})\s*(?:puertas?|accesos?|doors?|access points?)", lower)
        if access_count:
            dossier["site"]["access_points"] = access_count.group(1)

        existing_names = {item["name"] for item in dossier["attachments"]}
        for attachment in request.attachments:
            if attachment.name not in existing_names:
                dossier["attachments"].append(attachment.model_dump())
                existing_names.add(attachment.name)

        if dossier["confirmed_scope"]:
            self._refresh_options(mission)
        if any(word in lower for word in ("cotiz", "borrador", "quote", "proposal")) and dossier["confirmed_scope"]:
            dossier["quote"] = dossier.get("quote") or self._quote_draft(dossier, request.language).model_dump()
        self._refresh_project_profile(mission)
        self._refresh_questions(mission)
        self._set_progress_and_phase(mission)

    @staticmethod
    def _detect_project_kind(text: str) -> str:
        lower = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
        if any(
            term in lower
            for term in (
                "taller fotograf",
                "laboratorio fotograf",
                "archivo fotograf",
                "photography workshop",
                "photo workshop",
                "photo lab",
                "photography studio",
            )
        ):
            return "photo_workshop"
        if any(term in lower for term in ("control de acceso", "sistema de acceso", "access control", "access-control")):
            return "access_control"
        return "general"

    @staticmethod
    def _project_kind(dossier: dict[str, Any]) -> str:
        return str((dossier.get("project") or {}).get("kind") or "general")

    def _refresh_project_profile(self, mission: dict[str, Any]) -> None:
        dossier = mission["dossier"]
        project = dossier.setdefault("project", {})
        project.setdefault("facts", {})
        kind = str(project.get("kind") or "general")
        if kind == "general":
            known_text = " ".join(
                [
                    *dossier.get("confirmed_scope", []),
                    str((dossier.get("work_item") or {}).get("title") or ""),
                ]
            )
            inferred = self._detect_project_kind(known_text)
            if inferred != "general":
                kind = inferred
                project["kind"] = inferred
        customer = dossier.get("customer", {}).get("name", "").strip()
        language = mission["language"]
        if kind == "photo_workshop":
            self._translate_known_values(
                dossier["confirmed_scope"],
                (
                    "photo_scope_collections",
                    "photo_scope_delivery",
                    "photo_scope_ai",
                    "photo_scope_billing",
                ),
                language,
            )
            self._translate_known_values(
                dossier["risks"],
                ("photo_risk_server", "photo_risk_ai"),
                language,
            )
            project["title"] = (
                TEXT[language]["photo_title"].format(customer=customer)
                if customer
                else ("Taller fotográfico" if language == "es" else "Photography workshop")
            )
            project["summary"] = TEXT[language]["photo_summary"]
        elif kind == "access_control":
            self._translate_known_values(dossier["confirmed_scope"], ("scope",), language)
            self._translate_known_values(dossier["assumptions"], ("assumption",), language)
            self._translate_known_values(dossier["risks"], ("risk",), language)
            label = "Control de acceso" if language == "es" else "Access control"
            project["title"] = f"{customer} · {label}" if customer else label
            project["summary"] = TEXT[language]["scope"]
        else:
            project["title"] = (
                f"Proyecto de {customer}" if language == "es" and customer else
                f"{customer} project" if customer else
                "Nuevo proyecto" if language == "es" else "New project"
            )
            project["summary"] = ""
        work_item = dossier.get("work_item")
        if work_item:
            work_item["title"] = project["title"]
        self._translate_quote_lines(dossier, language)

    @staticmethod
    def _translate_known_values(items: list[str], keys: tuple[str, ...], language: str) -> None:
        for key in keys:
            variants = {TEXT["es"][key], TEXT["en"][key]}
            if not any(item in variants for item in items):
                continue
            items[:] = [item for item in items if item not in variants]
            items.append(TEXT[language][key])

    @staticmethod
    def _translate_quote_lines(dossier: dict[str, Any], language: str) -> None:
        quote = dossier.get("quote") or {}
        for line in quote.get("lines", []):
            description = QUOTE_LINE_TEXT[language].get(line.get("line_id", ""))
            if description:
                line["description"] = description

    @staticmethod
    def _extract_photo_facts(project: dict[str, Any], text: str) -> None:
        facts = project.setdefault("facts", {})
        patterns = {
            "archive_volume": r"(?:volumen(?: del archivo)?|archivo actual|archive size)\s*[:\-]\s*([^\n.]{2,160})",
            "current_server": r"(?:servidor(?: actual)?|almacenamiento(?: actual)?|current server|current storage)\s*[:\-]\s*([^\n.]{2,160})",
            "delivery_workflow": r"(?:entrega(?: actual)?|flujo de entrega|delivery workflow)\s*[:\-]\s*([^\n.]{2,160})",
            "billing_workflow": r"(?:cobros?(?: actuales)?|facturaci[oó]n(?: actual)?|billing workflow)\s*[:\-]\s*([^\n.]{2,160})",
            "local_ai_goal": r"(?:ia local|objetivo de ia|local ai)\s*[:\-]\s*([^\n.]{2,160})",
            "budget_and_schedule": r"(?:presupuesto y fecha|budget and schedule)\s*[:\-]\s*([^\n.]{2,160})",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                facts[key] = match.group(1).strip()

    def _quote_draft(self, dossier: dict[str, Any], language: str) -> EditableQuote:
        if self._project_kind(dossier) == "photo_workshop":
            descriptions = QUOTE_LINE_TEXT[language]
            return EditableQuote(
                status="needs_pricing",
                lines=[
                    EditableQuoteLine(line_id=line_id, description=descriptions[line_id], quantity=1, unit_price=0)
                    for line_id in (
                        "photo_discovery",
                        "photo_collections",
                        "photo_delivery",
                        "photo_billing",
                        "photo_ai",
                        "photo_implementation",
                    )
                ],
            )
        access_points = int(dossier["site"].get("access_points") or 1)
        descriptions = QUOTE_LINE_TEXT[language]
        return EditableQuote(
            status="needs_pricing",
            lines=[
                EditableQuoteLine(line_id="assessment", description=descriptions["assessment"], quantity=1, unit_price=0),
                EditableQuoteLine(line_id="equipment", description=descriptions["equipment"], quantity=access_points, unit_price=0),
                EditableQuoteLine(line_id="implementation", description=descriptions["implementation"], quantity=1, unit_price=0),
            ],
        )

    def _quote_for_package(
        self,
        dossier: dict[str, Any],
        language: str,
        option_code: str,
    ) -> EditableQuote:
        base = self._quote_draft(dossier, language)
        workspace = dossier.get("decision_workspace") or {}
        alternative = next(
            (item for item in workspace.get("alternatives", []) if item.get("code") == option_code),
            None,
        )
        if alternative:
            if alternative.get("status") != "approved":
                raise ValueError("configuration_review_required")
            configuration_lines = [
                EditableQuoteLine(
                    line_id=line["line_id"],
                    description=line["description"],
                    quantity=line["quantity"],
                    unit_price=0,
                    unit_cost=line["unit_cost"],
                    sku=line.get("sku", ""),
                    kind=line.get("kind", "equipment"),
                    supplier_offer_id=line.get("source_offer_id", ""),
                    price_source="unpriced",
                )
                for line in alternative.get("lines", [])
            ]
            lines = [base.lines[0], *configuration_lines, base.lines[-1]]
            return EditableQuote(
                status="needs_pricing",
                lines=lines,
                selected_option_code=option_code,
                supplier_cost_total=round(sum(line.quantity * line.unit_cost for line in lines), 2),
            )
        offer_lines: list[EditableQuoteLine] = []
        for offer in dossier.get("supplier_offers", []):
            for line in offer.get("lines", []):
                if option_code not in line.get("package_codes", []):
                    continue
                offer_lines.append(
                    EditableQuoteLine(
                        line_id=line["line_id"],
                        description=line["description"],
                        quantity=line["quantity"],
                        unit_price=0,
                        unit_cost=line["unit_cost"],
                        sku=line.get("sku", ""),
                        kind=line.get("kind", "equipment"),
                        supplier_offer_id=offer["offer_id"],
                        price_source="unpriced",
                    )
                )
        lines = [base.lines[0], *offer_lines, base.lines[-1]] if offer_lines else base.lines
        return EditableQuote(
            status="needs_pricing",
            lines=lines,
            selected_option_code=option_code,
            supplier_cost_total=round(sum(line.quantity * line.unit_cost for line in lines), 2),
        )

    def _refresh_options(self, mission: dict[str, Any]) -> None:
        dossier = mission["dossier"]
        workspace = self._workspace(mission)
        alternatives = {item.get("code"): item for item in workspace["alternatives"]}
        if not dossier.get("confirmed_scope") and not alternatives:
            dossier["options"] = []
            return
        language = mission["language"]
        existing_quote = dossier.get("quote") or {}
        selected = existing_quote.get("selected_option_code", "")
        options = []
        kind = self._project_kind(dossier)
        option_keys = (
            (
                ("A", "photo_option_a", "photo_option_a_summary"),
                ("B", "photo_option_b", "photo_option_b_summary"),
                ("C", "photo_option_c", "photo_option_c_summary"),
            )
            if kind == "photo_workshop"
            else (
                ("A", "general_option_a", "general_option_a_summary"),
                ("B", "general_option_b", "general_option_b_summary"),
                ("C", "general_option_c", "general_option_c_summary"),
            )
            if kind == "general"
            else (
                ("A", "option_a", "option_a_summary"),
                ("B", "option_b", "option_b_summary"),
                ("C", "option_c", "option_c_summary"),
            )
        )
        for code, title_key, summary_key in option_keys:
            alternative = alternatives.get(code)
            if alternative:
                alt_status = alternative.get("status", "needs_validation")
                status = {
                    "draft": "needs_validation",
                    "needs_validation": "needs_validation",
                    "ready_for_review": "ready_for_review",
                    "approved": "approved",
                    "rejected": "needs_validation",
                }[alt_status]
                if selected == code and existing_quote.get("status") in {
                    "draft",
                    "approved",
                    "delivered",
                }:
                    status = "ready"
                evidence = {
                    evidence_id
                    for line in alternative.get("lines", [])
                    for evidence_id in line.get("evidence_ids", [])
                }
                options.append(
                    DossierOption(
                        code=code,
                        title=alternative.get("title") or TEXT[language][title_key],
                        summary=alternative.get("objective") or TEXT[language][summary_key],
                        status=status,
                        line_ids=[line["line_id"] for line in alternative.get("lines", [])],
                        supplier_cost_total=alternative.get("supplier_cost_total", 0),
                        selling_total=existing_quote.get("total", 0) if selected == code else 0,
                        evidence_count=len(evidence),
                    ).model_dump()
                )
                continue
            related = []
            evidence = set()
            for offer in dossier.get("supplier_offers", []):
                for line in offer.get("lines", []):
                    if code in line.get("package_codes", []):
                        related.append(line)
                        evidence.add(offer.get("offer_id"))
            selling_total = existing_quote.get("total", 0) if selected == code else 0
            if selected == code and existing_quote.get("status") in {"draft", "approved", "delivered"}:
                status = "ready"
            elif related:
                status = "needs_pricing"
            else:
                status = "needs_costs"
            options.append(
                DossierOption(
                    code=code,
                    title=TEXT[language][title_key],
                    summary=TEXT[language][summary_key],
                    status=status,
                    line_ids=[line["line_id"] for line in related],
                    supplier_cost_total=round(sum(line["line_cost"] for line in related), 2),
                    selling_total=selling_total,
                    evidence_count=len(evidence),
                ).model_dump()
            )
        dossier["options"] = options

    def _refresh_questions(self, mission: dict[str, Any]) -> None:
        language = mission["language"]
        dossier = mission["dossier"]
        questions = []
        if not dossier["customer"].get("identifier"):
            questions.append(TEXT[language]["question_customer"])
        kind = self._project_kind(dossier)
        if kind == "photo_workshop":
            facts = (dossier.get("project") or {}).get("facts", {})
            for fact_key, question_key in (
                ("archive_volume", "photo_question_volume"),
                ("current_server", "photo_question_server"),
                ("delivery_workflow", "photo_question_delivery"),
                ("billing_workflow", "photo_question_billing"),
                ("local_ai_goal", "photo_question_ai"),
                ("budget_and_schedule", "photo_question_schedule"),
            ):
                if not facts.get(fact_key):
                    questions.append(TEXT[language][question_key])
        elif kind == "access_control":
            if not dossier["site"].get("location") or not dossier["site"].get("access_points"):
                questions.append(TEXT[language]["question_site"])
            if dossier["confirmed_scope"] and not dossier["assumptions"]:
                questions.append(TEXT[language]["question_existing"])
            if dossier["confirmed_scope"]:
                questions.append(TEXT[language]["question_schedule"])
        else:
            if not dossier["site"].get("location"):
                questions.append(TEXT[language]["question_general_site"])
            if not dossier["confirmed_scope"]:
                questions.append(TEXT[language]["question_general_scope"])
        for question in self._workspace(mission)["open_questions"]:
            if question not in questions:
                questions.append(question)
        dossier["questions"] = questions

    def _set_progress_and_phase(self, mission: dict[str, Any]) -> None:
        dossier = mission["dossier"]
        score = 10
        score += 12 if dossier["customer"].get("name") else 0
        score += 16 if dossier["customer"].get("identifier") else 0
        score += 22 if dossier["confirmed_scope"] else 0
        if self._project_kind(dossier) == "photo_workshop":
            score += min(26, len((dossier.get("project") or {}).get("facts", {})) * 5)
        else:
            score += 14 if dossier["site"].get("location") else 0
            score += 12 if dossier["site"].get("access_points") else 0
        score += 6 if dossier["attachments"] else 0
        score += 3 if dossier.get("extracted_evidence") else 0
        score += 4 if dossier.get("supplier_offers") else 0
        workspace = self._workspace(mission)
        score += 4 if workspace["requirements"] else 0
        score += 5 if workspace["alternatives"] else 0
        score += 8 if dossier.get("quote") else 0
        dossier["progress"] = min(score, 90 if not dossier.get("quote") else 92)
        quote = dossier.get("quote") or {}
        if quote.get("status") == "delivered":
            mission["phase"] = "delivery"
        elif quote.get("status") == "approved":
            mission["phase"] = "approval"
        elif quote:
            mission["phase"] = "quote"
        elif workspace["requirements"]:
            mission["phase"] = "design"
        elif not dossier["customer"].get("identifier"):
            mission["phase"] = "identity"
        elif dossier["confirmed_scope"]:
            mission["phase"] = "scope"
        else:
            mission["phase"] = "discovery"
        self._sync_work_item(mission)

    def _reply(self, mission: dict[str, Any]) -> str:
        language = mission["language"]
        dossier = mission["dossier"]
        quote = dossier.get("quote") or {}
        if quote.get("status") == "delivered":
            return TEXT[language]["reply_delivered"]
        if quote.get("status") == "approved":
            return TEXT[language]["reply_approved"]
        if quote:
            return TEXT[language]["reply_quote"]
        if self._workspace(mission)["requirements"]:
            return TEXT[language]["reply_design"]
        if dossier["questions"]:
            return TEXT[language]["reply_progress"].format(questions=" ".join(dossier["questions"][:3]))
        return TEXT[language]["reply_ready"]

    def _response(self, mission: dict[str, Any], reply: str) -> dict[str, Any]:
        return ConversationReply(
            mission_id=mission["mission_id"],
            language=mission["language"],
            phase=mission["phase"],
            assistant_message=reply,
            dossier=ContextDossier.model_validate(mission["dossier"]),
            history=[
                {"role": item["role"], "text": item.get("text", ""), "at": item["at"]}
                for item in mission["messages"]
                if item.get("role") in {"user", "assistant"}
            ],
            runtime_label=self.runtime_label,
        ).model_dump()

    def _new_mission(self, mission_id: str, language: str) -> dict[str, Any]:
        now = self._now()
        task_id = "task_" + sha256(mission_id.encode()).hexdigest()[:18]
        mission = {
            "mission_id": mission_id,
            "language": language,
            "phase": "discovery",
            "dossier": ContextDossier(
                customer=DossierCustomer(),
                site=DossierSite(),
                progress=10,
                work_item={
                    "task_id": task_id,
                    "correlation_id": mission_id,
                    "title": "Nuevo proyecto" if language == "es" else "New project",
                    "status": "in_progress",
                    "next_action": TEXT[language]["general_task_next_input"],
                    "source_channel": "web",
                },
            ).model_dump(),
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        self._add_event(mission, "mission_created", "Conversation mission and work item created")
        return mission

    def _load_mission(self, mission_id: str) -> dict[str, Any] | None:
        if mission_id in self._missions:
            return deepcopy(self._missions[mission_id])
        if self.collection is not None:
            value = self.collection.find_one({"mission_id": mission_id}, {"_id": 0})
            if value:
                self._missions[mission_id] = value
                return deepcopy(value)
        return None

    def _save_mission(self, mission: dict[str, Any]) -> None:
        mission["updated_at"] = self._now()
        self._missions[mission["mission_id"]] = deepcopy(mission)
        if self.collection is not None:
            self.collection.replace_one({"mission_id": mission["mission_id"]}, mission, upsert=True)
        work_item = mission.get("dossier", {}).get("work_item")
        if self.tasks is not None and work_item:
            self.tasks.replace_one({"task_id": work_item["task_id"]}, work_item, upsert=True)

    def _cached_operation(self, key: str) -> dict[str, Any] | None:
        if key in self._responses:
            return self._public_value(deepcopy(self._responses[key]))
        if self.operations is not None:
            value = self.operations.find_one({"idempotency_key": key}, {"_id": 0, "response": 1})
            if value:
                response = self._public_value(value["response"])
                self._responses[key] = response
                return deepcopy(response)
        return None

    def _save_operation(self, key: str, mission_id: str, kind: str, response: dict[str, Any]) -> None:
        response = self._public_value(response)
        self._responses[key] = deepcopy(response)
        if self.operations is not None:
            self.operations.update_one(
                {"idempotency_key": key},
                {"$setOnInsert": {"mission_id": mission_id, "kind": kind, "response": response, "created_at": self._now()}},
                upsert=True,
            )

    def _require_mission(self, mission_id: str) -> dict[str, Any]:
        mission = self._load_mission(mission_id)
        if mission is None:
            raise KeyError("mission_not_found")
        return mission

    @staticmethod
    def _mission_id(key: str) -> str:
        return "mission_" + sha256(key.encode()).hexdigest()[:18]

    @staticmethod
    def _append_unique(items: list[str], value: str) -> None:
        if value not in items:
            items.append(value)

    def _sync_work_item(self, mission: dict[str, Any]) -> None:
        dossier = mission["dossier"]
        work_item = dossier.get("work_item")
        if not work_item:
            return
        quote = dossier.get("quote") or {}
        if quote.get("status") == "delivered":
            status = "completed"
            next_action = TEXT[mission["language"]]["task_done"]
        elif quote.get("status") == "approved":
            status = "ready_for_delivery"
            next_action = TEXT[mission["language"]]["task_next_delivery"]
        elif quote.get("status") == "draft":
            status = "awaiting_approval"
            next_action = TEXT[mission["language"]]["task_next_approval"]
        elif self._workspace(mission)["requirements"] and not any(
            item.get("status") == "approved"
            for item in self._workspace(mission)["alternatives"]
        ):
            status = "needs_input"
            next_action = TEXT[mission["language"]]["task_next_design"]
        elif dossier.get("confirmed_scope") and dossier["customer"].get("identifier"):
            status = "ready_for_quote"
            next_action = TEXT[mission["language"]]["task_next_quote"]
        else:
            status = "needs_input"
            kind = self._project_kind(dossier)
            next_action_key = {
                "photo_workshop": "photo_task_next_input",
                "access_control": "task_next_input",
                "general": "general_task_next_input",
            }.get(kind, "general_task_next_input")
            next_action = TEXT[mission["language"]][next_action_key]
        work_item.update({"status": status, "next_action": next_action})

    def _add_event(self, mission: dict[str, Any], kind: str, detail: str) -> None:
        timeline = mission["dossier"].setdefault("timeline", [])
        at = self._now()
        seed = f"{mission['mission_id']}:{kind}:{len(timeline)}:{at}"
        timeline.append(
            {
                "event_id": "event_" + sha256(seed.encode()).hexdigest()[:18],
                "kind": kind,
                "detail": detail,
                "at": at,
            }
        )
        if len(timeline) > 200:
            del timeline[:-200]

    @staticmethod
    def _requirement_key(category: str, text: str) -> str:
        value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        return f"{category}:{re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')}"

    @staticmethod
    def _workspace(mission: dict[str, Any]) -> dict[str, Any]:
        dossier = mission.setdefault("dossier", {})
        current = dossier.get("decision_workspace") or {}
        normalized = DecisionWorkspace.model_validate(current).model_dump()
        dossier["decision_workspace"] = normalized
        return normalized

    @staticmethod
    def _refresh_decision_workspace(workspace: dict[str, Any]) -> None:
        statuses = {item.get("status") for item in workspace.get("alternatives", [])}
        if "approved" in statuses:
            status = "approved"
        elif "ready_for_review" in statuses:
            status = "ready_for_review"
        elif workspace.get("alternatives"):
            status = "needs_validation"
        elif workspace.get("requirements"):
            status = "drafting_alternatives"
        else:
            status = "collecting_requirements"
        workspace["status"] = status

    @staticmethod
    def _resolve_offer_line(
        dossier: dict[str, Any],
        offer_line_id: str,
        sku: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        normalized_sku = sku.strip().lower()
        for offer in dossier.get("supplier_offers", []):
            for line in offer.get("lines", []):
                if offer_line_id and line.get("line_id") == offer_line_id:
                    candidates.append((offer, line))
                elif not offer_line_id and normalized_sku and str(line.get("sku") or "").lower() == normalized_sku:
                    candidates.append((offer, line))
        if not offer_line_id and not normalized_sku:
            raise ValueError("configuration_item_reference_required")
        if not candidates:
            raise ValueError("configuration_item_not_found")
        if len(candidates) > 1:
            raise ValueError("configuration_item_ambiguous")
        offer, line = candidates[0]
        if normalized_sku and str(line.get("sku") or "").lower() != normalized_sku:
            raise ValueError("configuration_item_reference_mismatch")
        rejected_draft_ids = {
            item.get("catalog_draft_id")
            for item in dossier.get("catalog_drafts", [])
            if item.get("status") == "rejected"
        }
        if line.get("catalog_draft_id") in rejected_draft_ids:
            raise ValueError("configuration_catalog_item_rejected")
        return offer, line

    @staticmethod
    def _resolve_evidence(
        dossier: dict[str, Any],
        evidence_ids: list[str],
    ) -> list[dict[str, Any]]:
        index = {
            item.get("evidence_id"): item
            for item in dossier.get("extracted_evidence", [])
            if item.get("evidence_id")
        }
        missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in index]
        if missing:
            raise ValueError("configuration_evidence_not_found")
        return [index[evidence_id] for evidence_id in evidence_ids]

    def _catalog_index(self, mission: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """Read known catalog items without turning an unavailable source into a match."""
        index: dict[str, dict[str, Any]] = {}
        lookup = {
            "source": f"{self.settings.ralfia_ops_base_url.rstrip('/')}/api/inventory/items",
            "status": "unavailable",
            "items_read": 0,
        }

        items: list[dict[str, Any]] = []
        try:
            response = httpx.get(lookup["source"], params={"limit": 200}, timeout=1.2)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                items = [item for item in payload if isinstance(item, dict)]
            elif isinstance(payload, dict):
                raw_items = payload.get("items") or payload.get("results") or payload.get("data") or []
                if isinstance(raw_items, list):
                    items = [item for item in raw_items if isinstance(item, dict)]
            lookup.update({"status": "ok", "items_read": len(items)})
        except Exception:
            pass

        if self.catalog is not None:
            try:
                items.extend(self.catalog.find({}, {"_id": 0}).limit(200))
            except Exception:
                pass
        for draft in mission.get("dossier", {}).get("catalog_drafts", []):
            if draft.get("status") == "approved_staging" and draft.get("canonical_item_id"):
                items.append(draft)

        for item in items:
            if not self._canonical_item_id(item):
                continue
            sku = str(item.get("sku") or item.get("item_code") or item.get("code") or "").strip().lower()
            name = str(item.get("name") or item.get("nombre") or item.get("description") or "").strip()
            if sku:
                index.setdefault(f"sku:{sku}", item)
            if name:
                index.setdefault(f"name:{self._catalog_key('', name)}", item)
        return index, lookup

    @classmethod
    def _find_catalog_match(
        cls,
        index: dict[str, dict[str, Any]],
        sku: str,
        description: str,
    ) -> dict[str, Any] | None:
        normalized_sku = sku.strip().lower()
        if normalized_sku and f"sku:{normalized_sku}" in index:
            return index[f"sku:{normalized_sku}"]
        return index.get(f"name:{cls._catalog_key('', description)}")

    @staticmethod
    def _canonical_item_id(item: dict[str, Any] | None) -> str:
        if not item:
            return ""
        return str(
            item.get("canonical_item_id")
            or item.get("item_id")
            or item.get("inventory_item_id")
            or item.get("product_id")
            or item.get("id")
            or item.get("_id")
            or ""
        )

    @staticmethod
    def _catalog_key(sku: str, description: str) -> str:
        value = sku or description
        ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "item"

    @staticmethod
    def _profile_id(profile: dict[str, Any]) -> str:
        identity = profile.get("party_id") or normalize_name(profile.get("party_name"))
        seed = f"{profile.get('party_role', '')}:{identity}"
        return "commercial_" + sha256(seed.encode()).hexdigest()[:18]

    def _supplier_profile_terms(self, dossier: dict[str, Any], offer: dict[str, Any]) -> dict[str, Any]:
        """Apply supplier terms only for an exact party ID or one exact normalized-name match."""
        profiles = [item for item in dossier.get("commercial_profiles", []) if item.get("party_role") == "supplier"]
        party_id = str(offer.get("supplier_party_id") or "")
        if party_id:
            matched = [item for item in profiles if item.get("party_id") == party_id]
        else:
            name = normalize_name(str(offer.get("supplier_name") or ""))
            matched = [item for item in profiles if name and normalize_name(item.get("party_name")) == name]
        return dict(matched[0].get("terms") or {}) if len(matched) == 1 else {}

    def _refresh_sourcing_recommendations(self, mission: dict[str, Any]) -> None:
        dossier = mission["dossier"]
        grouped: dict[str, list[SourcingOffer]] = {}
        for stored in dossier.get("supplier_offers", []):
            terms = self._supplier_profile_terms(dossier, stored)
            source_lines = stored.get("lines", [])
            single_line = len(source_lines) == 1
            for line in source_lines:
                group = str(line.get("canonical_item_id") or "")
                if not group:
                    group = "draft:" + str(line.get("catalog_draft_id") or "")
                if group == "draft:":
                    sku = self._catalog_key(str(line.get("sku") or ""), "")
                    group = "sku:" + sku if sku != "item" else ""
                if not group:
                    continue
                # Whole-offer landed facts are only attributable to one line; otherwise remain unknown.
                def fact(name: str, default=None):
                    value = stored.get(name)
                    if name == "credit_status" and value in {"", None, "unverified", "unavailable"} and terms.get(name):
                        return terms[name]
                    return value if value not in (None, "") else terms.get(name, default)
                grouped.setdefault(group, []).append(SourcingOffer(
                    canonical_item_id=group,
                    supplier_party_id=stored.get("supplier_party_id") or None,
                    supplier_name=stored.get("supplier_name") or None,
                    supplier_reference=stored.get("supplier_reference") or None,
                    unit_cost=line.get("unit_cost"), quantity=line.get("quantity"), currency=stored.get("currency") or "USD",
                    tax_amount=fact("tax_amount") if single_line else None,
                    tax_status=fact("tax_status", "unknown") if single_line else "unknown",
                    shipping_cost=fact("shipping_cost") if single_line else None,
                    other_cost=fact("other_cost") if single_line else None,
                    availability=stored.get("availability") or "unknown", stock_quantity=stored.get("stock_quantity"),
                    lead_time_days=stored.get("lead_time_days"), valid_until=stored.get("valid_until") or None,
                    source=stored.get("supplier_reference") or None, evidence=stored.get("attachment_sha256") or None,
                    payment_mode=fact("payment_mode") or None, credit_days=fact("credit_days"),
                    credit_status=fact("credit_status", "unverified"), credit_source=fact("credit_source") or None,
                    credit_confirmed_date=fact("credit_confirmed_date") or None,
                ))
        results = []
        policy = dossier.get("sourcing_policy_max_credit_premium_pct", 5)
        for group in sorted(grouped):
            recommendation = recommend_offer(grouped[group], max_credit_premium_pct=policy)
            def present(value):
                if value is None:
                    return None
                return {"supplier_party_id": value.offer.supplier_party_id, "supplier_name": value.offer.supplier_name,
                        "supplier_reference": value.offer.supplier_reference, "landed_unit_cost": str(value.landed_unit_cost) if value.landed_unit_cost is not None else None,
                        "eligible": value.eligible, "reasons": list(value.reasons), "credit_status": value.offer.credit_status,
                        "unknown_facts": [reason for reason in value.reasons if reason.startswith("unknown_") or reason == "availability_unconfirmed"]}
            results.append({"canonical_item_id": group, "lowest_cost_offer": present(recommendation.lowest_cost_offer),
                            "best_confirmed_credit_offer": present(recommendation.best_confirmed_credit_offer),
                            "recommended_offer": present(recommendation.recommended_offer), "recommendation_reason": recommendation.recommendation_reason,
                            "absolute_delta": str(recommendation.absolute_delta) if recommendation.absolute_delta is not None else None,
                            "percentage_delta": str(recommendation.percentage_delta) if recommendation.percentage_delta is not None else None,
                            "policy_max_credit_premium_pct": str(recommendation.policy_max_credit_premium_pct),
                            "alternatives": [present(item) for item in recommendation.alternatives]})
        dossier["sourcing_recommendations"] = results

    @classmethod
    def _public_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cls._public_value(item) for key, item in value.items() if key != "_id"}
        if isinstance(value, list):
            return [cls._public_value(item) for item in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
