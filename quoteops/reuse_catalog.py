"""Catálogo de reutilización para QuoteOps.

This module keeps the project honest about what is reused from the
existing Ralphi IA stack and what is actually new for the hackathon.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ReuseItem:
    kind: str
    name: str
    description: str
    owner: str
    source: str
    status: str = "existing"


REUSE_CATALOG: tuple[ReuseItem, ...] = (
    ReuseItem(
        kind="service",
        name="raphiia-openai",
        description="Core Ralphi IA FastAPI/MCP stack.",
        owner="CODEX/CURSOR",
        source="/home/rlopez/projects/raphiia-openai",
    ),
    ReuseItem(
        kind="service",
        name="RalfIA MCP",
        description="Existing MCP transport and quote-related tools.",
        owner="CODEX",
        source="http://127.0.0.1:8102/mcp",
    ),
    ReuseItem(
        kind="service",
        name="Smart Quoter",
        description="Quote delivery and quote UI flow already in production-like use.",
        owner="ANTIGRAVITY",
        source="innerspark-smart-quoter",
    ),
    ReuseItem(
        kind="service",
        name="MongoDB pcdoctor_swarm",
        description="Canonical data store for the platform.",
        owner="SYSTEM",
        source="mongodb://127.0.0.1:27017/",
    ),
    ReuseItem(
        kind="service",
        name="WhatsApp / Evolution API",
        description="Existing outbound delivery and inbound command channel.",
        owner="CODEX",
        source="raphiia_openai.whatsapp_*",
    ),
    ReuseItem(
        kind="service",
        name="PDF pipeline",
        description="Existing quote PDF generation and delivery attachments.",
        owner="CODEX",
        source="raphiia_openai.operational.quote_pdf",
    ),
    ReuseItem(
        kind="agent",
        name="AG-25_ralfia_coordination_orchestrator",
        description="Canonical coordination daemon and inbox/outbox synchronizer.",
        owner="RALFIA_PLATFORM",
        source="/home/rlopez/inneros_core/agents_pool/AG-25_ralfia_coordination_orchestrator/",
    ),
)


NEW_COMPONENTS: tuple[ReuseItem, ...] = (
    ReuseItem(
        kind="repo",
        name="ralphiia-quoteops",
        description="Separate hackathon repository for OpenAI Build Week.",
        owner="CODEX",
        source="/home/rlopez/projects/ralphiia-quoteops",
        status="new",
    ),
    ReuseItem(
        kind="package",
        name="quoteops",
        description="FastAPI app and QuoteOps domain layer.",
        owner="CODEX",
        source="/home/rlopez/projects/ralphiia-quoteops/quoteops",
        status="new",
    ),
    ReuseItem(
        kind="contracts",
        name="QuoteIntake / MissionState / Risks",
        description="Structured Outputs contracts for H2-H4.",
        owner="CODEX",
        source="/home/rlopez/projects/ralphiia-quoteops/quoteops/contracts.py",
        status="new",
    ),
)


def serialize_catalog() -> dict[str, list[dict[str, str]]]:
    return {
        "reuse_first": [asdict(item) for item in REUSE_CATALOG],
        "new_for_quoteops": [asdict(item) for item in NEW_COMPONENTS],
    }


def reuse_summary() -> dict[str, object]:
    return {
        "ok": True,
        "reuse_count": len(REUSE_CATALOG),
        "new_count": len(NEW_COMPONENTS),
        "catalog": serialize_catalog(),
    }
