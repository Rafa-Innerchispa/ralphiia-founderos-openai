from __future__ import annotations

from hashlib import sha256
from time import time_ns

from quoteops.adapters.customer_identity import (
    QuoteOpsCustomerStore,
    RalphiIdentityReader,
    compare_customer,
)
from quoteops.adapters.taxpayer_registry import IntuitoAzureRucAdapter, normalize_ruc
from quoteops.contracts import (
    RucConfirmationResult,
    RucConfirmRequest,
    RucLookupRequest,
    RucLookupResult,
)
from quoteops.settings import Settings


class CustomerIdentityService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = IntuitoAzureRucAdapter(settings)
        self.identity_reader = RalphiIdentityReader(settings)
        self.customer_store = QuoteOpsCustomerStore(settings)

    async def lookup(self, request: RucLookupRequest) -> RucLookupResult:
        trace_id = _trace_id(request.ruc)
        verification = await self.registry.lookup(
            request.ruc, force_refresh=request.force_refresh
        )
        internal_matches = await self.identity_reader.resolve(verification.ruc)
        staging_matches = await self.customer_store.staging_match(verification.ruc)
        comparison, draft = compare_customer(
            verification, internal_matches + staging_matches
        )
        await self.customer_store.save_verification(verification)
        return RucLookupResult(
            trace_id=trace_id,
            verification=verification,
            comparison=comparison,
            customer_draft=draft,
        )

    async def confirm(self, request: RucConfirmRequest) -> RucConfirmationResult:
        ruc = normalize_ruc(request.ruc)
        return await self.customer_store.confirm(
            request.expected_verification_id,
            ruc,
            request.approved_by,
            _trace_id(ruc),
            contact_email=request.contact_email,
            billing_email=request.billing_email,
            phone=request.phone,
            address=request.address,
        )


def _trace_id(seed: str) -> str:
    return "trace_" + sha256(f"{seed}:{time_ns()}".encode()).hexdigest()[:20]
