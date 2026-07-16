from typing import Any, Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
ChannelCode = Literal["web", "chatgpt_mcp", "whatsapp", "telegram", "api"]


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
    source_channel: ChannelCode = "web"
    channel_event_id: str = Field(default="", max_length=160)
    sender_id: str = Field(default="", max_length=160)
    customer_name: str = Field(default="", max_length=200)
    message: str = Field(default="", max_length=30_000)
    attachments: list[ConversationAttachment] = Field(default_factory=list, max_length=20)

    @field_validator(
        "mission_id",
        "idempotency_key",
        "message",
        "channel_event_id",
        "sender_id",
        "customer_name",
        mode="before",
    )
    @classmethod
    def strip_conversation_text(cls, value):
        return str(value or "").strip()


class ChannelEventEnvelope(BaseModel):
    channel: ChannelCode
    payload: dict[str, Any]
    signature: str = Field(default="", max_length=256)


class DossierCustomer(BaseModel):
    name: str = ""
    identifier: str = ""
    identifier_type: Literal["cedula", "ruc", ""] = ""
    verification_status: Literal["pending", "locally_valid", "verified", "needs_review"] = "pending"
    source: str = ""


CreditStatus = Literal["current_confirmed", "historical_observed", "unverified", "unavailable"]
PartyRole = Literal["customer", "supplier"]


class CommercialPaymentTerms(BaseModel):
    payment_mode: str = Field(default="", max_length=120)
    credit_days: int | None = Field(default=None, ge=0, le=3650)
    credit_status: CreditStatus = "unverified"
    credit_limit: float | None = Field(default=None, ge=0)
    payment_behavior_or_risk: str = Field(default="", max_length=500)
    preference_or_quality: str = Field(default="", max_length=500)
    confirmation_source: str = Field(default="", max_length=300)
    confirmed_date: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=2000)


class CommercialPartyProfile(BaseModel):
    profile_id: str = ""
    party_role: PartyRole
    party_id: str = Field(default="", max_length=160)
    party_name: str = Field(default="", max_length=200)
    party_type: str = Field(default="", max_length=120)
    category: str = Field(default="", max_length=120)
    terms: CommercialPaymentTerms = Field(default_factory=CommercialPaymentTerms)


class CommercialProfileUpsertRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    profile: CommercialPartyProfile
    max_credit_premium_pct: float | None = Field(default=None, ge=0, le=100)


class CommercialProfileUpsertResult(BaseModel):
    ok: bool = True
    mission_id: str
    profile: CommercialPartyProfile
    idempotent_replay: bool = False


class DossierSite(BaseModel):
    location: str = ""
    access_points: str = ""
    operating_constraints: list[str] = Field(default_factory=list)


class ProjectProfile(BaseModel):
    kind: Literal["general", "access_control", "photo_workshop"] = "general"
    title: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=1000)
    facts: dict[str, str] = Field(default_factory=dict)


class DossierOption(BaseModel):
    code: str
    title: str
    summary: str
    status: Literal[
        "needs_scope",
        "needs_costs",
        "needs_validation",
        "ready_for_review",
        "needs_pricing",
        "ready",
        "approved",
    ] = "needs_costs"
    line_ids: list[str] = Field(default_factory=list, max_length=100)
    supplier_cost_total: float = Field(default=0, ge=0)
    selling_total: float = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)


class MissionWorkItem(BaseModel):
    task_id: str
    correlation_id: str
    title: str
    status: Literal[
        "in_progress",
        "needs_input",
        "ready_for_quote",
        "awaiting_approval",
        "ready_for_delivery",
        "completed",
    ] = "in_progress"
    next_action: str = ""
    source_channel: ChannelCode = "web"


class MissionTimelineEvent(BaseModel):
    event_id: str
    kind: Literal[
        "mission_created",
        "message_received",
        "attachment_stored",
        "evidence_extracted",
        "evidence_reviewed",
        "catalog_reviewed",
        "customer_verified",
        "supplier_offer_added",
        "requirements_updated",
        "alternative_updated",
        "alternative_reviewed",
        "channel_event_received",
        "package_selected",
        "quote_priced",
        "quote_approved",
        "delivery_registered",
    ]
    detail: str
    at: str


