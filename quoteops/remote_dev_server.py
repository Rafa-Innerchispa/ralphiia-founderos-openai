"""Minimal public demo app: no QuoteOps production routes or data adapters."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from quoteops.remote_dev_api import build_remote_dev_router


class DemoSettings:
    remote_dev_demo_mode = os.getenv("REMOTE_DEV_DEMO_MODE", "offline")
    remote_dev_mcp_url = os.getenv("REMOTE_DEV_MCP_URL", "http://127.0.0.1:8102/mcp")
    ralfia_mcp_url = remote_dev_mcp_url
    remote_dev_mcp_api_key = os.getenv("REMOTE_DEV_MCP_API_KEY") or os.getenv("MCP_API_KEY", "")
    remote_dev_codex_bin = os.getenv("REMOTE_DEV_CODEX_BIN", "/home/rlopez/.local/node_modules/.bin/codex")
    remote_dev_execute_codex = os.getenv("REMOTE_DEV_EXECUTE_CODEX", "0").lower() in {"1", "true", "yes", "on"}
    remote_dev_workspace_root = os.getenv("REMOTE_DEV_WORKSPACE_ROOT", "/home/rlopez/worktrees/ralfia-public-demo")
    remote_dev_timeout_seconds = int(os.getenv("REMOTE_DEV_TIMEOUT_SECONDS", "240"))
    remote_dev_model = os.getenv("REMOTE_DEV_MODEL", "gpt-5.6-sol")
    remote_dev_whisper_url = os.getenv("REMOTE_DEV_WHISPER_URL", "http://127.0.0.1:9001")
    remote_dev_owner_code_sha256 = os.getenv("REMOTE_DEV_OWNER_CODE_SHA256", "")
    remote_dev_auto_owner_memory = os.getenv("REMOTE_DEV_AUTO_OWNER_MEMORY", "1").lower() in {"1", "true", "yes", "on"}


app = FastAPI(
    title="RalfIA FounderOS",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(build_remote_dev_router(DemoSettings()))


@app.middleware("http")
async def demo_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'self'"
    )
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@app.get("/healthz", include_in_schema=False)
async def healthz() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "ralfia-founderos",
            "environment": "live_control_plane",
            "mcp": DemoSettings.remote_dev_demo_mode == "mcp",
            "codex": DemoSettings.remote_dev_execute_codex,
            "model_requested": DemoSettings.remote_dev_model,
            "memory_available": DemoSettings.remote_dev_auto_owner_memory and bool(DemoSettings.remote_dev_owner_code_sha256),
        }
    )


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/founderos", status_code=307)
