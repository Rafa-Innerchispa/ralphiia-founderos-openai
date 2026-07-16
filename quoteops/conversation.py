from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import re
from threading import RLock
from typing import Any

from pymongo import MongoClient

from quoteops.adapters.taxpayer_registry import TaxpayerRegistryError, normalize_ec_identifier
from quoteops.contracts import (
    ContextDossier,
    ConversationMessageRequest,
    ConversationReply,
    DossierCustomer,
    DossierOption,
    DossierSite,
    EditableQuote,
    EditableQuoteLine,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    QuoteUpdateRequest,
)


TEXT = {
    "es": {
        "scope": "Cambio o rehabilitación del sistema de control de acceso",
        "assumption": "Se evaluará qué componentes existentes pueden conservarse antes de reemplazarlos.",
        "risk": "La compatibilidad del sistema existente debe verificarse en sitio.",
        "option_a": "Rehabilitación selectiva",
        "option_a_summary": "Conservar componentes compatibles y sustituir únicamente los puntos críticos.",
        "option_b": "Renovación integral",
        "option_b_summary": "Diseñar una plataforma nueva con migración controlada del sistema actual.",
        "question_customer": "¿Cuál es la cédula o RUC del cliente?",
        "question_site": "¿Dónde está el sitio y cuántos accesos o puertas incluye?",
        "question_existing": "¿Qué marca, modelo y estado tiene el sistema actual?",
        "question_schedule": "¿Qué restricciones operativas y fecha objetivo debemos considerar?",
        "reply_progress": "Ya incorporé la información al expediente. Para avanzar necesito: {questions}",
        "reply_ready": "El expediente tiene contexto suficiente. Puedes pedirme preparar la cotización editable.",
        "reply_quote": "Preparé un borrador editable sin inventar precios. Completa los valores reales antes de enviarlo a aprobación.",
        "reply_approved": "La aprobación humana quedó registrada y el PDF real está listo.",
        "reply_delivered": "La entrega quedó registrada con su identificador y trazabilidad.",
    },
    "en": {
        "scope": "Replace or rehabilitate the access-control system",
        "assumption": "Existing components will be assessed for reuse before replacement.",
        "risk": "Compatibility with the existing system must be verified on site.",
        "option_a": "Selective rehabilitation",
        "option_a_summary": "Keep compatible components and replace only critical access points.",
        "option_b": "Full renewal",
        "option_b_summary": "Design a new platform with a controlled migration from the current system.",
        "question_customer": "What is the customer's national ID or RUC?",
        "question_site": "Where is the site and how many doors or access points are included?",
        "question_existing": "What are the brand, model, and condition of the current system?",
        "question_schedule": "Which operating constraints and target date should we consider?",
        "reply_progress": "I added the information to the case file. To continue I need: {questions}",
        "reply_ready": "The case file has enough context. You can ask me to prepare the editable quote.",
        "reply_quote": "I prepared an editable draft without inventing prices. Enter the real values before human approval.",
        "reply_approved": "Human approval was recorded and the real PDF is ready.",
        "reply_delivered": "Delivery was registered with its identifier and trace.",
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
            self.collection.create_index("mission_id", unique=True)
            self.operations.create_index("idempotency_key", unique=True)
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
            mission["messages"].append(
                {
                    "role": "user",
                    "text": request.message,
                    "attachments": [item.model_dump() for item in request.attachments],
                    "at": self._now(),
                }
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
                self._refresh_questions(mission)
            reply = self._reply(mission)
            return ConversationReply.model_validate(self._response(mission, reply))

    def update_quote(self, mission_id: str, request: QuoteUpdateRequest) -> ConversationReply:
        with self._lock:
            replay = self._cached_operation(request.idempotency_key)
            if replay:
                replay["idempotent_replay"] = True
                return ConversationReply.model_validate(replay)
            mission = self._require_mission(mission_id)
            subtotal = round(sum(line.quantity * line.unit_price for line in request.lines), 2)
            tax = round(subtotal * request.tax_rate, 2)
            quote = EditableQuote(
                status="draft" if subtotal > 0 and all(line.unit_price > 0 for line in request.lines) else "needs_pricing",
                lines=request.lines,
                subtotal=subtotal,
                tax=tax,
                total=round(subtotal + tax, 2),
            )
            mission["language"] = request.language
            mission["dossier"]["quote"] = quote.model_dump()
            mission["phase"] = "quote"
            mission["dossier"]["progress"] = max(mission["dossier"]["progress"], 82)
            self._save_mission(mission)
            response = self._response(mission, self._reply(mission))
            self._save_operation(request.idempotency_key, mission_id, "quote_update", response)
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
            self._set_progress_and_phase(mission)
            self._save_mission(mission)
            return ConversationReply.model_validate(self._response(mission, self._reply(mission)))

    def _apply_message(self, mission: dict[str, Any], request: ConversationMessageRequest) -> None:
        text = request.message
        lower = text.lower()
        dossier = mission["dossier"]
        if re.search(r"\bfemar\b", lower):
            dossier["customer"]["name"] = "FEMAR"
        generic_name = re.search(r"(?:cliente|customer)\s*[:\-]\s*([^\n,.]{2,80})", text, re.IGNORECASE)
        if generic_name and not dossier["customer"]["name"]:
            dossier["customer"]["name"] = generic_name.group(1).strip()

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

        dossier["options"] = [
            DossierOption(code="A", title=TEXT[request.language]["option_a"], summary=TEXT[request.language]["option_a_summary"]).model_dump(),
            DossierOption(code="B", title=TEXT[request.language]["option_b"], summary=TEXT[request.language]["option_b_summary"]).model_dump(),
        ] if dossier["confirmed_scope"] else []
        if any(word in lower for word in ("cotiz", "borrador", "quote", "proposal")) and dossier["confirmed_scope"]:
            dossier["quote"] = dossier.get("quote") or self._quote_draft(dossier, request.language).model_dump()
        self._refresh_questions(mission)
        self._set_progress_and_phase(mission)

    def _quote_draft(self, dossier: dict[str, Any], language: str) -> EditableQuote:
        access_points = int(dossier["site"].get("access_points") or 1)
        descriptions = (
            ["Levantamiento técnico y diseño", "Equipos y materiales de control de acceso", "Instalación, configuración y capacitación"]
            if language == "es"
            else ["Technical assessment and design", "Access-control equipment and materials", "Installation, configuration, and training"]
        )
        return EditableQuote(
            status="needs_pricing",
            lines=[
                EditableQuoteLine(line_id="assessment", description=descriptions[0], quantity=1, unit_price=0),
                EditableQuoteLine(line_id="equipment", description=descriptions[1], quantity=access_points, unit_price=0),
                EditableQuoteLine(line_id="implementation", description=descriptions[2], quantity=1, unit_price=0),
            ],
        )

    def _refresh_questions(self, mission: dict[str, Any]) -> None:
        language = mission["language"]
        dossier = mission["dossier"]
        questions = []
        if not dossier["customer"].get("identifier"):
            questions.append(TEXT[language]["question_customer"])
        if not dossier["site"].get("location") or not dossier["site"].get("access_points"):
            questions.append(TEXT[language]["question_site"])
        if dossier["confirmed_scope"] and not dossier["assumptions"]:
            questions.append(TEXT[language]["question_existing"])
        if dossier["confirmed_scope"]:
            questions.append(TEXT[language]["question_schedule"])
        dossier["questions"] = questions

    def _set_progress_and_phase(self, mission: dict[str, Any]) -> None:
        dossier = mission["dossier"]
        score = 10
        score += 12 if dossier["customer"].get("name") else 0
        score += 16 if dossier["customer"].get("identifier") else 0
        score += 22 if dossier["confirmed_scope"] else 0
        score += 14 if dossier["site"].get("location") else 0
        score += 12 if dossier["site"].get("access_points") else 0
        score += 6 if dossier["attachments"] else 0
        score += 8 if dossier.get("quote") else 0
        dossier["progress"] = min(score, 90 if not dossier.get("quote") else 92)
        quote = dossier.get("quote") or {}
        if quote.get("status") == "delivered":
            mission["phase"] = "delivery"
        elif quote.get("status") == "approved":
            mission["phase"] = "approval"
        elif quote:
            mission["phase"] = "quote"
        elif not dossier["customer"].get("identifier"):
            mission["phase"] = "identity"
        elif dossier["confirmed_scope"]:
            mission["phase"] = "scope"
        else:
            mission["phase"] = "discovery"

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
        return {
            "mission_id": mission_id,
            "language": language,
            "phase": "discovery",
            "dossier": ContextDossier(
                customer=DossierCustomer(),
                site=DossierSite(),
                progress=10,
            ).model_dump(),
            "messages": [],
            "created_at": self._now(),
            "updated_at": self._now(),
        }

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
