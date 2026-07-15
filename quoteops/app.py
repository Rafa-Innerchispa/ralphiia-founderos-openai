from __future__ import annotations

from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path
from platform import node

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from quoteops.adapters.openai_analysis import analyze_intake, build_fallback_analysis
from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.adapters.ralfia_bridge import verify_stack
from quoteops.adapters.tool_planner import build_tool_plan
from quoteops.adapters.taxpayer_registry import TaxpayerRegistryError
from quoteops.contracts import (
    QuoteIntake,
    QuoteIntakeAnalysis,
    QuoteToolPlan,
    RucConfirmationResult,
    RucConfirmRequest,
    RucLookupRequest,
    RucLookupResult,
)
from quoteops.customer_identity import CustomerIdentityService
from quoteops.frontend import render_cockpit_page
from quoteops.reuse_catalog import reuse_summary
from quoteops.settings import get_settings

app = FastAPI(title="RalphiIA QuoteOps", version="0.4.0")
settings = get_settings()
_identity_service: CustomerIdentityService | None = None
_execution_service = QuoteExecutionService(settings)


@app.get("/")
async def home() -> HTMLResponse:
    return HTMLResponse(render_cockpit_page(await build_bootstrap()))


@app.get("/cockpit")
async def cockpit() -> HTMLResponse:
    return HTMLResponse(render_cockpit_page(await build_bootstrap()))


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


@app.get("/api/ui/bootstrap")
async def ui_bootstrap() -> JSONResponse:
    return JSONResponse(await build_bootstrap())


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


@app.post("/api/plan", response_model=QuoteToolPlan)
async def intake_plan(intake: QuoteIntake) -> QuoteToolPlan:
    return build_tool_plan(intake)


@app.get("/api/ruc/status")
async def ruc_status() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "live_enabled": settings.ruc_api_live_enabled,
            "credentials_configured": bool(
                settings.ruc_api_username and settings.ruc_api_password
            ),
            "persistence_target": settings.quoteops_mongo_db,
            "production_writes_enabled": settings.allow_production_writes,
        }
    )


@app.post("/api/ruc/lookup", response_model=RucLookupResult)
async def ruc_lookup(request: RucLookupRequest) -> RucLookupResult:
    try:
        return await _get_identity_service().lookup(request)
    except TaxpayerRegistryError as exc:
        trace_id = "trace_ruc_error"
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "message": exc.public_message,
                "retryable": exc.retryable,
                "trace_id": trace_id,
            },
        ) from exc


@app.post("/api/ruc/confirm", response_model=RucConfirmationResult)
async def ruc_confirm(request: RucConfirmRequest) -> RucConfirmationResult:
    try:
        return await _get_identity_service().confirm(request)
    except TaxpayerRegistryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.public_message},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "verification_not_found_or_stale",
                "message": "La verificación debe repetirse antes de confirmar.",
            },
        ) from exc


@app.post("/api/quote/approve")
async def quote_approve(request: dict) -> JSONResponse:
    return JSONResponse(_execution_service.approve(request))


@app.get("/api/quote/artifacts/{artifact_id}.pdf")
async def quote_artifact(artifact_id: str) -> FileResponse:
    path = _execution_service.artifact_path(artifact_id)
    if not path:
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.post("/api/quote/deliver")
async def quote_deliver(request: dict) -> JSONResponse:
    return JSONResponse(_execution_service.deliver(request))


def _get_identity_service() -> CustomerIdentityService:
    global _identity_service
    if _identity_service is None:
        _identity_service = CustomerIdentityService(settings)
    return _identity_service


async def build_bootstrap() -> dict[str, object]:
    meta_payload = {
        "ok": True,
        "project": "ralphiia-quoteops",
        "correlation_id": "openai-build-week-quoteops-20260714",
        "task_id": "ops_202172a3b4c8",
        "repo_path": "/home/rlopez/projects/ralphiia-quoteops",
        "milestones": ["H1", "H2", "H3", "H4", "H5", "H6", "H7"],
    }
    reuse_payload = reuse_summary()
    reuse_verify_payload = await verify_stack()
    return {
        "meta": meta_payload,
        "reuse": reuse_payload,
        "reuse_verify": reuse_verify_payload,
    }
