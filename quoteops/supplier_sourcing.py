"""Deterministic supplier-offer normalization, comparison and reconciliation.

This module is deliberately pure: it performs no I/O and never places orders.
All amounts are ``Decimal`` and unknown commercial facts remain ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Iterable, Optional
import re
import unicodedata


USD = "USD"
CREDIT_CURRENT_CONFIRMED = "current_confirmed"
CREDIT_HISTORICAL_OBSERVED = "historical_observed"
CREDIT_UNVERIFIED = "unverified"
CREDIT_UNAVAILABLE = "unavailable"
CREDIT_STATUSES = frozenset(
    {
        CREDIT_CURRENT_CONFIRMED,
        CREDIT_HISTORICAL_OBSERVED,
        CREDIT_UNVERIFIED,
        CREDIT_UNAVAILABLE,
    }
)
SUPPORTED_CURRENCIES = frozenset({USD})


def _decimal(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid monetary value: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"invalid monetary value: {value!r}")
    return amount


def normalize_name(name: str | None) -> str:
    """Return a comparison key, never an identity assertion."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@dataclass(frozen=True)
class SupplierOffer:
    canonical_item_id: str
    supplier_party_id: str | None
    supplier_name: str | None
    supplier_reference: str | None
    unit_cost: Decimal | str | int | float | None
    quantity: Decimal | str | int | float | None
    currency: str | None = USD
    tax_amount: Decimal | str | int | float | None = None
    tax_status: str = "unknown"  # known | unknown
    shipping_cost: Decimal | str | int | float | None = None
    other_cost: Decimal | str | int | float | None = None
    availability: str | None = None  # available | unavailable | unknown
    stock_quantity: Decimal | str | int | float | None = None
    lead_time_days: int | None = None
    valid_until: date | str | None = None
    source: str | None = None
    evidence: str | None = None
    payment_mode: str | None = None
    credit_days: int | None = None
    credit_status: str = CREDIT_UNVERIFIED

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_item_id", (self.canonical_item_id or "").strip())
        object.__setattr__(self, "currency", (self.currency or "").upper())
        for name in ("unit_cost", "quantity", "tax_amount", "shipping_cost", "other_cost", "stock_quantity"):
            object.__setattr__(self, name, _decimal(getattr(self, name)))
        if isinstance(self.valid_until, str):
            object.__setattr__(self, "valid_until", date.fromisoformat(self.valid_until))
        if self.tax_status not in {"known", "unknown"}:
            raise ValueError("tax_status must be 'known' or 'unknown'")
        if self.availability not in {"available", "unavailable", "unknown", None}:
            raise ValueError("invalid availability")
        if self.credit_status not in CREDIT_STATUSES:
            raise ValueError("invalid credit_status")

    @property
    def offer_id(self) -> str:
        """Stable semantic identifier used only for idempotent de-duplication."""
        parts = (
            self.canonical_item_id, self.supplier_party_id, normalize_name(self.supplier_name),
            self.supplier_reference, self.unit_cost, self.quantity, self.currency,
            self.tax_amount, self.tax_status, self.shipping_cost, self.other_cost,
            self.availability, self.stock_quantity, self.lead_time_days, self.valid_until,
            self.source, self.evidence, self.payment_mode, self.credit_days, self.credit_status,
        )
        return sha256("|".join("" if part is None else str(part) for part in parts).encode()).hexdigest()


@dataclass(frozen=True)
class OfferEvaluation:
    offer: SupplierOffer
    eligible: bool
    reasons: tuple[str, ...]
    landed_total: Decimal | None
    landed_unit_cost: Decimal | None


@dataclass(frozen=True)
class SourcingRecommendation:
    canonical_item_id: str
    lowest_cost_offer: OfferEvaluation | None
    best_confirmed_credit_offer: OfferEvaluation | None
    recommended_offer: OfferEvaluation | None
    recommendation_reason: str
    absolute_delta: Decimal | None
    percentage_delta: Decimal | None
    policy_max_credit_premium_pct: Decimal
    alternatives: tuple[OfferEvaluation, ...]


def evaluate_offer(offer: SupplierOffer, *, as_of: date | None = None) -> OfferEvaluation:
    """Evaluate facts without filling any missing commercial data."""
    as_of = as_of or date.today()
    reasons: list[str] = []
    if not offer.canonical_item_id:
        reasons.append("missing_canonical_item_id")
    if not (offer.supplier_party_id or offer.supplier_name):
        reasons.append("missing_supplier_identity")
    if offer.unit_cost is None or offer.unit_cost < 0:
        reasons.append("missing_or_invalid_unit_cost")
    if offer.quantity is None or offer.quantity <= 0:
        reasons.append("missing_or_invalid_quantity")
    if offer.currency not in SUPPORTED_CURRENCIES:
        reasons.append("unsupported_currency")
    if offer.tax_status == "unknown" or offer.tax_amount is None:
        reasons.append("unknown_tax")
    if offer.shipping_cost is None:
        reasons.append("unknown_shipping_cost")
    if offer.other_cost is None:
        reasons.append("unknown_other_cost")
    if offer.valid_until is not None and offer.valid_until < as_of:
        reasons.append("expired")
    if offer.availability == "unavailable":
        reasons.append("unavailable")
    if offer.stock_quantity is not None and offer.quantity is not None and offer.stock_quantity < offer.quantity:
        reasons.append("insufficient_stock")
    if offer.availability in {None, "unknown"}:
        reasons.append("availability_unconfirmed")
    landed_total: Decimal | None = None
    if not {"missing_or_invalid_unit_cost", "missing_or_invalid_quantity", "unsupported_currency", "unknown_tax", "unknown_shipping_cost", "unknown_other_cost"}.intersection(reasons):
        landed_total = offer.unit_cost * offer.quantity + offer.tax_amount + offer.shipping_cost + offer.other_cost  # type: ignore[operator]
    landed_unit_cost = landed_total / offer.quantity if landed_total is not None and offer.quantity else None
    return OfferEvaluation(offer, not reasons, tuple(reasons), landed_total, landed_unit_cost)


