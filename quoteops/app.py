from __future__ import annotations

from datetime import datetime, timezone
from getpass import getuser
from hashlib import sha256
from pathlib import Path
from platform import node
import re
from time import perf_counter

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from quoteops.adapters.openai_analysis import analyze_intake, build_fallback_analysis
from quoteops.adapters.quote_execution import QuoteExecutionService
from quoteops.adapters.channel_intake import ChannelIntakeRouter
from quoteops.adapters.ralfia_bridge import verify_stack
from quoteops.adapters.smart_quoter import SmartQuoterAdapter
from quoteops.adapters.tool_planner import build_tool_plan
from quoteops.adapters.taxpayer_registry import TaxpayerRegistryError, normalize_ec_identifier
from quoteops.contracts import (
    ConversationMessageRequest,
    ConversationReply,
    CustomerIdentifierLookupRequest,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    QuoteIntake,
    QuoteIntakeAnalysis,
    PublicProgressResponse,
    QuoteUpdateRequest,
    QuoteToolPlan,
    RucConfirmationResult,
    RucConfirmRequest,
    RucLookupRequest,
    RucLookupResult,
)
from quoteops.conversation import ConversationService
from quoteops.customer_identity import CustomerIdentityService
from quoteops.frontend import render_cockpit_page
from quoteops.iess_payments import IessPaymentService
from quoteops.integration_trace import IntegrationTraceStore, seed_integration_traces
from quoteops.operations_dashboard import OperationsDashboardService
from quoteops.public_progress import PublicProgressFeed
from quoteops.reuse_catalog import reuse_summary
from quoteops.settings import get_settings

app = FastAPI(title="RalphiIA QuoteOps", version="0.6.0")
settings = get_settings()
_identity_service: CustomerIdentityService | None = None
_execution_service = QuoteExecutionService(settings)
_channel_router = ChannelIntakeRouter(settings.quoteops_webhook_secret)
_smart_quoter = SmartQuoterAdapter(settings.smart_quoter_base_url)
_iess_payments = IessPaymentService(settings)
_operations_dashboard = OperationsDashboardService(settings.mongo_uri)
_conversation = ConversationService(settings)
_trace_store = IntegrationTraceStore()
seed_integration_traces(
    _trace_store,
    settings,
    mongo_connected=_conversation.mongo_connected or _execution_service.db is not None,
)
_repo_root = Path(__file__).resolve().parents[1]
_public_progress = PublicProgressFeed(
    _repo_root / "docs" / "PUBLIC_PROGRESS.json",
    trace_store=_trace_store,
    repo_root=_repo_root,
)


@app.exception_handler(RequestValidationError)
async def localized_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    language = "en" if request.headers.get("x-quoteops-language", "").lower() == "en" else "es"
    message = (
        "Review the highlighted fields and try again."
        if language == "en"
        else "Revisa los campos indicados e inténtalo nuevamente."
    )
    errors = [
        {"field": ".".join(str(item) for item in error.get("loc", [])[1:]), "code": error.get("type", "invalid")}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": {"code": "validation_error", "message": message, "errors": errors}})


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


@app.get("/api/integrations/trace")
async def integrations_trace() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "runtime_label": _conversation.runtime_label,
            "items": _trace_store.snapshot(),
        }
    )


@app.get("/api/public/progress", response_model=PublicProgressResponse)
async def public_progress(response: Response, language: str = "es") -> PublicProgressResponse:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return PublicProgressResponse.model_validate(_public_progress.snapshot(language))


@app.post("/api/conversation/messages", response_model=ConversationReply)
async def conversation_message(request: ConversationMessageRequest) -> ConversationReply:
    started = perf_counter()
    try:
        result = _conversation.message(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=_mission_error(str(exc), request.language)) from exc
    _trace_store.record(
        "MongoDB",
        source=settings.quoteops_mongo_db,
        call="upsert conversation mission",
        status="ok" if _conversation.mongo_connected else "warning",
        latency_ms=(perf_counter() - started) * 1000,
        result="Mission persisted in staging" if _conversation.mongo_connected else "Mission retained in process memory",
    )
    return result


@app.get("/api/conversation/missions/{mission_id}", response_model=ConversationReply)
async def conversation_mission(mission_id: str, language: str = "es") -> ConversationReply:
    try:
        return _conversation.get(mission_id, language if language in {"es", "en"} else "es")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=_mission_error("mission_not_found", language)) from exc


@app.put("/api/conversation/missions/{mission_id}/quote", response_model=ConversationReply)
async def conversation_quote_update(mission_id: str, request: QuoteUpdateRequest) -> ConversationReply:
    try:
        return _conversation.update_quote(mission_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=_mission_error("mission_not_found", request.language)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=_mission_error(str(exc), request.language)) from exc


