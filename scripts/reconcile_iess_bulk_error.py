from __future__ import annotations

import argparse
from datetime import datetime, timezone

from pymongo import MongoClient

from quoteops.settings import get_settings


CORRECT_PLAN = "0000000216009271"
BULK_MARKER = "Pago_Manual_Rafael_20260715.pdf"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    client = MongoClient(get_settings().mongo_uri, serverSelectionTimeoutMS=3000)
    db = client.pcdoctor_swarm
    query = {"archivo_pago": BULK_MARKER, "total_pago": 195.7, "status": "paid"}
    rows = list(db.ralfia_iess_vouchers.find(query))
    if len(rows) != 15:
        raise SystemExit(f"guard_failed_expected_15_found_{len(rows)}")
    if sum(row.get("comprobante_id") == CORRECT_PLAN for row in rows) != 1:
        raise SystemExit("guard_failed_correct_plan_not_unique")
    suspect = [row for row in rows if row.get("comprobante_id") != CORRECT_PLAN]
    print({"matched": len(rows), "suspect": len(suspect), "correct_plan": CORRECT_PLAN, "apply": args.apply})
    if not args.apply:
        return

    now = datetime.now(timezone.utc).isoformat()
    run_id = "iess_reconcile_20260715_bulk_19570"
    for row in rows:
        plan_code = row["comprobante_id"]
        is_correct = plan_code == CORRECT_PLAN
        audit_id = f"{run_id}_{plan_code}"
        db.accounting_reconciliation_audit.update_one(
            {"audit_id": audit_id},
            {"$setOnInsert": {
                "audit_id": audit_id,
                "run_id": run_id,
                "created_at": now,
                "entity_type": "ralfia_iess_voucher",
                "entity_id": plan_code,
                "reason": "same_manual_payment_was_applied_to_15_unrelated_vouchers",
                "before": {
                    "status": row.get("status"),
                    "periodo": row.get("periodo"),
                    "total_planilla": row.get("total_planilla"),
                    "total_pago": row.get("total_pago"),
                    "archivo_pago": row.get("archivo_pago"),
                    "fecha_pago": row.get("fecha_pago"),
                },
                "resolution": "preserve_verified_payment" if is_correct else "needs_reconciliation",
                "agent": "CODEX",
            }},
            upsert=True,
        )
        set_fields = {
            "updated_at": now,
            "reconciliation_run_id": run_id,
            "reconciliation_note": "Removed unverified bulk payment assignment; verify against bank/PST/Contifico.",
        }
        if not is_correct:
            set_fields["status"] = "needs_reconciliation"
        db.ralfia_iess_vouchers.update_one(
            {"_id": row["_id"]},
            {
                "$set": set_fields,
                "$unset": {"total_pago": "", "archivo_pago": "", "fecha_pago": ""},
            },
        )
    print({"ok": True, "audited": len(rows), "quarantined": len(suspect), "verified_payment_preserved": CORRECT_PLAN})


if __name__ == "__main__":
    main()
