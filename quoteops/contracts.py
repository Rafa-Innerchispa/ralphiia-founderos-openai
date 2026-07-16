from typing import Literal
import re
from pydantic import BaseModel, Field, field_validator


def validate_email_value(value: str, field_name: str = "email") -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError(f"{field_name} debe tener un correo valido con dominio")
    return value.lower()


def validate_phone_value(value: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"\+?[0-9][0-9 .()\-]{6,19}", value):
        raise ValueError("phone debe contener un telefono valido")
    return value


class QuoteIntake(BaseModel):
    source_channel: Literal["whatsapp", "telegram", "chatgpt_mcp", "web", "sandbox"] = "sandbox"
    customer_name: str = Field(default="", max_length=200, description="Nombre del cliente o solicitante")
    contact: str = Field(default="", max_length=200, description="Teléfono, correo o referencia")
    original_text: str = Field(default="", max_length=10000, description="Texto crudo del mensaje o transcripción")
    attachments: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("customer_name", "contact", "original_text", mode="before")
    @classmethod
    def strip_text(cls, value):
        return str(value or "").strip()

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, value: str) -> str:
        if not value:
            return value
        email = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        phone = r"^\+?[0-9][0-9 .()-]{6,19}$"
        if not re.fullmatch(email, value) and not re.fullmatch(phone, value):
            raise ValueError("contact debe ser un correo o telefono valido")
        return value


class MissingInformation(BaseModel):
    items: list[str] = Field(default_factory=list)


class TechnicalRisk(BaseModel):
    items: list[str] = Field(default_factory=list)


class ProposalOption(BaseModel):
    code: str
    title: str
    summary: str
    estimated_value: str = ""


class ToolDecision(BaseModel):
    tool_name: str
    reason: str
    args: dict = Field(default_factory=dict)


class QuoteReview(BaseModel):
    status: Literal["draft", "needs_review", "approved", "rejected"] = "draft"
    notes: list[str] = Field(default_factory=list)


class MissionState(BaseModel):
    mission_id: str
    correlation_id: str
    status: Literal["intake", "analysis", "draft", "review", "delivery", "done"] = "intake"


class QuoteAnalysisResult(BaseModel):
    missing_information: MissingInformation = Field(default_factory=MissingInformation)
    technical_risks: TechnicalRisk = Field(default_factory=TechnicalRisk)
    proposal_options: list[ProposalOption] = Field(default_factory=list)
    review: QuoteReview = Field(default_factory=QuoteReview)
    next_action: str = ""


class QuoteIntakeAnalysis(BaseModel):
    ok: bool = True
    analysis_source: Literal["openai", "fallback"] = "fallback"
    model_used: str = "deterministic"
    mission: MissionState
    intake: QuoteIntake
    missing_information: MissingInformation = Field(default_factory=MissingInformation)
    technical_risks: TechnicalRisk = Field(default_factory=TechnicalRisk)
    proposal_options: list[ProposalOption] = Field(default_factory=list)
    review: QuoteReview = Field(default_factory=QuoteReview)
    next_action: str = ""


class ApprovalDraft(BaseModel):
    status: Literal["blocked", "ready", "approved"] = "ready"
    blockers: list[str] = Field(default_factory=list)
    summary: str = ""


class QuoteToolPlan(BaseModel):
    ok: bool = True
    mission: MissionState
    intake: QuoteIntake
    tool_decisions: list[ToolDecision] = Field(default_factory=list)
    approval: ApprovalDraft = Field(default_factory=ApprovalDraft)
    recommended_next_step: str = ""


class RucLookupRequest(BaseModel):
    ruc: str = Field(min_length=13, max_length=13)
    force_refresh: bool = False
    mode: Literal["owner", "sandbox"] = "owner"

    @field_validator("ruc")
    @classmethod
    def validate_ruc_digits(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9]{13}", value.strip()):
            raise ValueError("ruc debe contener exactamente 13 digitos")
        return value.strip()


class TaxpayerEstablishment(BaseModel):
    commercial_name: str = ""
    number: str = ""
    establishment_type: str = ""
    full_address: str = ""


class TaxpayerVerification(BaseModel):
    verification_id: str
    ruc: str
    legal_name: str = ""
    commercial_name: str = ""
    activity: str = ""
    legal_representative: str = ""
    establishments: list[TaxpayerEstablishment] = Field(default_factory=list)
    source: Literal["intuito_azure", "sandbox_fixture"] = "intuito_azure"
    retrieved_at: str
    upstream_status: str = "verified"
    checksum_valid: bool = False
    cache_status: Literal["live", "fresh_cache", "sandbox"] = "live"


class IdentityMatch(BaseModel):
    source: str
    source_id: str = ""
    party_id: str = ""
    client_id: str = ""
    legal_name: str = ""
    commercial_name: str = ""
    ruc: str = ""
    address: str = ""
    linked: bool = False


class IdentityConflict(BaseModel):
    field: str
    source: str
    official_value: str = ""
    source_value: str = ""
    severity: Literal["info", "warning", "critical"] = "warning"


class CustomerComparison(BaseModel):
    matches: list[IdentityMatch] = Field(default_factory=list)
    conflicts: list[IdentityConflict] = Field(default_factory=list)
    exact_ruc_match: bool = False
    recommended_action: Literal["create", "update", "link_existing", "review"] = "create"


class CustomerDraft(BaseModel):
    ruc: str
    legal_name: str
    commercial_name: str = ""
    activity: str = ""
    address: str = ""
    phone: str = ""
    contact_email: str = ""
    billing_email: str = ""
    recommended_action: Literal["create", "update", "link_existing", "review"] = "create"


