from unittest import TestCase

from quoteops.adapters.openai_analysis import build_fallback_analysis
from quoteops.contracts import QuoteIntake


class TestIntakeAnalysis(TestCase):
    def test_fallback_analysis_has_required_sections(self) -> None:
        analysis = build_fallback_analysis(
            QuoteIntake(
                source_channel="sandbox",
                customer_name="Ana",
                contact="ana@example.com",
                original_text="Necesito una cotización para automatizar WhatsApp y PDFs.",
            )
        )

        self.assertTrue(analysis.ok)
        self.assertEqual(analysis.analysis_source, "fallback")
        self.assertEqual(analysis.mission.status, "analysis")
        self.assertGreaterEqual(len(analysis.proposal_options), 1)
        self.assertTrue(analysis.next_action)
