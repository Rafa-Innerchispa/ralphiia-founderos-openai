from typing import Literal
from pydantic import BaseModel, Field


class QuoteIntake(BaseModel):
    source_channel: Literal["whatsapp", "web", "sandbox"] = "sandbox"
    customer_name: str = Field(default="", description="Nombre del cliente o solicitante")
    contact: str = Field(default="", description="Teléfono, correo o referencia")
    original_text: str = Field(default="", description="Texto crudo del mensaje o transcripción")
    attachments: list[str] = Field(default_factory=list)


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
    ruc: str
    force_refresh: bool = False
    mode: Literal["owner", "sandbox"] = "owner"


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
    ruc: str
    approved_by: str = Field(min_length=2, max_length=120)
    expected_verification_id: str


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