class RucLookupResult(BaseModel):
    ok: bool = True
    trace_id: str
    verification: TaxpayerVerification
    comparison: CustomerComparison
    customer_draft: CustomerDraft
    approval_required: bool = True
    persistence_target: str = "quoteops_staging"


class RucConfirmRequest(BaseModel):
    ruc: str = Field(min_length=13, max_length=13)
    approved_by: str = Field(min_length=2, max_length=120)
    expected_verification_id: str = Field(min_length=5, max_length=80)
    contact_email: str
    billing_email: str
    phone: str
    address: str = Field(min_length=3, max_length=300)

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str) -> str:
        return validate_email_value(value, "contact_email")

    @field_validator("billing_email")
    @classmethod
    def validate_billing_email(cls, value: str) -> str:
        return validate_email_value(value, "billing_email")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return validate_phone_value(value)

    @field_validator("ruc")
    @classmethod
    def validate_ruc_digits(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9]{13}", value.strip()):
            raise ValueError("ruc debe contener exactamente 13 digitos")
        return value.strip()


class RucConfirmationResult(BaseModel):
    ok: bool = True
    trace_id: str
    created: bool
    action: Literal["created", "updated", "linked"]
    party_id: str
    client_id: str
    ruc: str
    persistence_target: str = "quoteops_staging"
    duplicate_count: int = 1
    canonical_status: Literal["staging_only", "upserted", "blocked", "error"] = "staging_only"
    canonical_client_id: str = ""


LanguageCode = Literal["es", "en"]


class ConversationAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    media_type: str = Field(default="application/octet-stream", max_length=120)
    size_bytes: int = Field(default=0, ge=0, le=25_000_000)
    storage_id: str = Field(default="", max_length=120)
    sha256: str = Field(default="", max_length=64)
    status: Literal["selected", "stored"] = "selected"

    @field_validator("name", "media_type", mode="before")
    @classmethod
    def strip_attachment_text(cls, value):
        return str(value or "").strip()


class ConversationMessageRequest(BaseModel):
    mission_id: str = Field(default="", max_length=80, pattern=r"^(?:|mission_[a-f0-9]{18})$")
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    message: str = Field(default="", max_length=30_000)
    attachments: list[ConversationAttachment] = Field(default_factory=list, max_length=20)

    @field_validator("mission_id", "idempotency_key", "message", mode="before")
    @classmethod
    def strip_conversation_text(cls, value):
        return str(value or "").strip()


class DossierCustomer(BaseModel):
    name: str = ""
    identifier: str = ""
    identifier_type: Literal["cedula", "ruc", ""] = ""
    verification_status: Literal["pending", "locally_valid", "verified", "needs_review"] = "pending"
    source: str = ""


class DossierSite(BaseModel):
    location: str = ""
    access_points: str = ""
    operating_constraints: list[str] = Field(default_factory=list)


class DossierOption(BaseModel):
    code: str
    title: str
    summary: str


class EditableQuoteLine(BaseModel):
    line_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=400)
    quantity: float = Field(default=1, gt=0, le=100_000)
    unit_price: float = Field(default=0, ge=0, le=100_000_000)


class EditableQuote(BaseModel):
    currency: Literal["USD"] = "USD"
    status: Literal["needs_pricing", "draft", "approved", "delivered"] = "needs_pricing"
    lines: list[EditableQuoteLine] = Field(default_factory=list, max_length=100)
    subtotal: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    approval_id: str = ""
    artifact_id: str = ""
    pdf_url: str = ""
    delivery_id: str = ""


class ContextDossier(BaseModel):
    customer: DossierCustomer = Field(default_factory=DossierCustomer)
    site: DossierSite = Field(default_factory=DossierSite)
    confirmed_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    options: list[DossierOption] = Field(default_factory=list)
    attachments: list[ConversationAttachment] = Field(default_factory=list)
    progress: int = Field(default=0, ge=0, le=100)
    quote: EditableQuote | None = None


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=30_000)
    at: str


class ConversationReply(BaseModel):
    ok: bool = True
    mission_id: str
    language: LanguageCode
    phase: Literal["discovery", "identity", "scope", "quote", "approval", "delivery"]
    assistant_message: str
    dossier: ContextDossier
    history: list[ConversationTurn] = Field(default_factory=list)
    idempotent_replay: bool = False
    runtime_label: str = "Codex-built / MCP runtime"


class QuoteUpdateRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    lines: list[EditableQuoteLine] = Field(min_length=1, max_length=100)
    tax_rate: float = Field(default=0, ge=0, le=1)


class MissionApprovalRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    approved_by: str = Field(min_length=2, max_length=120)
    access_mode: Literal["private", "judge"] = "judge"


class MissionDeliveryRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    channels: list[Literal["download", "email", "whatsapp", "telegram"]] = Field(
        default_factory=lambda: ["download"], max_length=4
    )
    access_mode: Literal["private", "judge"] = "judge"


class CustomerIdentifierLookupRequest(BaseModel):
    identifier: str = Field(min_length=10, max_length=13)
    mission_id: str = Field(default="", max_length=80, pattern=r"^(?:|mission_[a-f0-9]{18})$")
    language: LanguageCode = "es"
    force_refresh: bool = False

    @field_validator("identifier", mode="before")
    @classmethod
    def validate_identifier_digits(cls, value: str) -> str:
        clean = re.sub(r"[\s-]", "", str(value or ""))
        if not re.fullmatch(r"(?:[0-9]{10}|[0-9]{13})", clean):
            raise ValueError("identifier must contain 10 or 13 digits")
        return clean


class IntegrationTrace(BaseModel):
    integration: str
    source: str
    call: str
    status: Literal["ready", "ok", "warning", "error", "not_configured"]
    latency_ms: float = Field(default=0, ge=0)
    observed_at: str
    result: str
