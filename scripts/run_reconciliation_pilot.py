from __future__ import annotations

import argparse
import json
from pathlib import Path

from pymongo import MongoClient

from quoteops.reconciliation_pipeline import generate_candidates, parse_pacifico_statement, persist_pilot
from quoteops.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("statement", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.statement.is_file():
        raise SystemExit("statement_not_found")
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
    db = client.pcdoctor_swarm
    statement = parse_pacifico_statement(args.statement)
    candidates = generate_candidates(db, statement)
    result = {
        "ok": True,
        "apply": args.apply,
        "statement": {key: value for key, value in statement.items() if key not in {"transactions", "ocr_text_by_page", "source_path"}},
        "candidate_count": len(candidates),
        "top_candidates": [
            {
                "candidate_id": item["candidate_id"],
                "transaction_id": item["transaction_id"],
                "amount": item["amount"],
                "party_name": item["party_name"],
                "document_ids": item["document_ids"],
                "score": item["score"],
                "reasons": item["reasons"],
            }
            for item in sorted(candidates, key=lambda row: row["score"], reverse=True)[:10]
        ],
    }
    if args.apply:
        result["persistence"] = persist_pilot(db, statement, candidates)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
