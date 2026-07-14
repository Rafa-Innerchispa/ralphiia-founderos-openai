"""Small bridge to verify and reuse the existing Ralphi IA stack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class BridgeTarget:
    name: str
    url: str


DEFAULT_TARGETS: tuple[BridgeTarget, ...] = (
    BridgeTarget(name="raphiia-health", url="http://127.0.0.1:8101/status"),
    BridgeTarget(name="raphiia-mcp", url="http://127.0.0.1:8102/mcp"),
    BridgeTarget(name="smart-quoter", url="http://127.0.0.1:2026/"),
)


async def check_target(client: httpx.AsyncClient, target: BridgeTarget) -> dict[str, Any]:
    response = await client.get(target.url, timeout=5.0)
    body_preview = response.text[:200] if response.text else ""
    return {
        "name": target.name,
        "url": target.url,
        "status_code": response.status_code,
        "ok": response.is_success,
        "body_preview": body_preview,
    }


async def verify_stack(targets: tuple[BridgeTarget, ...] = DEFAULT_TARGETS) -> dict[str, Any]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        results = [await check_target(client, target) for target in targets]
    return {
        "ok": all(result["ok"] for result in results),
        "results": results,
    }
