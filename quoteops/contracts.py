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
