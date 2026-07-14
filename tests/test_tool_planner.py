from unittest import TestCase

from quoteops.adapters.tool_planner import build_tool_plan
from quoteops.contracts import QuoteIntake


class TestToolPlanner(TestCase):
    def test_plan_blocks_when_missing_fields(self) -> None:
        plan = build_tool_plan(QuoteIntake())

        self.assertEqual(plan.approval.status, "blocked")
        self.assertGreaterEqual(len(plan.approval.blockers), 1)
        self.assertGreaterEqual(len(plan.tool_decisions), 1)

    def test_plan_routes_to_pdf_and_delivery_when_complete(self) -> None:
        plan = build_tool_plan(
            QuoteIntake(
                source_channel="whatsapp",
                customer_name="Ana",
                contact="ana@example.com",
                original_text="Necesito una cotización para automatizar WhatsApp y PDFs.",
                attachments=["brief.pdf"],
            )
        )

        tool_names = [item.tool_name for item in plan.tool_decisions]
        self.assertEqual(plan.approval.status, "ready")
        self.assertIn("render_quote_document", tool_names)
        self.assertIn("generate_quote_pdf", tool_names)
        self.assertIn("send_quote_delivery", tool_names)
