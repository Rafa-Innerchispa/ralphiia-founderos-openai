from __future__ import annotations

from datetime import datetime, timezone
import re
from threading import RLock
from typing import Any


class IntegrationTraceStore:
    """Latest observed, sanitized status for each user-visible integration."""

    ORDER = ("MCP", "Intuito", "Contífico", "Smart Quoter", "MongoDB", "PDF")

    def __init__(self) -> None:
        self._lock = RLock()
        self._latest: dict[str, dict[str, Any]] = {}

    def record(
        self,
        integration: str,
        *,
        source: str,
        call: str,
        status: str,
        latency_ms: float = 0,
        result: str = "",
    ) -> dict[str, Any]:
        event = {
            "integration": integration,
            "source": self._sanitize(source, 220),
            "call": self._sanitize(call, 160),
            "status": status if status in {"ready", "ok", "warning", "error", "not_configured"} else "warning",
            "latency_ms": round(max(0, float(latency_ms)), 1),
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result": self._sanitize(result, 240),
        }
        with self._lock:
            self._latest[integration] = event
        return event

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(self._latest[name]) for name in self.ORDER if name in self._latest]

    @staticmethod
    def _sanitize(value: Any, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        text = re.sub(r"(?i)(bearer|token|password|secret|api[_-]?key)\s*[:=]?\s*[^ ,;]+", r"\1=[redacted]", text)
        return text[:limit]


def seed_integration_traces(store: IntegrationTraceStore, settings, *, mongo_connected: bool) -> None:
    store.record(
        "MCP",
        source=settings.ralfia_mcp_url,
        call="availability handshake",
        status="ready",
        result="Awaiting observed request",
    )
    store.record(
        "Intuito",
        source=settings.ruc_api_lookup_base_url,
        call="server-side configuration check",
        status="ready" if settings.ruc_api_live_enabled and settings.ruc_api_username and settings.ruc_api_password else "not_configured",
        result="Live RUC lookup enabled" if settings.ruc_api_live_enabled and settings.ruc_api_username and settings.ruc_api_password else "Live credentials are not enabled",
    )
    store.record(
        "Contífico",
        source=settings.ralfia_package_root,
        call="read-only identity adapter",
        status="ready",
        result="Lookup runs only after a valid identifier",
    )
    store.record(
        "Smart Quoter",
        source=settings.smart_quoter_base_url,
        call="read-only availability check",
        status="ready",
        result="Diagnosis and refinement only; writes blocked",
    )
    store.record(
        "MongoDB",
        source=settings.quoteops_mongo_db,
        call="staging database ping",
        status="ok" if mongo_connected else "warning",
        result="Staging persistence connected" if mongo_connected else "In-memory continuity active; staging database unavailable",
    )
    store.record(
        "PDF",
        source=settings.quoteops_artifact_root,
        call="local PDF artifact writer",
        status="ready",
        result="Generated only after human approval",
    )
