from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from hashlib import sha256
import shutil
import subprocess
from threading import RLock
from time import monotonic
from typing import Any

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from quoteops.remote_dev_demo import (
    MAX_MEDIA_BYTES,
    CodexScenarioExecutor,
    DemoRegistry,
    LocalMediaProcessor,
    McpCoordinationGateway,
    OfflineCoordinationGateway,
    RemoteDevDemoService,
    SCENARIOS,
)
from quoteops.remote_dev_frontend import render_remote_dev_demo


class ApprovalRequest(BaseModel):
    checkpoint: str


class OwnerUnlockRequest(BaseModel):
    code: str


class DailyMemoryRequest(BaseModel):
    message: str
    privacy_scope: str = "PRIVATE_PERSONAL"
    conversation_label: str | None = None
    project: str | None = None


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5


class ChatRequest(BaseModel):
    request_id: str
    message: str
    lang: str = "es"


class DemoRateLimiter:
    """Small in-memory limiter; client identifiers are hashed and never logged."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}
        self._lock = RLock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> bool:
        now = monotonic()
        cutoff = now - window_seconds
        digest = sha256(key.encode()).hexdigest()
        with self._lock:
            recent = [stamp for stamp in self._hits.get(digest, []) if stamp >= cutoff]
            if len(recent) >= limit:
                self._hits[digest] = recent
                return False
            recent.append(now)
            self._hits[digest] = recent
            return True


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("CF-Connecting-IP", "").strip()
    return forwarded or (request.client.host if request.client else "unknown")


READ_ONLY_USER_SERVICES = (
    "ralfia-mcp.service",
    "whatsapp-automation.service",
    "ralfia-remote-dev-demo.service",
)
READ_ONLY_SYSTEM_SERVICES = ("nginx", "mongod")


def _service_state(args: list[str]) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3, check=False)
    except Exception as exc:
        return f"unavailable:{type(exc).__name__}"
    value = (result.stdout or result.stderr or "unknown").strip().splitlines()
    return (value[0] if value else "unknown")[:80]


def _safe_service_snapshot() -> dict[str, Any]:
    services: dict[str, str] = {}
    for name in READ_ONLY_USER_SERVICES:
        services[name] = _service_state(["systemctl", "--user", "is-active", name])
    for name in READ_ONLY_SYSTEM_SERVICES:
        services[name] = _service_state(["systemctl", "is-active", name])
    return {
        "server": ".4",
        "host": "192.168.1.4",
        "reachable": True,
        "services": services,
    }


def _remote_safe_service_snapshot(host: str, label: str) -> dict[str, Any]:
    remote_script = (
        "for s in ralfia-mcp.service whatsapp-automation.service "
        "evolution-api.service ralfia-remote-dev-demo.service; do "
        "printf '%s=' \"$s\"; systemctl --user is-active \"$s\" 2>/dev/null || echo unknown; done; "
        "for s in nginx mongod; do printf '%s=' \"$s\"; systemctl is-active \"$s\" 2>/dev/null || echo unknown; done"
    )
    try:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=3", f"rlopez@{host}", remote_script],
            capture_output=True,
            text=True,
            timeout=7,
            check=False,
        )
    except Exception as exc:
        return {"server": label, "host": host, "reachable": False, "error": type(exc).__name__, "services": {}}
    services: dict[str, str] = {}
    for line in (result.stdout or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            services[key[:80]] = value.strip()[:80]
    return {
        "server": label,
        "host": host,
        "reachable": result.returncode == 0,
        "services": services,
        "error": (result.stderr or "").strip()[:240] if result.returncode else None,
    }


def build_remote_dev_service(settings: Any) -> RemoteDevDemoService:
    mode = str(getattr(settings, "remote_dev_demo_mode", "offline")).lower()
    if mode == "mcp" and getattr(settings, "remote_dev_mcp_api_key", ""):
        coordination = McpCoordinationGateway(
            str(getattr(settings, "remote_dev_mcp_url", settings.ralfia_mcp_url)),
            str(settings.remote_dev_mcp_api_key),
        )
    else:
        coordination = OfflineCoordinationGateway()
    codex_bin = str(getattr(settings, "remote_dev_codex_bin", "")).strip()
    if not codex_bin:
        codex_bin = shutil.which("codex") or "/home/rlopez/.local/node_modules/.bin/codex"
    workspace_root = Path(getattr(settings, "remote_dev_workspace_root", "/tmp/ralfia-remote-dev-demo"))
    executor = CodexScenarioExecutor(
        workspace_root,
        codex_bin,
        enabled=bool(getattr(settings, "remote_dev_execute_codex", False)),
        timeout=int(getattr(settings, "remote_dev_timeout_seconds", 240)),
        model=str(getattr(settings, "remote_dev_model", "gpt-5.6-sol")),
    )
    media = LocalMediaProcessor(
        workspace_root / "media",
        whisper_url=str(getattr(settings, "remote_dev_whisper_url", "http://127.0.0.1:9001")),
    )
    return RemoteDevDemoService(
        DemoRegistry(),
        coordination,
        executor,
        media,
        owner_code_sha256=str(getattr(settings, "remote_dev_owner_code_sha256", "")),
    )


async def _call_mcp(settings: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    api_key = str(getattr(settings, "remote_dev_mcp_api_key", "") or "")
    url = str(getattr(settings, "remote_dev_mcp_url", getattr(settings, "ralfia_mcp_url", "")) or "")
    if not api_key or not url:
        raise RuntimeError("mcp_not_configured")
    transport = StreamableHttpTransport(url, headers={"X-API-Key": api_key})
    async with Client(transport, timeout=45) as client:
        result = await client.call_tool(name, arguments, raise_on_error=False)
    payload = result.data if isinstance(result.data, dict) else result.structured_content
    if result.is_error or not isinstance(payload, dict):
        raise RuntimeError(f"mcp_{name}_failed")
    if payload.get("ok") is False:
        raise RuntimeError(str(payload.get("error") or f"mcp_{name}_failed"))
    return payload


def build_remote_dev_router(settings: Any, service: RemoteDevDemoService | None = None) -> APIRouter:
    router = APIRouter()
    demo = service or build_remote_dev_service(settings)
    limiter = DemoRateLimiter()

    @router.get("/remote-dev-demo", response_class=HTMLResponse)
    async def remote_dev_demo_page() -> HTMLResponse:
        return HTMLResponse(render_remote_dev_demo())

    @router.get("/api/remote-dev/live-status")
    async def remote_dev_live_status() -> JSONResponse:
        checked_at = datetime.now(timezone.utc).isoformat()
        return JSONResponse(
            {
                "ok": True,
                "checked_at": checked_at,
                "policy": "read_only_allowlist_no_sudo_no_arbitrary_shell",
                "layers": ["Cloudflare/demo.pcdoctor.ai", "demo service :8766", "MCP :8102", "WhatsApp automation", "MongoDB"],
                "servers": [_safe_service_snapshot(), _remote_safe_service_snapshot("192.168.1.5", ".5")],
            }
        )

    @router.get("/api/remote-dev/capabilities")
    async def remote_dev_capabilities() -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "environment": "isolated_demo",
                "transport": "whatsapp_ui_emulator",
                "execution": "real_when_approved",
                "coordination": demo.coordination.mode,
                "model_requested": getattr(demo.executor, "model", None),
                "private_data": False,
                "production_access": False,
                "arbitrary_shell": False,
                "sudo": False,
                "scenarios": [
                    {
                        "scenario_id": item.scenario_id,
                        "label": item.label,
                        "agent": item.agent,
                        "allowed_tools": list(item.allowed_tools),
                        "scopes": list(item.scopes),
                    }
                    for item in SCENARIOS.values()
                ],
            }
        )

    @router.post("/api/remote-dev/sessions")
    async def create_remote_dev_session(request: Request) -> JSONResponse:
        if not limiter.allow(_client_key(request) + ":session", limit=6, window_seconds=600):
            raise HTTPException(status_code=429, detail="demo_rate_limit_reached")
        try:
            return JSONResponse(demo.create_session())
        except PermissionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/chat")
    async def remote_dev_chat(
        request: Request,
        session_id: str,
        payload: ChatRequest,
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            if not limiter.allow(_client_key(request) + ":chat", limit=60, window_seconds=600):
                raise PermissionError("demo_rate_limit_reached")
            return JSONResponse(
                demo.chat(
                    session_id,
                    session_token,
                    request_id=payload.request_id,
                    message=payload.message,
                    lang=payload.lang,
                )
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/messages")
    async def remote_dev_message(
        request: Request,
        session_id: str,
        request_id: str = Form(...),
        scenario_id: str = Form(...),
        message: str = Form(""),
        media: UploadFile | None = File(None),
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            if not limiter.allow(_client_key(request) + ":action", limit=30, window_seconds=600):
                raise PermissionError("demo_rate_limit_reached")
            media_data = await media.read(MAX_MEDIA_BYTES + 1) if media else None
            result = await demo.submit(
                session_id,
                session_token,
                request_id=request_id,
                scenario_id=scenario_id,
                message=message,
                media=media_data,
                media_type=media.content_type if media else None,
            )
            return JSONResponse(result)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/actions/{action_id}/approve")
    async def approve_remote_dev_action(
        http_request: Request,
        session_id: str,
        action_id: str,
        approval: ApprovalRequest,
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            if not limiter.allow(_client_key(http_request) + ":action", limit=30, window_seconds=600):
                raise PermissionError("demo_rate_limit_reached")
            result = await demo.approve(session_id, session_token, action_id, approval.checkpoint)
            return JSONResponse(result, status_code=200 if result.get("ok") else 409)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.get("/api/remote-dev/sessions/{session_id}")
    async def remote_dev_session(
        session_id: str,
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            return JSONResponse({"ok": True, "snapshot": demo.snapshot(session_id, session_token)})
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/media-preview")
    async def remote_dev_media_preview(
        request: Request,
        session_id: str,
        media: UploadFile = File(...),
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            if not limiter.allow(_client_key(request) + ":media", limit=20, window_seconds=600):
                raise PermissionError("demo_rate_limit_reached")
            demo.registry.require(session_id, session_token)
            media_data = await media.read(MAX_MEDIA_BYTES + 1)
            result = demo.media_processor.process(media_data, media.content_type or "")
            return JSONResponse({"ok": True, "media": result.__dict__})
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/owner-unlock")
    async def remote_dev_owner_unlock(
        session_id: str,
        payload: OwnerUnlockRequest,
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            return JSONResponse(demo.unlock_owner(session_id, session_token, payload.code))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/daily-memory")
    async def remote_dev_daily_memory(
        request: Request,
        session_id: str,
        payload: DailyMemoryRequest,
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            if not limiter.allow(_client_key(request) + ":memory", limit=20, window_seconds=600):
                raise PermissionError("demo_rate_limit_reached")
            session = demo.require_owner(session_id, session_token)
            text = str(payload.message or "").strip()
            if not text:
                raise ValueError("message_required")
            privacy = str(payload.privacy_scope or "PRIVATE_PERSONAL").upper()
            conversation_id = f"web-daily:{session.session_id}:{datetime.now(timezone.utc).date().isoformat()}"
            message_id = f"webmsg_{sha256((session.session_id + text).encode()).hexdigest()[:16]}"
            save_payload = {
                "owner_id": "RAFAEL",
                "conversation_id": conversation_id,
                "privacy_scope": privacy,
                "source": "ralfia_remote_dev_owner_mode",
                "actor": "RAFAEL",
                "messages": [{"role": "user", "content": text, "message_id": message_id}],
                "metadata": {"conversation_label": payload.conversation_label, "project": payload.project, "surface": "demo.pcdoctor.ai"},
            }
            saved = await _call_mcp(settings, "save_conversation_batch", {"payload": save_payload})
            finalized = await _call_mcp(
                settings,
                "finalize_conversation",
                {
                    "payload": {
                        "owner_id": "RAFAEL",
                        "conversation_id": conversation_id,
                        "privacy_scope": privacy,
                        "actor": "RAFAEL",
                        "project": payload.project,
                        "state_key": f"web:{privacy.lower()}",
                    }
                },
            )
            demo.registry.add_event(
                session,
                "daily_memory_saved",
                actor="ralfia-mcp",
                tool="save_conversation_batch+finalize_conversation",
                detail="Conversación real guardada en Daily Life Memory para consulta posterior desde WhatsApp/MCP.",
                evidence={"message_id": message_id, "correlation_id": conversation_id},
            )
            return JSONResponse({"ok": True, "conversation_id": conversation_id, "message_id": message_id, "save": saved, "finalize": finalized, "snapshot": demo.registry.snapshot(session)})
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("/api/remote-dev/sessions/{session_id}/daily-memory/search")
    async def remote_dev_daily_memory_search(
        request: Request,
        session_id: str,
        payload: MemorySearchRequest,
        session_token: str = Header(..., alias="X-Demo-Session-Token"),
    ) -> JSONResponse:
        try:
            if not limiter.allow(_client_key(request) + ":memory-search", limit=30, window_seconds=600):
                raise PermissionError("demo_rate_limit_reached")
            demo.require_owner(session_id, session_token)
            result = await _call_mcp(
                settings,
                "search_memory",
                {"query": payload.query, "owner_id": "RAFAEL", "actor": "RAFAEL", "limit": max(1, min(payload.limit, 10))},
            )
            return JSONResponse({"ok": True, "result": result})
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return router
