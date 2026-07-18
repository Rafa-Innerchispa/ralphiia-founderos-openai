from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import shutil
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
    return RemoteDevDemoService(DemoRegistry(), coordination, executor, media)


def build_remote_dev_router(settings: Any, service: RemoteDevDemoService | None = None) -> APIRouter:
    router = APIRouter()
    demo = service or build_remote_dev_service(settings)
    limiter = DemoRateLimiter()

    @router.get("/remote-dev-demo", response_class=HTMLResponse)
    async def remote_dev_demo_page() -> HTMLResponse:
        return HTMLResponse(render_remote_dev_demo())

    @router.get("/api/remote-dev/capabilities")
    async def remote_dev_capabilities() -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "environment": "isolated_demo",
                "transport": "whatsapp_ui_emulator",
                "execution": "real_when_approved",
                "coordination": demo.coordination.mode,
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

    return router
