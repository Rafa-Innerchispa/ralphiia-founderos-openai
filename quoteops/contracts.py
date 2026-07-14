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
