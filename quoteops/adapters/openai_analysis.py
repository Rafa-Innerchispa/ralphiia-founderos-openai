from __future__ import annotations

from textwrap import dedent

from quoteops.contracts import (
    MissionState,
    MissingInformation,
    ProposalOption,
    QuoteAnalysisResult,
    QuoteIntake,
    QuoteIntakeAnalysis,
    QuoteReview,
    TechnicalRisk,
)
from quoteops.settings import Settings, get_settings

SYSTEM_PROMPT = dedent(
    """
    You are RalphiIA QuoteOps, an internal intake analyst.
    Return only structured JSON that matches the schema.
    Keep the answer concise, actionable, and focused on reuse of the existing RalphiIA stack.
    Prefer existing services, agents, and tools over proposing new ones.
    """
).strip()


def build_fallback_analysis(intake: QuoteIntake, settings: Settings | None = None) -> QuoteIntakeAnalysis:
    settings = settings or get_settings()
    missing = []
    if not intake.customer_name:
        missing.append("customer_name")
    if not intake.contact:
        missing.append("contact")
    if not intake.original_text:
        missing.append("original_text")

    risks = []
    if intake.original_text and len(intake.original_text) < 40:
        risks.append("Input too short for reliable technical analysis")
    if intake.source_channel == "sandbox":
        risks.append("Sandbox request should be confirmed before any production-like action")

    options = [
        ProposalOption(
            code="A",
            title="Baseline assisted quote",
            summary="Quick deterministic scaffold for straightforward requests.",
            estimated_value="TBD",
        ),
        ProposalOption(
            code="B",
            title="Context-rich quote",
            summary="Uses selective retrieval and structured review before drafting.",
            estimated_value="TBD",
        ),
    ]

    return QuoteIntakeAnalysis(
        analysis_source="fallback",
        model_used="deterministic_rules",
        mission=MissionState(
            mission_id="mission_preview_0001",
            correlation_id="openai-build-week-quoteops-20260714",
            status="analysis",
        ),
        intake=intake,
        missing_information=MissingInformation(items=missing),
        technical_risks=TechnicalRisk(items=risks),
        proposal_options=options,
        review=QuoteReview(status="needs_review" if missing else "draft", notes=["Fallback analysis ready"]),
        next_action="Complete the missing fields and continue through the QuoteOps review flow.",
    )


def analyze_intake(intake: QuoteIntake, settings: Settings | None = None) -> QuoteIntakeAnalysis:
    settings = settings or get_settings()
    if not settings.enable_openai or not settings.openai_api_key:
        return build_fallback_analysis(intake, settings)

    try:
        from openai import OpenAI
    except Exception:
        return build_fallback_analysis(intake, settings)

    client = OpenAI()
    schema = QuoteAnalysisResult.model_json_schema()
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze this RalphiIA quote intake and return only structured JSON. "
                    f"Intake: {intake.model_dump_json()}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "quoteops_intake_analysis",
                "strict": True,
                "schema": schema,
            }
        },
    )

    payload = getattr(response, "output_text", "") or ""
    if not payload:
        return build_fallback_analysis(intake, settings)

    result = QuoteAnalysisResult.model_validate_json(payload)
    return QuoteIntakeAnalysis(
        analysis_source="openai",
        model_used=settings.openai_model,
        mission=MissionState(
            mission_id="mission_preview_0001",
            correlation_id="openai-build-week-quoteops-20260714",
            status="analysis",
        ),
        intake=intake,
        missing_information=result.missing_information,
        technical_risks=result.technical_risks,
        proposal_options=result.proposal_options,
        review=result.review,
        next_action=result.next_action,
    )
