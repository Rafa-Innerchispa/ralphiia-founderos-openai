from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient


MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


class IessPaymentError(RuntimeError):
    pass


def parse_iess_payment_ocr(text: str) -> dict[str, Any]:
    compact = re.sub(r"\s+", "", text or "")
    amount_match = re.search(r"pagado\$([0-9]+(?:[.,][0-9]{2})?)", compact, re.I)
    plan_match = re.search(r"PLANILLAS:([0-9]{10,})", compact, re.I)
    type_match = re.search(r"PLANILLAS:[0-9]{10,}:([0-9]{3}):", compact, re.I)
    receipt_match = re.search(r"(?:N[uú]mero)?decomprobante:([0-9]+)", compact, re.I)
    date_match = re.search(r"([0-9]{1,2})(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\.?([0-9]{4})-([0-9]{1,2}):([0-9]{2})", compact, re.I)
    paid_at = ""
    if date_match:
        day, month_name, year, hour, minute = date_match.groups()
        month = MONTHS[month_name.lower()]
        paid_at = datetime(int(year), month, int(day), int(hour), int(minute), tzinfo=timezone.utc).isoformat()
    return {
        "amount": float(amount_match.group(1).replace(",", ".")) if amount_match else 0.0,
        "plan_code": plan_match.group(1) if plan_match else "",
        "plan_type": type_match.group(1) if type_match else "",
        "bank_receipt": receipt_match.group(1) if receipt_match else "",
        "paid_at": paid_at,
    }


