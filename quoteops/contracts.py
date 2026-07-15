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
    model_used: str = "gpt-5.6"
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