class SupplierOfferLineInput(BaseModel):
    sku: str = Field(default="", max_length=120)
    description: str = Field(min_length=2, max_length=400)
    kind: Literal["equipment", "material", "service", "labor"] = "equipment"
    quantity: float = Field(default=1, gt=0, le=100_000)
    unit: str = Field(default="unit", min_length=1, max_length=40)
    unit_cost: float = Field(gt=0, le=100_000_000)
    package_codes: list[Literal["A", "B", "C"]] = Field(default_factory=lambda: ["A", "B", "C"])

    @field_validator("sku", "description", "unit", mode="before")
    @classmethod
    def strip_offer_line_text(cls, value):
        return str(value or "").strip()


class SupplierOfferCreateRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    supplier_name: str = Field(min_length=2, max_length=200)
    supplier_party_id: str = Field(default="", max_length=160)
    supplier_reference: str = Field(min_length=2, max_length=200)
    currency: Literal["USD"] = "USD"
    tax_included: bool | None = None
    effective_at: str = Field(default="", max_length=40)
    valid_until: str = Field(default="", max_length=40)
    attachment_storage_id: str = Field(default="", max_length=120)
    attachment_sha256: str = Field(default="", max_length=64, pattern=r"^(?:|[a-f0-9]{64})$")
    notes: str = Field(default="", max_length=1000)
    payment_mode: str = Field(default="", max_length=120)
    credit_days: int | None = Field(default=None, ge=0, le=3650)
    credit_status: CreditStatus = "unverified"
    credit_source: str = Field(default="", max_length=300)
    credit_confirmed_date: str = Field(default="", max_length=40)
    tax_amount: float | None = Field(default=None, ge=0)
    tax_status: Literal["known", "unknown"] = "unknown"
    shipping_cost: float | None = Field(default=None, ge=0)
    other_cost: float | None = Field(default=None, ge=0)
    availability: Literal["available", "unavailable", "unknown"] = "unknown"
    stock_quantity: float | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0, le=3650)
    lines: list[SupplierOfferLineInput] = Field(min_length=1, max_length=100)

    @field_validator(
        "supplier_name",
        "supplier_reference",
        "effective_at",
        "valid_until",
        "attachment_storage_id",
        "attachment_sha256",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_offer_text(cls, value):
        return str(value or "").strip()


class SupplierOfferLine(BaseModel):
    line_id: str
    sku: str = ""
    description: str
    kind: Literal["equipment", "material", "service", "labor"]
    quantity: float
    unit: str
    unit_cost: float
    line_cost: float
    package_codes: list[Literal["A", "B", "C"]]
    catalog_draft_id: str = ""
    canonical_item_id: str = ""


class SupplierOffer(BaseModel):
    offer_id: str
    supplier_name: str
    supplier_party_id: str = ""
    supplier_reference: str
    currency: Literal["USD"] = "USD"
    tax_included: bool | None = None
    effective_at: str = ""
    valid_until: str = ""
    attachment_storage_id: str = ""
    attachment_sha256: str = ""
    notes: str = ""
    payment_mode: str = ""
    credit_days: int | None = None
    credit_status: CreditStatus = "unverified"
    credit_source: str = ""
    credit_confirmed_date: str = ""
    tax_amount: float | None = None
    tax_status: Literal["known", "unknown"] = "unknown"
    shipping_cost: float | None = None
    other_cost: float | None = None
    availability: Literal["available", "unavailable", "unknown"] = "unknown"
    stock_quantity: float | None = None
    lead_time_days: int | None = None
    total_cost: float = Field(ge=0)
    evidence_status: Literal["reference", "attachment", "reference_and_attachment"] = "reference"
    lines: list[SupplierOfferLine] = Field(default_factory=list)


class SourcingOfferSummary(BaseModel):
    supplier_party_id: str | None = None
    supplier_name: str | None = None
    supplier_reference: str | None = None
    landed_unit_cost: str | None = None
    eligible: bool
    reasons: list[str] = Field(default_factory=list)
    credit_status: CreditStatus = "unverified"
    unknown_facts: list[str] = Field(default_factory=list)


class SupplierSourcingRecommendation(BaseModel):
    canonical_item_id: str
    lowest_cost_offer: SourcingOfferSummary | None = None
    best_confirmed_credit_offer: SourcingOfferSummary | None = None
    recommended_offer: SourcingOfferSummary | None = None
    recommendation_reason: str = "no_eligible_offer"
    absolute_delta: str | None = None
    percentage_delta: str | None = None
    policy_max_credit_premium_pct: str = "5"
    alternatives: list[SourcingOfferSummary | None] = Field(default_factory=list)


class CatalogDraftItem(BaseModel):
    catalog_draft_id: str
    sku: str = ""
    name: str
    kind: Literal["equipment", "material", "service", "labor"]
    unit: str
    status: Literal["draft", "approved_staging", "rejected"] = "draft"
    source_offer_id: str
    source_line_id: str
    canonical_item_id: str = ""
    approval_required: bool = True
    reviewed_by: str = ""
    review_notes: str = ""


class CatalogDraftReviewRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    decision: Literal["approve", "reject"]
    reviewed_by: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=1000)


