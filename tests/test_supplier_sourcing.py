from datetime import date
from decimal import Decimal
import unittest

from quoteops.supplier_sourcing import (
    CREDIT_CURRENT_CONFIRMED, CREDIT_HISTORICAL_OBSERVED, SupplierOffer, SupplierRecord,
    deduplicate_offers, rank_offers, reconcile_supplier_records, recommend_offer,
)


def offer(**changes):
    values = dict(canonical_item_id="SKU-1", supplier_party_id="p1", supplier_name="ZC Mayoristas",
                  supplier_reference="ZC-001", unit_cost="10", quantity="2", tax_amount="0",
                  tax_status="known", shipping_cost="0", other_cost="0", availability="available",
                  valid_until="2026-12-31", source="quote", evidence="Q-1")
    values.update(changes)
    return SupplierOffer(**values)


class SupplierSourcingTests(unittest.TestCase):
    def test_same_sku_two_suppliers_are_retained_and_cheapest_selected(self):
        result = recommend_offer([offer(), offer(supplier_party_id="p2", supplier_name="Other", supplier_reference="O-1", unit_cost="9")], as_of=date(2026, 7, 16))
        self.assertEqual(result.lowest_cost_offer.offer.supplier_party_id, "p2")
        self.assertEqual(len(result.alternatives), 2)

    def test_confirmed_credit_within_and_outside_five_percent(self):
        cheap = offer(unit_cost="100", quantity="1")
        credit = offer(supplier_party_id="p2", supplier_reference="C", unit_cost="104", quantity="1", credit_status=CREDIT_CURRENT_CONFIRMED, credit_days=30)
        self.assertEqual(recommend_offer([cheap, credit], as_of=date(2026, 7, 16)).recommended_offer.offer.supplier_party_id, "p2")
        too_high = offer(supplier_party_id="p3", supplier_reference="H", unit_cost="106", quantity="1", credit_status=CREDIT_CURRENT_CONFIRMED, credit_days=30)
        self.assertEqual(recommend_offer([cheap, too_high], as_of=date(2026, 7, 16)).recommended_offer.offer.supplier_party_id, "p1")

    def test_historical_credit_is_not_automatic_credit_and_warns(self):
        historical = offer(unit_cost="9", credit_status=CREDIT_HISTORICAL_OBSERVED, credit_days=30)
        result = recommend_offer([historical], as_of=date(2026, 7, 16))
        self.assertIsNone(result.best_confirmed_credit_offer)
        self.assertIn("requires_reconfirmation", result.recommendation_reason)

    def test_landed_cost_includes_tax_shipping_and_other(self):
        evaluated = rank_offers([offer(unit_cost="10", quantity="2", tax_amount="3", shipping_cost="4", other_cost="1")], as_of=date(2026, 7, 16))[0]
        self.assertEqual(evaluated.landed_total, Decimal("28"))
        self.assertEqual(evaluated.landed_unit_cost, Decimal("14"))

    def test_ranking_uses_landed_unit_cost_when_quantities_differ(self):
        bulk = offer(supplier_party_id="bulk", supplier_reference="B", unit_cost="8", quantity="100", tax_amount="0", shipping_cost="0", other_cost="0")
        small = offer(supplier_party_id="small", supplier_reference="S", unit_cost="9", quantity="1", tax_amount="0", shipping_cost="0", other_cost="0")
        result = recommend_offer([bulk, small], as_of=date(2026, 7, 16))
        self.assertEqual(result.lowest_cost_offer.offer.supplier_party_id, "bulk")
        self.assertEqual(result.lowest_cost_offer.landed_unit_cost, Decimal("8"))

    def test_mixed_canonical_items_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "mixed_canonical_item_ids"):
            recommend_offer([offer(), offer(canonical_item_id="SKU-2", supplier_reference="other")])

    def test_expired_and_insufficient_stock_are_ineligible(self):
        expired = rank_offers([offer(valid_until="2026-07-15")], as_of=date(2026, 7, 16))[0]
        stock = rank_offers([offer(stock_quantity="1")], as_of=date(2026, 7, 16))[0]
        self.assertIn("expired", expired.reasons)
        self.assertIn("insufficient_stock", stock.reasons)

    def test_idempotency_deduplication_and_deterministic_order(self):
        first, second = offer(supplier_party_id="z", supplier_reference="Z"), offer(supplier_party_id="a", supplier_reference="A")
        self.assertEqual(len(deduplicate_offers([first, first, second])), 2)
        self.assertEqual([x.offer.supplier_party_id for x in rank_offers([first, second], as_of=date(2026, 7, 16))], ["a", "z"])

    def test_unknown_fields_are_explicit_not_invented(self):
        evaluation = rank_offers([offer(tax_status="unknown", tax_amount=None, shipping_cost=None, other_cost=None)], as_of=date(2026, 7, 16))[0]
        self.assertFalse(evaluation.eligible)
        self.assertIn("unknown_tax", evaluation.reasons)
        self.assertIsNone(evaluation.landed_total)

    def test_supplier_reconciliation_does_not_merge_ambiguous_names(self):
        rows = [SupplierRecord("a", "contifico", name="Comercial Acme"), SupplierRecord("b", "crm", name="COMERCIAL ACME"), SupplierRecord("c", "legacy", name="Comercial Acme")]
        results = {row.record_id: row for row in reconcile_supplier_records(rows)}
        self.assertIsNone(results["a"].matched_record_id)
        self.assertEqual(results["a"].match_method, "name_candidate")
        self.assertEqual(results["a"].candidate_record_ids, ("b", "c"))
        self.assertEqual(reconcile_supplier_records([SupplierRecord("x", "crm", party_id="7"), SupplierRecord("y", "contifico", party_id="7")])[0].match_method, "party_id")


if __name__ == "__main__":
    unittest.main()
