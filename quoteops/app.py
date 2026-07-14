from __future__ import annotations

from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path
from platform import node

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from quoteops.adapters.openai_analysis import analyze_intake, build_fallback_analysis
from quoteops.adapters.ralfia_bridge import verify_stack
from quoteops.contracts import MissionState, QuoteIntake, QuoteIntakeAnalysis
from quoteops.reuse_catalog import reuse_summary
from quoteops.settings import get_settings

app = FastAPI(title="RalphiIA QuoteOps", version="0.2.0")
settings = get_settings()


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


@app.get("/api/reuse")
async def reuse() -> JSONResponse:
    return JSONResponse(reuse_summary())


@app.get("/api/reuse/verify")
async def reuse_verify() -> JSONResponse:
    result = await verify_stack()
    return JSONResponse(result)


@app.post("/api/intake/preview", response_model=QuoteIntakeAnalysis)
async def intake_preview(intake: QuoteIntake) -> QuoteIntakeAnalysis:
    return build_fallback_analysis(intake, settings)


@app.post("/api/intake/analyze", response_model=QuoteIntakeAnalysis)
async def intake_analyze(intake: QuoteIntake) -> QuoteIntakeAnalysis:
    return analyze_intake(intake, settings)