class ExtractedFact(BaseModel):
    field: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=1000)
    normalized_value: str = Field(default="", max_length=1000)
    unit: str = Field(default="", max_length=40)
    page: int | None = Field(default=None, ge=1, le=100_000)
    region: str = Field(default="", max_length=120)
    confidence: float = Field(default=0, ge=0, le=1)


class ExtractedProductCandidate(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    brand: str = Field(default="", max_length=120)
    model: str = Field(default="", max_length=120)
    sku: str = Field(default="", max_length=120)
    kind: Literal["equipment", "material", "service", "labor"] = "equipment"
    page: int | None = Field(default=None, ge=1, le=100_000)
    region: str = Field(default="", max_length=120)
    confidence: float = Field(default=0, ge=0, le=1)


class ExtractedSupplierPrice(BaseModel):
    supplier_name: str = Field(default="", max_length=200)
    supplier_reference: str = Field(default="", max_length=200)
    sku: str = Field(default="", max_length=120)
    description: str = Field(min_length=2, max_length=400)
    quantity: float = Field(default=1, gt=0, le=100_000)
    unit: str = Field(default="unit", min_length=1, max_length=40)
    unit_cost: float = Field(gt=0, le=100_000_000)
    currency: Literal["USD"] = "USD"
    tax_included: bool | None = None
    page: int | None = Field(default=None, ge=1, le=100_000)
    region: str = Field(default="", max_length=120)
    confidence: float = Field(default=0, ge=0, le=1)


class MultimodalEvidenceCreateRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    source_file_name: str = Field(min_length=1, max_length=240)
    media_type: str = Field(default="application/octet-stream", max_length=120)
    source_attachment_id: str = Field(default="", max_length=120)
    source_sha256: str = Field(default="", max_length=64, pattern=r"^(?:|[a-f0-9]{64})$")
    extraction_type: Literal[
        "product_label",
        "supplier_price_list",
        "technical_document",
        "site_photo",
        "other",
    ]
    extracted_by: Literal["chatgpt_mcp", "web_ocr", "manual"] = "chatgpt_mcp"
    extracted_text: str = Field(default="", max_length=20_000)
    facts: list[ExtractedFact] = Field(default_factory=list, max_length=300)
    products: list[ExtractedProductCandidate] = Field(default_factory=list, max_length=200)
    supplier_prices: list[ExtractedSupplierPrice] = Field(default_factory=list, max_length=500)
    warnings: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("source_file_name", "media_type", "source_attachment_id", "source_sha256", mode="before")
    @classmethod
    def strip_evidence_source(cls, value):
        return str(value or "").strip()


class MultimodalEvidence(BaseModel):
    evidence_id: str
    source_file_name: str
    media_type: str
    source_attachment_id: str = ""
    source_sha256: str = ""
    extraction_type: Literal[
        "product_label",
        "supplier_price_list",
        "technical_document",
        "site_photo",
        "other",
    ]
    extracted_by: Literal["chatgpt_mcp", "web_ocr", "manual"]
    extracted_text: str = ""
    facts: list[ExtractedFact] = Field(default_factory=list)
    products: list[ExtractedProductCandidate] = Field(default_factory=list)
    supplier_prices: list[ExtractedSupplierPrice] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: Literal["source_unlinked", "needs_review", "confirmed", "rejected"]
    reviewed_by: str = ""
    review_notes: str = ""
    extracted_at: str


class EvidenceReviewRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    decision: Literal["confirm", "reject"]
    reviewed_by: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=1000)


class PackageSelectionRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    option_code: Literal["A", "B", "C"]


class EditableQuoteLine(BaseModel):
    line_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=400)
    quantity: float = Field(default=1, gt=0, le=100_000)
    unit_price: float = Field(default=0, ge=0, le=100_000_000)
    unit_cost: float = Field(default=0, ge=0, le=100_000_000)
    sku: str = Field(default="", max_length=120)
    kind: Literal["equipment", "material", "service", "labor", ""] = ""
    supplier_offer_id: str = Field(default="", max_length=120)
    price_source: Literal["unpriced", "human_entered"] = "unpriced"


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
    selected_option_code: Literal["A", "B", "C", ""] = ""
    supplier_cost_total: float = Field(default=0, ge=0)


class TechnicalRequirementInput(BaseModel):
    requirement_id: str = Field(
        default="",
        max_length=80,
        pattern=r"^(?:|requirement_[a-f0-9]{18})$",
    )
    category: Literal[
        "legacy",
        "infrastructure",
        "door",
        "credential",
        "software",
        "commercial",
        "other",
    ] = "other"
    text: str = Field(min_length=2, max_length=1000)
    status: Literal["confirmed", "assumption", "needs_validation"] = "confirmed"
    priority: Literal["must", "should", "could"] = "must"

    @field_validator("requirement_id", "text", mode="before")
    @classmethod
    def strip_requirement_text(cls, value):
        return str(value or "").strip()


class TechnicalRequirement(TechnicalRequirementInput):
    requirement_id: str = Field(pattern=r"^requirement_[a-f0-9]{18}$")
    source_channel: ChannelCode = "web"
    source_event_id: str = ""
    updated_by: str = ""
    updated_at: str


class DecisionBriefUpdateRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    source_channel: ChannelCode = "web"
    channel_event_id: str = Field(default="", max_length=160)
    updated_by: str = Field(min_length=2, max_length=120)
    requirements: list[TechnicalRequirementInput] = Field(default_factory=list, max_length=100)
    remove_requirement_ids: list[str] = Field(default_factory=list, max_length=100)
    open_questions: list[str] = Field(default_factory=list, max_length=100)
    replace_requirements: bool = False
    replace_open_questions: bool = False
    selected_model: str = Field(default="", max_length=120)


class ConfigurationLineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_line_id: str = Field(default="", max_length=120)
    sku: str = Field(default="", max_length=120)
    quantity: float = Field(default=1, gt=0, le=100_000)
    role: str = Field(default="equipment", min_length=2, max_length=80)
    compatibility_status: Literal["needs_validation", "verified", "incompatible"] = (
        "needs_validation"
    )
    rationale: str = Field(default="", max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("offer_line_id", "sku", "role", "rationale", mode="before")
    @classmethod
    def strip_configuration_line_text(cls, value):
        return str(value or "").strip()


class ConfigurationLine(BaseModel):
    line_id: str
    source_offer_id: str
    source_offer_line_id: str
    supplier_name: str
    canonical_item_id: str = ""
    sku: str = ""
    description: str
    kind: Literal["equipment", "material", "service", "labor"]
    unit: str
    quantity: float
    unit_cost: float = Field(ge=0)
    line_cost: float = Field(ge=0)
    role: str
    compatibility_status: Literal["needs_validation", "verified", "incompatible"]
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class ConfigurationAlternativeUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    source_channel: ChannelCode = "web"
    channel_event_id: str = Field(default="", max_length=160)
    code: Literal["A", "B", "C"]
    title: str = Field(min_length=2, max_length=200)
    objective: str = Field(default="", max_length=1000)
    lines: list[ConfigurationLineInput] = Field(min_length=1, max_length=100)
    coverage: list[str] = Field(default_factory=list, max_length=100)
    gaps: list[str] = Field(default_factory=list, max_length=100)
    assumptions: list[str] = Field(default_factory=list, max_length=100)
    risks: list[str] = Field(default_factory=list, max_length=100)
    generated_by: Literal[
        "web",
        "chatgpt_mcp",
        "whatsapp",
        "telegram",
        "api",
        "deterministic_rules",
    ] = "web"
    selected_model: str = Field(default="", max_length=120)
    updated_by: str = Field(min_length=2, max_length=120)


class ConfigurationAlternative(BaseModel):
    code: Literal["A", "B", "C"]
    title: str
    objective: str = ""
    status: Literal[
        "draft",
        "needs_validation",
        "ready_for_review",
        "approved",
        "rejected",
    ] = "draft"
    lines: list[ConfigurationLine] = Field(default_factory=list)
    supplier_cost_total: float = Field(default=0, ge=0)
    coverage: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    generated_by: str = ""
    selected_model: str = ""
    updated_by: str = ""
    reviewed_by: str = ""
    review_notes: str = ""
    updated_at: str
    revision: int = Field(default=1, ge=1)


class ConfigurationReviewRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)
    language: LanguageCode = "es"
    decision: Literal["approve", "reject"]
    reviewed_by: str = Field(min_length=2, max_length=120)
    notes: str = Field(default="", max_length=1000)


