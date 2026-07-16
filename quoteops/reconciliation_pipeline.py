"""Auditable, candidate-only bank reconciliation for QuoteOps staging."""

from __future__ import annotations

import hashlib
import itertools
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from rapidocr_onnxruntime import RapidOCR


PARSER_VERSION = "pacifico-ocr-v1"
DATE_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
MONEY_RE = re.compile(r"(?<!\d)(\d+[.,]\d{2})(?!\d)")
MONTHS = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
    "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
    "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}
SECTION_MARKERS = {
    "DEPOSITOS": "deposit",
    "VALORES ACREDITADOS": "credit",
    "CHEQUES PAGADOS": "cheque",
    "VALORES DEBITADOS": "debit",
    "PAGO DE SERVICIO": "service",
}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", (text or "").upper()).strip()


def _money_values(lines: list[str]) -> list[float]:
    values: list[float] = []
    for line in lines:
        for match in MONEY_RE.findall(line.replace("O.OO", "0.00").replace("0.OO", "0.00")):
            values.append(float(match.replace(",", ".")))
    return values


def _statement_period(lines: list[str]) -> tuple[str, str] | tuple[None, None]:
    joined = " ".join(lines)
    match = re.search(r"MES\s+DE\s+CORTE\s*:?\s*([A-Z]+)\s*[- ]\s*(20\d{2})", _normalized(joined))
    if not match or match.group(1) not in MONTHS:
        return None, None
    year, month = int(match.group(2)), MONTHS[match.group(1)]
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    end = date.fromordinal(next_month.toordinal() - 1)
    return start.isoformat(), end.isoformat()


def _balance_after_label(lines: list[str], label: str) -> float | None:
    target = _normalized(label)
    for index, line in enumerate(lines):
        if target not in _normalized(line):
            continue
        values = _money_values(lines[index:index + 5])
        if values:
            return values[0]
    return None


def ocr_pdf_pages(path: str | Path) -> list[list[str]]:
    document = fitz.open(str(path))
    engine = RapidOCR()
    pages: list[list[str]] = []
    with tempfile.TemporaryDirectory(prefix="quoteops-ocr-") as tmp:
        for page_number, page in enumerate(document, start=1):
            image = Path(tmp) / f"page-{page_number}.png"
            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(str(image))
            result, _ = engine(str(image))
            pages.append([str(item[1]).strip() for item in (result or []) if str(item[1]).strip()])
    return pages


def _section_for_line(line: str, current: str | None) -> str | None:
    normalized = _normalized(line)
    for marker, section in SECTION_MARKERS.items():
        if marker in normalized:
            return section
    return current


def _transaction_from_block(section: str, block: list[str], *, page: int, row: int, source_hash: str) -> dict[str, Any] | None:
    values = _money_values(block)
    if not values:
        return None
    if section == "deposit" and len(values) >= 3:
        amount = values[2]
        direction = "credit"
    else:
        amount = values[0]
        direction = "credit" if section == "credit" else "debit"
    reference = ""
    if section == "cheque":
        for token in block[1:5]:
            digits = "".join(char for char in token if char.isdigit())
            if 3 <= len(digits) <= 8 and "." not in token:
                reference = digits.zfill(7)
                break
    description = " ".join(block[1:])[:800]
    raw_key = f"{source_hash}:{page}:{row}:{section}:{block[0]}:{amount:.2f}:{reference}"
    return {
        "transaction_id": "banktx_" + hashlib.sha256(raw_key.encode()).hexdigest()[:20],
        "transaction_date": block[0],
        "value_date": block[0],
        "direction": direction,
        "transaction_type": section,
        "reference": reference,
        "description": description,
        "description_normalized": _normalized(description),
        "debit": amount if direction == "debit" else 0.0,
        "credit": amount if direction == "credit" else 0.0,
        "amount": amount,
        "source_page": page,
        "source_row": row,
        "confidence": 0.82,
        "parser_version": PARSER_VERSION,
    }


