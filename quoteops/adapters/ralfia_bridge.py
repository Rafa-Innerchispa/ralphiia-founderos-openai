"""Small bridge to verify and reuse the existing Ralphi IA stack."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import httpx


@dataclass(frozen=True)
class BridgeTarget:
    name: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    acceptable_statuses: tuple[int, ...] = (200,)


DEFAULT_TARGETS: tuple[BridgeTarget, ...] = (
    BridgeTarget(name="raphiia-health", url="http://127.0.0.1:8101/status"),
    BridgeTarget(
        name="raphiia-mcp",
        url="http://127.0.0.1:8102/mcp",
        headers={"Accept": "text/event-stream"},
        acceptable_statuses=(200, 400, 406),
    ),
    BridgeTarget(name="smart-quoter", url="http://127.0.0.1:2026/"),
)


async def check_target(client: httpx.AsyncClient, target: BridgeTarget) -> dict[str, Any]:
    started = perf_counter()
    try:
        response = await client.get(target.url, timeout=5.0, headers=target.headers)
    except httpx.HTTPError as exc:
        return {
            "name": target.name,
            "url": target.url,
            "status_code": 0,
            "ok": False,
            "protocol_hint": "unavailable",
            "latency_ms": round((perf_counter() - started) * 1000, 1),
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result": type(exc).__name__,
        }
    live = response.status_code in target.acceptable_statuses
    protocol_hint = "streamable-http handshake required" if target.name == "raphiia-mcp" and response.status_code != 200 else "ok"
    return {
        "name": target.name,
        "url": target.url,
        "status_code": response.status_code,
        "ok": live,
        "protocol_hint": protocol_hint,
        "latency_ms": round((perf_counter() - started) * 1000, 1),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "result": f"HTTP {response.status_code}; {protocol_hint}",
    }


async def verify_stack(targets: tuple[BridgeTarget, ...] = DEFAULT_TARGETS) -> dict[str, Any]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        results = [await check_target(client, target) for target in targets]
    return {
        "ok": all(result["ok"] for result in results),
        "results": results,
    }
