from __future__ import annotations

from datetime import datetime, timezone
from getpass import getuser
from pathlib import Path
from platform import node

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from quoteops.adapters.openai_analysis import analyze_intake, build_fallback_analysis
from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.adapters.channel_intake import ChannelIntakeRouter
from quoteops.adapters.ralfia_bridge import verify_stack
from quoteops.adapters.smart_quoter import SmartQuoterAdapter
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
from quoteops.iess_payments import IessPaymentService
from quoteops.operations_dashboard import OperationsDashboardService
from quoteops.reuse_catalog import reuse_summary
from quoteops.settings import get_settings

app = FastAPI(title="RalphiIA QuoteOps", version="0.4.0")
settings = get_settings()
_identity_service: CustomerIdentityService | None = None
_execution_service = QuoteExecutionService(settings)
_channel_router = ChannelIntakeRouter(settings.quoteops_webhook_secret)
_smart_quoter = SmartQuoterAdapter(settings.smart_quoter_base_url)
_iess_payments = IessPaymentService(settings)
_operations_dashboard = OperationsDashboardService(settings.mongo_uri)


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


@app.get("/api/operations/summary")
async def operations_summary() -> JSONResponse:
    """Expose a sanitized, read-only projection of staging operations."""
    try:
        return JSONResponse(_operations_dashboard.snapshot())
    except Exception:
        raise HTTPException(
            status_code=503,
            detail={"code": "operations_summary_unavailable", "message": "No se pudo leer el resumen operativo."},
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


@app.get("/api/smart-quoter/client/{client_id}")
async def smart_quoter_client_lookup(client_id: str) -> JSONResponse:
    """Read-only lookup through the existing Smart Quoter 2026 service."""
    return JSONResponse(await _smart_quoter.client_lookup(client_id))


@app.post("/api/smart-quoter/diagnose")
async def smart_quoter_diagnose(request: dict) -> JSONResponse:
    """Reuse Smart Quoter's local diagnostic engine without writing a quote."""
    transcription = str(request.get("transcription") or "").strip()
    if not transcription:
        raise HTTPException(status_code=422, detail="transcription_required")
    return JSONResponse(await _smart_quoter.diagnose(transcription))


@app.post("/api/smart-quoter/refine")
async def smart_quoter_refine(request: dict) -> JSONResponse:
    analysis = request.get("current_analysis")
    prompt = str(request.get("prompt") or "").strip()
    if not isinstance(analysis, dict) or not prompt:
        raise HTTPException(status_code=422, detail="analysis_and_prompt_required")
    return JSONResponse(await _smart_quoter.refine(analysis, prompt))


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


@app.post("/api/intake/channel")
async def channel_intake(request: dict) -> JSONResponse:
    channel = str(request.get("channel") or "web")
    payload = request.get("payload") or {}
    return JSONResponse(_channel_router.ingest(channel, payload, str(request.get("signature") or "")))


@app.post("/api/mcp/quoteops_intake")
async def mcp_quoteops_intake(request: dict) -> JSONResponse:
    """Typed bridge for an authorized MCP client; no arbitrary tool execution."""
    channel = str(request.get("channel") or "chatgpt_mcp")
    payload = request.get("payload") or {}
    return JSONResponse(_channel_router.ingest(channel, payload, str(request.get("signature") or "")))


@app.post("/api/webhooks/whatsapp")
async def whatsapp_webhook(request: dict) -> JSONResponse:
    return JSONResponse(_channel_router.ingest("whatsapp", request, str(request.get("signature") or "")))


@app.post("/api/webhooks/telegram")
async def telegram_webhook(request: dict) -> JSONResponse:
    return JSONResponse(_channel_router.ingest("telegram", request, str(request.get("signature") or "")))


def _allow_iess_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    provided = request.headers.get("x-quoteops-webhook-secret", "")
    return host in {"127.0.0.1", "::1", "localhost"} or bool(settings.quoteops_webhook_secret and provided == settings.quoteops_webhook_secret)


@app.post("/api/iess/whatsapp-preview")
async def iess_whatsapp_preview(request: Request) -> JSONResponse:
    if not _allow_iess_local_request(request):
        return JSONResponse({"ok": False, "error": "local_or_signed_request_required"}, status_code=403)
    return JSONResponse(_iess_payments.preview(await request.json()))


@app.post("/api/iess/confirm")
async def iess_confirm(request: Request) -> JSONResponse:
    if not _allow_iess_local_request(request):
        return JSONResponse({"ok": False, "error": "local_or_signed_request_required"}, status_code=403)
    payload = await request.json()
    return JSONResponse(
        _iess_payments.confirm(
            str(payload.get("action_id") or ""),
            str(payload.get("approved_by") or "RAFAEL"),
            str(payload.get("request_sender") or ""),
        )
    )


@app.post("/api/iess/cancel")
async def iess_cancel(request: Request) -> JSONResponse:
    if not _allow_iess_local_request(request):
        return JSONResponse({"ok": False, "error": "local_or_signed_request_required"}, status_code=403)
    payload = await request.json()
    return JSONResponse(
        _iess_payments.cancel(
            str(payload.get("action_id") or ""),
            str(payload.get("request_sender") or ""),
        )
    )


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