def parse_pacifico_statement(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    source_hash = sha256_file(source)
    pages = ocr_pdf_pages(source)
    all_lines = [line for page in pages for line in page]
    period_start, period_end = _statement_period(all_lines)
    transactions: list[dict[str, Any]] = []
    current_section: str | None = None
    for page_number, lines in enumerate(pages, start=1):
        index = 0
        while index < len(lines):
            normalized_line = _normalized(lines[index])
            if "TOTAL DE" in normalized_line or "SALDO ACTUAL" in normalized_line:
                current_section = None
                index += 1
                continue
            current_section = _section_for_line(lines[index], current_section)
            if current_section and DATE_RE.match(lines[index]):
                end = index + 1
                while end < len(lines) and not DATE_RE.match(lines[end]):
                    if any(marker in _normalized(lines[end]) for marker in SECTION_MARKERS):
                        break
                    if "TOTAL DE" in _normalized(lines[end]):
                        break
                    end += 1
                item = _transaction_from_block(
                    current_section,
                    lines[index:end],
                    page=page_number,
                    row=index + 1,
                    source_hash=source_hash,
                )
                if item:
                    item.update({"source_file": source.name, "source_sha256": source_hash})
                    transactions.append(item)
                index = end
                continue
            index += 1
    opening = _balance_after_label(all_lines, "Saldo Anterior")
    closing = _balance_after_label(all_lines, "Saldo Actual")
    credits = round(sum(item["credit"] for item in transactions), 2)
    debits = round(sum(item["debit"] for item in transactions), 2)
    calculated = round((opening or 0.0) + credits - debits, 2) if opening is not None else None
    difference = round((closing or 0.0) - calculated, 2) if closing is not None and calculated is not None else None
    statement_id = "statement_" + source_hash[:20]
    return {
        "statement_id": statement_id,
        "account_id": "pacifico_cc_04996984",
        "bank": "Banco del Pacifico",
        "statement_period_start": period_start,
        "statement_period_end": period_end,
        "opening_balance": opening,
        "closing_balance": closing,
        "parsed_credits": credits,
        "parsed_debits": debits,
        "calculated_closing_balance": calculated,
        "balance_difference": difference,
        "continuity_status": "balanced" if difference == 0 else "exception",
        "source_file": source.name,
        "source_path": str(source),
        "source_sha256": source_hash,
        "page_count": len(pages),
        "transaction_count": len(transactions),
        "parser_version": PARSER_VERSION,
        "ocr_text_by_page": pages,
        "transactions": transactions,
    }


def _date_distance(left: str, right: str) -> int:
    try:
        return abs((date.fromisoformat(left) - date.fromisoformat(right)).days)
    except Exception:
        return 9999


def generate_candidates(db: Any, statement: dict[str, Any]) -> list[dict[str, Any]]:
    people = list(db.contifico_personas.find({}, {"_id": 0, "persona_id": 1, "nombre": 1, "nombre_norm": 1}))
    candidates: list[dict[str, Any]] = []
    for transaction in statement["transactions"]:
        if transaction["direction"] != "credit":
            continue
        description = transaction["description_normalized"]
        matched_people = []
        for person in people:
            name = _normalized(str(person.get("nombre_norm") or person.get("nombre") or ""))
            tokens = [token for token in name.split() if len(token) >= 4]
            if len(tokens) >= 2 and sum(token in description for token in tokens) >= 2:
                matched_people.append(person)
        for person in matched_people[:5]:
            documents = list(db.contifico_documents.find(
                {"persona_id": person["persona_id"], "tipo_documento": "FAC", "total_num": {"$gt": 0}},
                {"_id": 0, "contifico_id": 1, "documento": 1, "fecha_iso": 1, "total_num": 1, "estado": 1},
            ))
            eligible = [doc for doc in documents if _date_distance(transaction["transaction_date"], str(doc.get("fecha_iso") or "")) <= 45]
            for size in range(1, min(3, len(eligible)) + 1):
                for group in itertools.combinations(eligible, size):
                    total = round(sum(float(doc.get("total_num") or 0) for doc in group), 2)
                    delta = round(abs(total - transaction["amount"]), 2)
                    if delta > 0.02:
                        continue
                    max_days = max(_date_distance(transaction["transaction_date"], str(doc.get("fecha_iso") or "")) for doc in group)
                    reasons = ["exact_amount", "party_name_in_bank_description", f"date_distance_max_{max_days}_days"]
                    if size > 1:
                        reasons.append(f"split_merge_{size}_documents")
                    score = max(0.0, round(0.99 - min(max_days, 45) * 0.002 - (size - 1) * 0.03, 3))
                    doc_ids = sorted(str(doc["contifico_id"]) for doc in group)
                    candidate_key = transaction["transaction_id"] + ":" + ":".join(doc_ids)
                    candidates.append({
                        "candidate_id": "recon_" + hashlib.sha256(candidate_key.encode()).hexdigest()[:20],
                        "statement_id": statement["statement_id"],
                        "transaction_id": transaction["transaction_id"],
                        "transaction_date": transaction["transaction_date"],
                        "amount": transaction["amount"],
                        "party_id": person["persona_id"],
                        "party_name": person.get("nombre"),
                        "document_ids": doc_ids,
                        "documents": list(group),
                        "candidate_total": total,
                        "amount_delta": delta,
                        "score": score,
                        "reasons": reasons,
                        "status": "candidate",
                        "requires_human_approval": True,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
    return candidates


def persist_pilot(db: Any, statement: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    statement_doc = {key: value for key, value in statement.items() if key not in {"transactions", "ocr_text_by_page"}}
    statement_doc.update({"updated_at": now, "environment": "staging"})
    db.quoteops_bank_statements.update_one({"statement_id": statement["statement_id"]}, {"$set": statement_doc, "$setOnInsert": {"created_at": now}}, upsert=True)
    for transaction in statement["transactions"]:
        transaction_doc = {**transaction, "statement_id": statement["statement_id"], "environment": "staging", "updated_at": now}
        db.quoteops_bank_transactions.update_one({"transaction_id": transaction["transaction_id"]}, {"$set": transaction_doc, "$setOnInsert": {"created_at": now}}, upsert=True)
    for candidate in candidates:
        db.quoteops_reconciliation_candidates.update_one({"candidate_id": candidate["candidate_id"]}, {"$set": candidate}, upsert=True)
    return {
        "statement_id": statement["statement_id"],
        "transactions": len(statement["transactions"]),
        "candidates": len(candidates),
        "exceptions": 1 if statement["continuity_status"] == "exception" else 0,
    }