@app.post("/api/conversation/missions/{mission_id}/attachments", response_model=ConversationReply)
async def conversation_attachment(
    mission_id: str,
    file: UploadFile = File(...),
    language: str = Form("es"),
) -> ConversationReply:
    locale = language if language in {"es", "en"} else "es"
    try:
        _conversation.get(mission_id, locale)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=_mission_error("mission_not_found", locale)) from exc
    original_name = Path(file.filename or "attachment").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", original_name)[:160] or "attachment"
    content = bytearray()
    while chunk := await file.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > 25_000_000:
            message = "El archivo supera el límite de 25 MB." if locale == "es" else "The file exceeds the 25 MB limit."
            raise HTTPException(status_code=413, detail={"code": "attachment_too_large", "message": message})
    digest = sha256(content).hexdigest()
    storage_id = "attachment_" + digest[:18]
    root = Path(settings.quoteops_artifact_root) / "attachments" / mission_id
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{storage_id}_{safe_name}").write_bytes(bytes(content))
    return _conversation.record_attachment(
        mission_id,
        {
            "name": original_name[:240],
            "media_type": str(file.content_type or "application/octet-stream")[:120],
            "size_bytes": len(content),
            "storage_id": storage_id,
            "sha256": digest,
            "status": "stored",
        },
        locale,
    )


@app.post("/api/conversation/missions/{mission_id}/approve")
async def conversation_quote_approve(mission_id: str, request: MissionApprovalRequest) -> JSONResponse:
    started = perf_counter()
    try:
        result = _conversation.approve(mission_id, request, _execution_service)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=_mission_error("mission_not_found", request.language)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=_mission_error(str(exc), request.language)) from exc
    _trace_store.record(
        "PDF",
        source=settings.quoteops_artifact_root,
        call="human approval and PDF generation",
        status="ok",
        latency_ms=(perf_counter() - started) * 1000,
        result=f"Artifact {result['approval']['artifact_id']} created",
    )
    return JSONResponse(result)


@app.post("/api/conversation/missions/{mission_id}/deliver")
async def conversation_quote_deliver(mission_id: str, request: MissionDeliveryRequest) -> JSONResponse:
    try:
        result = _conversation.deliver(mission_id, request, _execution_service)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=_mission_error("mission_not_found", request.language)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=_mission_error(str(exc), request.language)) from exc
    return JSONResponse(result)


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


@app.post("/api/customer/lookup")
async def customer_lookup(request: CustomerIdentifierLookupRequest) -> JSONResponse:
    started = perf_counter()
    try:
        identifier, identifier_type = normalize_ec_identifier(request.identifier)
    except TaxpayerRegistryError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_identity_error(exc.code, request.language),
        ) from exc

    if identifier_type == "cedula":
        matches = await _get_identity_service().identity_reader.resolve(identifier)
        sources = sorted({item.source for item in matches})
        name = next((item.legal_name for item in matches if item.legal_name), "")
        status = "locally_valid"
        source = ", ".join(sources) if sources else "local_validation"
        _conversation.set_customer_identity(
            request.mission_id,
            identifier=identifier,
            identifier_type=identifier_type,
            name=name,
            verification_status=status,
            source=source,
        )
        _trace_store.record(
            "Contífico",
            source=settings.ralfia_package_root,
            call="read-only identity reconciliation",
            status="ok",
            latency_ms=(perf_counter() - started) * 1000,
            result=f"{len(matches)} existing match(es); Intuito RUC endpoint not called",
        )
        return JSONResponse(
            {
                "ok": True,
                "identifier": identifier,
                "identifier_type": identifier_type,
                "local_validation": "valid",
                "provider_lookup": "not_applicable",
                "provider_called": False,
                "matches": [item.model_dump() for item in matches],
                "duplicate_risk": len(matches) > 1,
            }
        )

    try:
        result = await _get_identity_service().lookup(
            RucLookupRequest(ruc=identifier, force_refresh=request.force_refresh, mode="owner")
        )
    except TaxpayerRegistryError as exc:
        _trace_store.record(
            "Intuito",
            source=settings.ruc_api_lookup_base_url,
            call="authorized RUC lookup",
            status="error",
            latency_ms=(perf_counter() - started) * 1000,
            result=exc.code,
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail={**_identity_error(exc.code, request.language), "retryable": exc.retryable},
        ) from exc

    name = result.verification.legal_name
    sources = sorted({item.source for item in result.comparison.matches})
    _conversation.set_customer_identity(
        request.mission_id,
        identifier=identifier,
        identifier_type=identifier_type,
        name=name,
        verification_status="verified",
        source="Intuito" + (" + " + ", ".join(sources) if sources else ""),
    )
    latency_ms = (perf_counter() - started) * 1000
    _trace_store.record(
        "Intuito",
        source=settings.ruc_api_lookup_base_url,
        call="authorized RUC lookup",
        status="ok",
        latency_ms=latency_ms,
        result=f"Verified from {result.verification.cache_status}; provider result sanitized",
    )
    _trace_store.record(
        "Contífico",
        source=settings.ralfia_package_root,
        call="read-only identity reconciliation",
        status="ok",
        latency_ms=latency_ms,
        result=f"{len(result.comparison.matches)} match(es), {len(result.comparison.conflicts)} conflict(s)",
    )
    return JSONResponse(
        {
            "ok": True,
            "identifier": identifier,
            "identifier_type": identifier_type,
            "local_validation": "valid",
            "provider_lookup": "verified",
            "provider_called": True,
            "verification": result.verification.model_dump(),
            "comparison": result.comparison.model_dump(),
            "customer_draft": result.customer_draft.model_dump(),
            "trace_id": result.trace_id,
            "approval_required": result.approval_required,
        }
    )


