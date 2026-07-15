from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, MongoClient

from quoteops.contracts import (
    CustomerComparison,
    CustomerDraft,
    IdentityConflict,
    IdentityMatch,
    RucConfirmationResult,
    TaxpayerVerification,
)
from quoteops.settings import Settings


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm(value).lower())


class RalphiIdentityReader:
    """Read-only bridge to the existing identity kernel and Contífico mirror."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def resolve(self, ruc: str) -> list[IdentityMatch]:
        return await asyncio.to_thread(self._resolve_sync, ruc)

    def _resolve_sync(self, ruc: str) -> list[IdentityMatch]:
        package_root = Path(self.settings.ralfia_package_root)
        if not package_root.exists():
            return []
        root = str(package_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            from raphiia_openai.contifico_normalize import resolve_contifico_persona
            from raphiia_openai.operational.party_store import resolve_party
            from raphiia_openai.operational.pcdoctor_store import resolve_client
        except ImportError:
            return []

        matches: list[IdentityMatch] = []
        party_result = resolve_party(ruc, limit=5, roles=["client"])
        for item in party_result.get("matches") or []:
            matches.append(_party_match(item))
        client_result = resolve_client(ruc, limit=5)
        for item in client_result.get("matches") or []:
            matches.append(_client_match(item))
        contifico_result = resolve_contifico_persona(ruc, limit=5)
        for item in contifico_result.get("matches") or []:
            matches.append(_contifico_match(item))
        deduped: dict[tuple[str, str], IdentityMatch] = {}
        for match in matches:
            key = (match.source, match.source_id or match.party_id or match.client_id)
            deduped[key] = match
        return list(deduped.values())


class QuoteOpsCustomerStore:
    """Staging-only customer registry with unique RUC identity keys."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[settings.quoteops_mongo_db]
        self.verifications = self.db["taxpayer_verifications"]
        self.parties = self.db["parties"]
        self.clients = self.db["clients"]
        self.identity_map = self.db["identity_map"]
        self.audit = self.db["audit_events"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.verifications.create_index([("verification_id", ASCENDING)], unique=True)
        self.verifications.create_index([("ruc", ASCENDING), ("retrieved_at", -1)])
        self.parties.create_index([("tax_id", ASCENDING)], unique=True)
        self.clients.create_index([("tax_id", ASCENDING)], unique=True)
        self.identity_map.create_index(
            [("source", ASCENDING), ("source_id", ASCENDING)], unique=True
        )

    async def staging_match(self, ruc: str) -> list[IdentityMatch]:
        return await asyncio.to_thread(self._staging_match_sync, ruc)

    def _staging_match_sync(self, ruc: str) -> list[IdentityMatch]:
        party = self.parties.find_one({"tax_id": ruc}) or {}
        client = self.clients.find_one({"tax_id": ruc}) or {}
        if not party and not client:
            return []
        return [
            IdentityMatch(
                source="quoteops_staging",
                source_id=str(party.get("party_id") or client.get("client_id") or ""),
                party_id=str(party.get("party_id") or ""),
                client_id=str(client.get("client_id") or ""),
                legal_name=str(party.get("legal_name") or client.get("legal_name") or ""),
                commercial_name=str(party.get("trade_name") or client.get("trade_name") or ""),
                ruc=ruc,
                address=str(client.get("address") or ""),
                linked=True,
            )
        ]

    async def save_verification(self, verification: TaxpayerVerification) -> None:
        await asyncio.to_thread(self._save_verification_sync, verification)

    def _save_verification_sync(self, verification: TaxpayerVerification) -> None:
        doc = verification.model_dump()
        # Representative identification from the provider is never stored here.
        self.verifications.update_one(
            {"verification_id": verification.verification_id},
            {"$setOnInsert": doc},
            upsert=True,
        )

    async def confirm(
        self,
        verification_id: str,
        ruc: str,
        approved_by: str,
        trace_id: str,
    ) -> RucConfirmationResult:
        return await asyncio.to_thread(
            self._confirm_sync, verification_id, ruc, approved_by, trace_id
        )

    def _confirm_sync(
        self,
        verification_id: str,
        ruc: str,
        approved_by: str,
        trace_id: str,
    ) -> RucConfirmationResult:
        verification = self.verifications.find_one(
            {"verification_id": verification_id, "ruc": ruc}
        )
        if not verification:
            raise ValueError("verification_not_found_or_stale")
        existing_party = self.parties.find_one({"tax_id": ruc})
        existing_client = self.clients.find_one({"tax_id": ruc})
        created = not existing_party and not existing_client
        digest = sha256(ruc.encode()).hexdigest()[:18]
        party_id = str((existing_party or {}).get("party_id") or f"qparty_{digest}")
        client_id = str((existing_client or {}).get("client_id") or f"qclient_{digest}")
        now = datetime.now(timezone.utc).isoformat()
        establishments = verification.get("establishments") or []
        address = str(establishments[0].get("full_address") or "") if establishments else ""
        shared = {
            "legal_name": verification.get("legal_name") or "",
            "trade_name": verification.get("commercial_name") or "",
            "tax_id": ruc,
            "verification_source": verification.get("source"),
            "verification_id": verification_id,
            "verified_at": verification.get("retrieved_at"),
            "approved_by": approved_by,
            "updated_at": now,
        }
        self.parties.update_one(
            {"tax_id": ruc},
            {"$set": {**shared, "party_id": party_id, "roles": ["client"]}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        self.clients.update_one(
            {"tax_id": ruc},
            {"$set": {**shared, "client_id": client_id, "party_id": party_id, "address": address, "status": "active"}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        self.identity_map.update_one(
            {"source": "intuito_azure", "source_id": ruc},
            {"$set": {"party_id": party_id, "client_id": client_id, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        self.audit.insert_one(
            {
                "trace_id": trace_id,
                "event": "customer_confirmed",
                "ruc_hash": sha256(ruc.encode()).hexdigest(),
                "party_id": party_id,
                "client_id": client_id,
                "created": created,
                "approved_by": approved_by,
                "ts": now,
            }
        )
        duplicate_count = max(
            self.parties.count_documents({"tax_id": ruc}),
            self.clients.count_documents({"tax_id": ruc}),
        )
        return RucConfirmationResult(
            trace_id=trace_id,
            created=created,
            action="created" if created else "updated",
            party_id=party_id,
            client_id=client_id,
            ruc=ruc,
            duplicate_count=duplicate_count,
        )


def compare_customer(
    verification: TaxpayerVerification, matches: list[IdentityMatch]
) -> tuple[CustomerComparison, CustomerDraft]:
    conflicts: list[IdentityConflict] = []
    exact = any(match.ruc == verification.ruc for match in matches)
    for match in matches:
        if match.ruc and match.ruc != verification.ruc:
            conflicts.append(
                IdentityConflict(
                    field="ruc",
                    source=match.source,
                    official_value=verification.ruc,
                    source_value=match.ruc,
                    severity="critical",
                )
            )
        if match.legal_name and verification.legal_name and _norm_key(match.legal_name) != _norm_key(verification.legal_name):
            conflicts.append(
                IdentityConflict(
                    field="legal_name",
                    source=match.source,
                    official_value=verification.legal_name,
                    source_value=match.legal_name,
                )
            )
        if match.commercial_name and verification.commercial_name and _norm_key(match.commercial_name) != _norm_key(verification.commercial_name):
            conflicts.append(
                IdentityConflict(
                    field="commercial_name",
                    source=match.source,
                    official_value=verification.commercial_name,
                    source_value=match.commercial_name,
                    severity="info",
                )
            )
    staging_match = next((match for match in matches if match.source == "quoteops_staging"), None)
    if staging_match:
        action = "update"
    elif exact:
        action = "link_existing"
    else:
        action = "create"
    address = verification.establishments[0].full_address if verification.establishments else ""
    comparison = CustomerComparison(
        matches=matches,
        conflicts=conflicts,
        exact_ruc_match=exact,
        recommended_action=action,
    )
    draft = CustomerDraft(
        ruc=verification.ruc,
        legal_name=verification.legal_name,
        commercial_name=verification.commercial_name,
        activity=verification.activity,
        address=address,
        recommended_action=action,
    )
    return comparison, draft


def _party_match(item: dict[str, Any]) -> IdentityMatch:
    return IdentityMatch(
        source=str(item.get("_source") or "ralphiia_party"),
        source_id=str(item.get("_source_id") or item.get("party_id") or ""),
        party_id=str(item.get("party_id") or ""),
        legal_name=str(item.get("legal_name") or item.get("display_name") or ""),
        commercial_name=str(item.get("trade_name") or item.get("display_name") or ""),
        ruc=str(item.get("tax_id") or ""),
        address=str(item.get("address") or ""),
        linked=bool(item.get("_linked") or item.get("party_id")),
    )


def _client_match(item: dict[str, Any]) -> IdentityMatch:
    return IdentityMatch(
        source="ops_clients",
        source_id=str(item.get("client_id") or ""),
        client_id=str(item.get("client_id") or ""),
        legal_name=str(item.get("legal_name") or item.get("display_name") or ""),
        commercial_name=str(item.get("trade_name") or item.get("display_name") or ""),
        ruc=str(item.get("tax_id") or ""),
        address=str(item.get("address") or ""),
        linked=bool(item.get("party_id")),
    )


def _contifico_match(item: dict[str, Any]) -> IdentityMatch:
    return IdentityMatch(
        source="contifico_personas",
        source_id=str(item.get("persona_id") or ""),
        party_id=str(item.get("party_id") or ""),
        client_id=str(item.get("client_id") or ""),
        legal_name=str(item.get("nombre") or item.get("razon_social") or ""),
        commercial_name=str(item.get("nombre_comercial") or ""),
        ruc=str(item.get("ruc") or ""),
        address=str(item.get("direccion") or ""),
        linked=bool(item.get("party_id") or item.get("client_id")),
    )
