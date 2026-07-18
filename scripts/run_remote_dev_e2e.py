#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from quoteops.remote_dev_demo import (
    CodexScenarioExecutor,
    DemoRegistry,
    LocalMediaProcessor,
    McpCoordinationGateway,
    RemoteDevDemoService,
)


async def main() -> int:
    env_path = Path(os.getenv("RALFIA_BRIDGE_ENV", "/home/rlopez/projects/raphiia-openai/.env"))
    load_dotenv(env_path)
    api_key = os.getenv("REMOTE_DEV_MCP_API_KEY") or os.getenv("MCP_API_KEY")
    if not api_key:
        print(json.dumps({"ok": False, "error": "mcp_api_key_not_available"}))
        return 2

    root = Path(os.getenv("REMOTE_DEV_WORKSPACE_ROOT", "/tmp/ralfia-remote-dev-e2e"))
    codex_bin = os.getenv("REMOTE_DEV_CODEX_BIN", "/home/rlopez/.local/node_modules/.bin/codex")
    service = RemoteDevDemoService(
        DemoRegistry(),
        McpCoordinationGateway(os.getenv("REMOTE_DEV_MCP_URL", "http://127.0.0.1:8102/mcp"), api_key),
        CodexScenarioExecutor(root, codex_bin, enabled=True, timeout=240, model=os.getenv("REMOTE_DEV_MODEL", "gpt-5.6-sol")),
        LocalMediaProcessor(root / "media", os.getenv("REMOTE_DEV_WHISPER_URL", "http://127.0.0.1:9001")),
    )
    session = service.create_session()
    submitted = await service.submit(
        session["session_id"],
        session["session_token"],
        request_id="openai-demo-e2e-text-v1",
        scenario_id="fix_quote_total",
        message="codex: corrige el total de cotización y ejecuta las pruebas",
    )
    completed = await service.approve(
        session["session_id"],
        session["session_token"],
        submitted["action"]["action_id"],
        submitted["action"]["checkpoint"],
    )
    action = completed["action"]
    evidence = {
        "ok": completed["ok"],
        "session_id": session["session_id"],
        "message_id": action["message_id"],
        "correlation_id": action["correlation_id"],
        "task_id": action["task_id"],
        "job_id": action.get("job_id"),
        "commit": action.get("commit"),
        "tests": action.get("tests"),
        "summary": action.get("summary"),
        "model_requested": action.get("model_requested"),
        "codex_thread_id": action.get("codex_thread_id"),
        "usage": action.get("usage"),
        "latency_ms": action.get("latency_ms"),
        "status": action.get("status"),
        "event_count": len(completed["snapshot"]["events"]),
        "coordination_mode": service.coordination.mode,
        "workspace_root": str(root),
        "paid_api_calls": 0,
    }
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if completed["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
