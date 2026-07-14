from __future__ import annotations

from quoteops.contracts import (
    ApprovalDraft,
    MissionState,
    QuoteIntake,
    QuoteToolPlan,
    ToolDecision,
)


def build_tool_plan(intake: QuoteIntake) -> QuoteToolPlan:
    blockers: list[str] = []
    decisions: list[ToolDecision] = []

    if not intake.customer_name:
        blockers.append("customer_name")
    if not intake.contact:
        blockers.append("contact")
    if not intake.original_text:
        blockers.append("original_text")

    if blockers:
        decisions.append(
            ToolDecision(
                tool_name="collect_missing_info",
                reason="Need minimum viable intake before quoting.",
                args={"missing_fields": blockers},
            )
        )
        approval = ApprovalDraft(
            status="blocked",
            blockers=blockers,
            summary="Intake incomplete; stop before quote generation.",
        )
        next_step = "Ask for the missing information and re-run planning."
    else:
        decisions.append(
            ToolDecision(
                tool_name="generate_quote_intro",
                reason="Create a human-readable quote opening from the intake.",
                args={"channel": intake.source_channel},
            )
        )
        decisions.append(
            ToolDecision(
                tool_name="render_quote_document",
                reason="Prepare the structured quote document before PDF export.",
                args={"source_channel": intake.source_channel},
            )
        )
        decisions.append(
            ToolDecision(
                tool_name="generate_quote_pdf",
                reason="Produce the PDF artifact for review and delivery.",
                args={"attachments": intake.attachments},
            )
        )
        if intake.source_channel in {"whatsapp", "web"}:
            decisions.append(
                ToolDecision(
                    tool_name="send_quote_delivery",
                    reason="Dispatch quote through the requested channel once approved.",
                    args={"channels": [intake.source_channel, "email"]},
                )
            )
        approval = ApprovalDraft(
            status="ready",
            summary="Ready for approval gating, PDF generation, and delivery routing.",
        )
        next_step = "Move to approval, then PDF generation and delivery."

    return QuoteToolPlan(
        mission=MissionState(
            mission_id="mission_plan_0001",
            correlation_id="openai-build-week-quoteops-20260714",
            status="draft" if not blockers else "intake",
        ),
        intake=intake,
        tool_decisions=decisions,
        approval=approval,
        recommended_next_step=next_step,
    )
