from __future__ import annotations

from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path
from platform import node

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from quoteops.contracts import MissionState, QuoteIntake, QuoteReview, ProposalOption, TechnicalRisk, MissingInformation
from quoteops.settings import get_settings

app = FastAPI(title="RalphiIA QuoteOps", version="0.1.0")
settings = get_settings()


class IntakePreviewResponse(BaseModel):
    ok: bool = True
    mission: MissionState
    intake: QuoteIntake
    missing_information: MissingInformation = Field(default_factory=MissingInformation)
    technical_risks: TechnicalRisk = Field(default_factory=TechnicalRisk)
    proposal_options: list[ProposalOption] = Field(default_factory=list)
    review: QuoteReview = Field(default_factory=QuoteReview)
    next_action: str = "Expand intake and connect GPT-5.6 in H2"


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "RalphiIA QuoteOps",
            "host": node(),
            "user": getuser(),
            "path": str(Path.cwd()),
            "env": settings.env,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/api/meta")
async def meta() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "project": "ralphiia-quoteops",
            "correlation_id": "openai-build-week-quoteops-20260714",
            "task_id": "ops_202172a3b4c8",
            "repo_path": "/home/rlopez/projects/ralphiia-quoteops",
            "milestones": ["H1", "H2", "H3", "H4", "H5", "H6", "H7"],
        }
    )


@app.post("/api/intake/preview", response_model=IntakePreviewResponse)
async def intake_preview(intake: QuoteIntake) -> IntakePreviewResponse:
    mission = MissionState(
        mission_id="mission_preview_0001",
        correlation_id="openai-build-week-quoteops-20260714",
    )

    missing = []
    if not intake.customer_name:
        missing.append("customer_name")
    if not intake.contact:
        missing.append("contact")
    if not intake.original_text:
        missing.append("original_text")

    risks = []
    if intake.original_text and len(intake.original_text) < 40:
        risks.append("Input too short for reliable technical analysis")

    options = [
        ProposalOption(
            code="A",
            title="Baseline assisted quote",
            summary="Quick deterministic scaffold for straightforward requests.",
            estimated_value="TBD",
        ),
        ProposalOption(
            code="B",
            title="Context-rich quote",
            summary="Uses selective retrieval and structured review before drafting.",
            estimated_value="TBD",
        ),
    ]

    return IntakePreviewResponse(
        mission=mission,
        intake=intake,
        missing_information=MissingInformation(items=missing),
        technical_risks=TechnicalRisk(items=risks),
        proposal_options=options,
    )