def deduplicate_offers(offers: Iterable[SupplierOffer]) -> tuple[SupplierOffer, ...]:
    """Keep one copy of an identical offer while preserving distinct supplier offers."""
    unique = {offer.offer_id: offer for offer in offers}
    return tuple(unique[key] for key in sorted(unique))


def rank_offers(offers: Iterable[SupplierOffer], *, as_of: date | None = None) -> tuple[OfferEvaluation, ...]:
    evaluations = [evaluate_offer(offer, as_of=as_of) for offer in deduplicate_offers(offers)]
    return tuple(sorted(
        evaluations,
        key=lambda item: (
            not item.eligible, item.landed_total is None, item.landed_total or Decimal("0"),
            item.offer.supplier_party_id or "", normalize_name(item.offer.supplier_name),
            item.offer.supplier_reference or "", item.offer.offer_id,
        ),
    ))


def recommend_offer(
    offers: Iterable[SupplierOffer], *,
    as_of: date | None = None,
    max_credit_premium_pct: Decimal | str | int | float = Decimal("5"),
) -> SourcingRecommendation:
    """Recommend only; the default 5% confirmed-credit premium is adjustable."""
    policy = _decimal(max_credit_premium_pct)
    if policy is None or policy < 0:
        raise ValueError("max_credit_premium_pct must be a non-negative number")
    ranked = rank_offers(offers, as_of=as_of)
    item_id = ranked[0].offer.canonical_item_id if ranked else ""
    valid = [item for item in ranked if item.eligible]
    cheapest = valid[0] if valid else None
    confirmed = next((item for item in valid if item.offer.credit_status == CREDIT_CURRENT_CONFIRMED), None)
    delta = percent = None
    recommended = cheapest
    reason = "no_eligible_offer" if cheapest is None else "lowest_landed_cost"
    if cheapest and confirmed:
        delta = confirmed.landed_total - cheapest.landed_total  # type: ignore[operator]
        percent = Decimal("0") if cheapest.landed_total == 0 else delta / cheapest.landed_total * Decimal("100")
        if percent <= policy:
            recommended, reason = confirmed, "current_confirmed_credit_within_policy"
        else:
            reason = "lowest_landed_cost_credit_premium_exceeds_policy"
    if any(item.offer.credit_status == CREDIT_HISTORICAL_OBSERVED for item in ranked):
        reason += "; historical_credit_requires_reconfirmation"
    return SourcingRecommendation(item_id, cheapest, confirmed, recommended, reason, delta, percent, policy, ranked)


@dataclass(frozen=True)
class SupplierRecord:
    record_id: str
    source: str  # contifico | crm | legacy | invoice_history
    tax_id: str | None = None
    party_id: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    record_id: str
    matched_record_id: str | None
    match_method: str | None
    candidate_record_ids: tuple[str, ...]


def reconcile_supplier_records(records: Iterable[SupplierRecord]) -> tuple[ReconciliationResult, ...]:
    """Reconcile tax ID first, then party ID; normalized names are candidates only."""
    ordered = sorted(records, key=lambda row: (row.source, row.record_id))
    results: list[ReconciliationResult] = []
    for record in ordered:
        others = [row for row in ordered if row.record_id != record.record_id]
        tax_matches = [row for row in others if record.tax_id and row.tax_id == record.tax_id]
        party_matches = [row for row in others if record.party_id and row.party_id == record.party_id]
        name_matches = [row for row in others if normalize_name(record.name) and normalize_name(record.name) == normalize_name(row.name)]
        if len(tax_matches) == 1:
            results.append(ReconciliationResult(record.record_id, tax_matches[0].record_id, "tax_id", (tax_matches[0].record_id,)))
        elif len(tax_matches) > 1:
            results.append(ReconciliationResult(record.record_id, None, "ambiguous_tax_id", tuple(row.record_id for row in tax_matches)))
        elif len(party_matches) == 1:
            results.append(ReconciliationResult(record.record_id, party_matches[0].record_id, "party_id", (party_matches[0].record_id,)))
        elif len(party_matches) > 1:
            results.append(ReconciliationResult(record.record_id, None, "ambiguous_party_id", tuple(row.record_id for row in party_matches)))
        else:
            results.append(ReconciliationResult(record.record_id, None, "name_candidate" if name_matches else None, tuple(row.record_id for row in name_matches)))
    return tuple(results)