@app.post("/api/ruc/lookup", response_model=RucLookupResult)
async def ruc_lookup(request: RucLookupRequest) -> RucLookupResult:
    started = perf_counter()
    try:
        result = await _get_identity_service().lookup(request)
        _trace_store.record(
            "Intuito",
            source=settings.ruc_api_lookup_base_url,
            call="authorized RUC lookup",
            status="ok",
            latency_ms=(perf_counter() - started) * 1000,
            result=f"Verified from {result.verification.cache_status}; provider result sanitized",
        )
        return result
    except TaxpayerRegistryError as exc:
        _trace_store.record(
            "Intuito",
            source=settings.ruc_api_lookup_base_url,
            call="authorized RUC lookup",
            status="error",
            latency_ms=(perf_counter() - started) * 1000,
            result=exc.code,
        )
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


def _mission_error(code: str, language: str) -> dict[str, str]:
    messages = {
        "es": {
            "message_or_attachment_required": "Escribe un mensaje o adjunta al menos un archivo.",
            "mission_not_found": "No se encontró el expediente solicitado.",
            "quote_pricing_required": "Completa todos los precios reales antes de aprobar.",
            "customer_identity_required": "Valida la cédula o RUC antes de aprobar.",
            "approval_required": "La cotización necesita aprobación humana antes de entregarse.",
            "approval_blocked": "La aprobación quedó bloqueada por datos faltantes.",
            "delivery_blocked": "La entrega no pudo registrarse.",
        },
        "en": {
            "message_or_attachment_required": "Write a message or attach at least one file.",
            "mission_not_found": "The requested case file was not found.",
            "quote_pricing_required": "Enter every real price before approval.",
            "customer_identity_required": "Validate the national ID or RUC before approval.",
            "approval_required": "The quote needs human approval before delivery.",
            "approval_blocked": "Approval was blocked by missing information.",
            "delivery_blocked": "Delivery could not be registered.",
        },
    }
    locale = language if language in messages else "es"
    return {"code": code, "message": messages[locale].get(code, messages[locale]["approval_blocked"])}


def _identity_error(code: str, language: str) -> dict[str, str]:
    es = {
        "invalid_ec_identifier": "La cédula o RUC no supera la validación local ecuatoriana.",
        "ruc_provider_not_configured": "La consulta RUC en vivo no está habilitada en el servidor.",
        "ruc_not_found": "Intuito no encontró información válida para ese RUC.",
        "taxpayer_information_missing": "El RUC existe, pero Intuito reporta información faltante.",
    }
    en = {
        "invalid_ec_identifier": "The national ID or RUC did not pass local Ecuadorian validation.",
        "ruc_provider_not_configured": "Live RUC lookup is not enabled on this server.",
        "ruc_not_found": "Intuito did not find valid information for that RUC.",
        "taxpayer_information_missing": "The RUC exists, but Intuito reports missing information.",
    }
    catalog = en if language == "en" else es
    fallback = "The identity provider returned an error." if language == "en" else "El proveedor de identidad devolvió un error."
    return {"code": code, "message": catalog.get(code, fallback)}


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
    for result in reuse_verify_payload.get("results", []):
        if result.get("name") == "raphiia-mcp":
            _trace_store.record(
                "MCP",
                source=result.get("url", settings.ralfia_mcp_url),
                call="availability handshake",
                status="ok" if result.get("ok") else "error",
                latency_ms=result.get("latency_ms", 0),
                result=result.get("result", ""),
            )
        elif result.get("name") == "smart-quoter":
            _trace_store.record(
                "Smart Quoter",
                source=result.get("url", settings.smart_quoter_base_url),
                call="read-only availability check",
                status="ok" if result.get("ok") else "error",
                latency_ms=result.get("latency_ms", 0),
                result=result.get("result", ""),
            )
    return {
        "meta": meta_payload,
        "reuse": reuse_payload,
        "reuse_verify": reuse_verify_payload,
        "runtime_label": _conversation.runtime_label,
        "integration_traces": _trace_store.snapshot(),
    }