class DecisionWorkspace(BaseModel):
    status: Literal[
        "collecting_requirements",
        "drafting_alternatives",
        "needs_validation",
        "ready_for_review",
        "approved",
    ] = "collecting_requirements"
    requirements: list[TechnicalRequirement] = Field(default_factory=list)
    alternatives: list[ConfigurationAlternative] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    last_channel: ChannelCode = "web"
    selected_model: str = ""
    revision: int = Field(default=0, ge=0)


class ContextDossier(BaseModel):
    project: ProjectProfile = Field(default_factory=ProjectProfile)
    customer: DossierCustomer = Field(default_factory=DossierCustomer)
    commercial_profiles: list[CommercialPartyProfile] = Field(default_factory=list)
    site: DossierSite = Field(default_factory=DossierSite)
    confirmed_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    options: list[DossierOption] = Field(default_factory=list)
    supplier_offers: list[SupplierOffer] = Field(default_factory=list)
    sourcing_recommendations: list[SupplierSourcingRecommendation] = Field(default_factory=list)
    sourcing_policy_max_credit_premium_pct: float = Field(default=5, ge=0, le=100)
    catalog_drafts: list[CatalogDraftItem] = Field(default_factory=list)
    extracted_evidence: list[MultimodalEvidence] = Field(default_factory=list)
    decision_workspace: DecisionWorkspace = Field(default_factory=DecisionWorkspace)
    attachments: list[ConversationAttachment] = Field(default_factory=list)
    work_item: MissionWorkItem | None = None
    timeline: list[MissionTimelineEvent] = Field(default_factory=list, max_length=200)
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
    phase: Literal["discovery", "identity", "scope", "design", "quote", "approval", "delivery"]
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


class PublicProgressSummary(BaseModel):
    title: str = Field(max_length=200)
    status: Literal["active", "paused", "completed", "blocked"]
    phase: str = Field(max_length=160)
    progress_percent: int = Field(ge=0, le=100)


class PublicProgressVerification(BaseModel):
    tests_passed: int = Field(ge=0)
    tests_total: int = Field(ge=0)
    staging_status: Literal["healthy", "degraded", "offline", "not_verified"]
    commit: str = Field(pattern=r"^(?:unknown|[a-f0-9]{7,40})$")


class PublicProgressDecision(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=800)
    status: Literal["accepted", "reviewing", "superseded"]
    decided_at: str


class PublicProgressEvent(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    type: Literal["milestone", "commit", "verification", "decision", "release"]
    title: str = Field(max_length=200)
    summary: str = Field(max_length=800)
    status: Literal["completed", "in_progress", "blocked"]
    occurred_at: str
    evidence: dict[str, str] = Field(default_factory=dict)


class PublicIntegrationStatus(BaseModel):
    name: str = Field(max_length=80)
    status: Literal["ready", "ok", "warning", "error", "not_configured"]


class PublicProgressResponse(BaseModel):
    ok: bool = True
    project: Literal["ralphiia-quoteops"] = "ralphiia-quoteops"
    language: LanguageCode
    generated_at: str
    revision: str = Field(pattern=r"^[a-f0-9]{16}$")
    refresh_seconds: int = Field(ge=10, le=300)
    summary: PublicProgressSummary
    verification: PublicProgressVerification
    decisions: list[PublicProgressDecision] = Field(default_factory=list, max_length=30)
    events: list[PublicProgressEvent] = Field(default_factory=list, max_length=50)
    integrations: list[PublicIntegrationStatus] = Field(default_factory=list, max_length=20)
