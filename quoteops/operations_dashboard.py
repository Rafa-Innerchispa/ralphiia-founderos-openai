from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient


def _clean(document: dict[str, Any] | None) -> dict[str, Any]:
    if not document:
        return {}
    return {key: value for key, value in document.items() if key != "_id"}


class OperationsDashboardService:
    """Read-only operational projection for the QuoteOps cockpit."""

    def __init__(self, mongo_uri: str, database: str = "pcdoctor_swarm") -> None:
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        self.db = self.client[database]

    def close(self) -> None:
        self.client.close()

    def snapshot(self) -> dict[str, Any]:
        vouchers = self.db.ralfia_iess_vouchers
        payments = self.db.accounting_payments
        statements = self.db.quoteops_bank_statements
        transactions = self.db.quoteops_bank_transactions
        candidates = self.db.quoteops_reconciliation_candidates
        pending_actions = self.db.whatsapp_pending_actions

        latest_payment = _clean(payments.find_one(
            {"source": "whatsapp_iess_payment"},
            {
                "_id": 0, "payment_id": 1, "payable_id": 1, "amount": 1,
                "currency": 1, "paid_at": 1, "reference": 1, "source": 1,
            },
            sort=[("updated_at", -1), ("created_at", -1)],
        ))
        recent_vouchers = [
            _clean(item)
            for item in vouchers.find(
                {},
                {
                    "_id": 0, "comprobante_id": 1, "periodo": 1, "status": 1,
                    "total_planilla": 1, "amount_paid": 1, "bank_receipt": 1,
                    "contribution_period": 1, "payment_due_period": 1,
                },
            ).sort([("updated_at", -1), ("periodo", -1)]).limit(8)
        ]
        latest_statement = _clean(statements.find_one(
            {}, {
                "_id": 0, "statement_id": 1, "bank": 1, "source_file": 1,
                "statement_period_start": 1, "statement_period_end": 1,
                "opening_balance": 1, "closing_balance": 1,
                "balance_difference": 1, "continuity_status": 1,
                "transaction_count": 1, "environment": 1,
            }, sort=[("updated_at", -1)]
        ))
        statement_id = latest_statement.get("statement_id")
        query = {"statement_id": statement_id} if statement_id else {"_id": None}
        recent_candidates = [
            _clean(item)
            for item in candidates.find(query, {
                "_id": 0, "candidate_id": 1, "transaction_date": 1,
                "amount": 1, "party_name": 1, "document_ids": 1,
                "score": 1, "reasons": 1, "status": 1,
                "requires_human_approval": 1,
            }).sort("score", -1).limit(8)
        ]

        return {
            "ok": True,
            "environment": "staging",
            "read_only": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "iess": {
                "total_vouchers": vouchers.count_documents({}),
                "paid_verified": vouchers.count_documents({"status": "paid_verified"}),
                "paid_unverified": vouchers.count_documents({"status": "paid_unverified"}),
                "awaiting_confirmation": pending_actions.count_documents({
                    "action_type": "iess_payment", "status": "awaiting_confirmation"
                }),
                "latest_payment": latest_payment,
                "recent_vouchers": recent_vouchers,
            },
            "bank": {
                "statement_count": statements.count_documents({}),
                "transaction_count": transactions.count_documents({}),
                "candidate_count": candidates.count_documents({"status": "candidate"}),
                "approved_count": candidates.count_documents({"status": "approved"}),
                "exception_count": statements.count_documents({"continuity_status": "exception"}),
                "latest_statement": latest_statement,
                "recent_candidates": recent_candidates,
            },
        }