def extract_ocr_text(image_path: str | Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:
        raise IessPaymentError("rapidocr_not_available") from exc
    result, _ = RapidOCR()(str(image_path))
    if not result:
        raise IessPaymentError("ocr_no_text")
    return "\n".join(str(item[1]) for item in result)


class IessPaymentService:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)
        self.db = self.client.pcdoctor_swarm
        self.evidence_root = Path(getattr(settings, "iess_evidence_root", "/home/rlopez/data/ralphiia-quoteops/iess-evidence"))
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self.db.whatsapp_pending_actions.create_index("action_id", unique=True, sparse=True)
        self.db.accounting_payments.create_index("source_action_id", unique=True, sparse=True)

    def close(self) -> None:
        self.client.close()

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = str(payload.get("image_base64") or "")
        message_id = str(payload.get("message_id") or "").strip()
        if not encoded or not message_id:
            return {"ok": False, "status": "needs_clarification", "error": "image_base64_and_message_id_required"}
        blob = base64.b64decode(encoded)
        digest = hashlib.sha256(blob).hexdigest()
        image_path = self.evidence_root / f"{digest}.jpg"
        if not image_path.exists():
            image_path.write_bytes(blob)
            image_path.chmod(0o600)
        ocr_text = extract_ocr_text(image_path)
        fields = parse_iess_payment_ocr(ocr_text)
        missing = [key for key in ("amount", "plan_code", "bank_receipt") if not fields.get(key)]
        if missing:
            return {
                "ok": True,
                "status": "needs_clarification",
                "missing": missing,
                "fields": fields,
                "reply": "Recibí un comprobante IESS, pero no pude leer todos los campos. Envíame otra foto más nítida o escribe número de planilla, monto y comprobante.",
            }
        voucher = self.db.ralfia_iess_vouchers.find_one({"comprobante_id": fields["plan_code"]}, {"_id": 0, "raw_text": 0, "ocr_text": 0})
        action_id = "iesspay_" + hashlib.sha256(message_id.encode()).hexdigest()[:16]
        existing = self.db.whatsapp_pending_actions.find_one({"action_id": action_id}, {"_id": 0})
        if existing and existing.get("status") == "confirmed":
            return {"ok": True, "status": "already_confirmed", "action_id": action_id, "payment_id": existing.get("payment_id"), "reply": "Este pago IESS ya fue registrado; no lo dupliqué."}
        period = str((voucher or {}).get("periodo") or "sin período identificado")
        action = {
            "action_id": action_id,
            "action_type": "iess_payment",
            "status": "awaiting_confirmation",
            "message_id": message_id,
            "sender": str(payload.get("sender") or ""),
            "caption": str(payload.get("caption") or ""),
            "evidence_sha256": digest,
            "evidence_path": str(image_path),
            "extraction_source": "rapidocr",
            "fields": fields,
            "voucher": voucher,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.whatsapp_pending_actions.update_one(
            {"action_id": action_id},
            {"$set": action, "$setOnInsert": {"created_at": action["updated_at"]}},
            upsert=True,
        )
        match_text = f"planilla de {period}" if voucher else "una planilla que aún no está emparejada"
        return {
            "ok": True,
            "status": "awaiting_confirmation",
            "action_id": action_id,
            "fields": fields,
            "voucher": voucher,
            "reply": (
                f"Detecté un pago IESS de USD {fields['amount']:.2f} para la {match_text}.\n"
                f"Planilla: {fields['plan_code']} · tipo {fields['plan_type'] or 'N/D'}\n"
                f"Comprobante bancario: {fields['bank_receipt']}\n"
                f"Responde CONFIRMAR PAGO {action_id} para registrarlo o CANCELAR PAGO {action_id}."
            ),
        }

    @staticmethod
    def _same_sender(expected: str, actual: str) -> bool:
        expected_digits = "".join(char for char in expected if char.isdigit())
        actual_digits = "".join(char for char in actual if char.isdigit())
        return bool(expected_digits and actual_digits and expected_digits == actual_digits)

    def confirm(self, action_id: str, approved_by: str, request_sender: str = "") -> dict[str, Any]:
        action = self.db.whatsapp_pending_actions.find_one({"action_id": action_id})
        if not action:
            return {"ok": False, "error": "pending_action_not_found"}
        if request_sender and not self._same_sender(str(action.get("sender") or ""), request_sender):
            return {"ok": False, "error": "sender_not_authorized_for_action"}
        if action.get("status") == "confirmed":
            return {"ok": True, "status": "already_confirmed", "payment_id": action.get("payment_id"), "payable_id": action.get("payable_id")}
        fields = action.get("fields") or {}
        voucher = action.get("voucher") or {}
        plan_code = str(fields.get("plan_code") or "")
        if not plan_code or str(voucher.get("comprobante_id") or "") != plan_code:
            return {"ok": False, "error": "voucher_match_required"}
        now = datetime.now(timezone.utc).isoformat()
        payable_id = f"payable_iess_{plan_code}"
        payment_id = f"payment_iess_{fields['bank_receipt']}"
        payable = {
            "payable_id": payable_id,
            "supplier_name": "IESS",
            "entity_id": "ent_pcdoctor",
            "payable_type": "transfer",
            "reference": plan_code,
            "amount": float(fields["amount"]),
            "currency": "USD",
            "status": "paid",
            "paid_at": fields.get("paid_at") or now,
            "payment_id": payment_id,
            "notes": f"Planilla IESS {voucher.get('periodo') or ''}".strip(),
            "source": "whatsapp_iess_payment",
            "updated_at": now,
        }
        payment = {
            "payment_id": payment_id,
            "payable_id": payable_id,
            "entity_id": "ent_pcdoctor",
            "amount": float(fields["amount"]),
            "currency": "USD",
            "method": "transfer",
            "direction": "outbound",
            "paid_at": fields.get("paid_at") or now,
            "reference": str(fields["bank_receipt"]),
            "notes": f"Pago planilla IESS {plan_code}",
            "recorded_by": approved_by,
            "source": "whatsapp_iess_payment",
            "source_action_id": action_id,
            "evidence_sha256": action.get("evidence_sha256"),
            "created_at": now,
            "updated_at": now,
        }
        self.db.accounting_payables.update_one({"payable_id": payable_id}, {"$set": payable, "$setOnInsert": {"created_at": now}}, upsert=True)
        self.db.accounting_payments.update_one({"source_action_id": action_id}, {"$setOnInsert": payment}, upsert=True)
        self.db.ralfia_iess_vouchers.update_one(
            {"comprobante_id": plan_code},
            {"$set": {"status": "paid", "amount_paid": float(fields["amount"]), "bank_receipt": str(fields["bank_receipt"]), "payment_id": payment_id, "payment_evidence_sha256": action.get("evidence_sha256"), "paid_at": payment["paid_at"], "updated_at": now}},
        )
        self.db.whatsapp_pending_actions.update_one(
            {"action_id": action_id},
            {"$set": {"status": "confirmed", "approved_by": approved_by, "confirmed_at": now, "payment_id": payment_id, "payable_id": payable_id, "updated_at": now}},
        )
        return {"ok": True, "status": "confirmed", "action_id": action_id, "payment_id": payment_id, "payable_id": payable_id, "plan_code": plan_code, "amount": payment["amount"]}

    def cancel(self, action_id: str, request_sender: str = "") -> dict[str, Any]:
        action = self.db.whatsapp_pending_actions.find_one({"action_id": action_id})
        if not action:
            return {"ok": False, "error": "pending_action_not_found"}
        if request_sender and not self._same_sender(str(action.get("sender") or ""), request_sender):
            return {"ok": False, "error": "sender_not_authorized_for_action"}
        if action.get("status") == "confirmed":
            return {"ok": False, "error": "confirmed_action_cannot_be_cancelled"}
        now = datetime.now(timezone.utc).isoformat()
        self.db.whatsapp_pending_actions.update_one(
            {"action_id": action_id},
            {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
        )
        return {"ok": True, "status": "cancelled", "action_id": action_id}
