from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from pymongo import MongoClient


class QuoteExecutionService:
    """Staging-safe approval, PDF artifact and channel delivery router."""

    def __init__(self, settings) -> None:
        self.settings = settings
        self.artifact_root = Path(settings.quoteops_artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.approvals: dict[str, dict] = {}
        self.db = None
        self.mongo_client = None
        try:
            client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=1000)
            client.admin.command("ping")
            self.mongo_client = client
            self.db = client[settings.quoteops_mongo_db]
            self.db.quoteops_approvals.create_index("approval_id", unique=True)
            self.db.quoteops_deliveries.create_index("delivery_id", unique=True)
        except Exception:
            try:
                client.close()
            except Exception:
                pass
            self.db = None

    def close(self) -> None:
        if self.mongo_client is not None:
            self.mongo_client.close()
            self.mongo_client = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def approve(self, request: dict) -> dict:
        intake = request.get("intake") or {}
        missing = [key for key in ("customer_name", "contact", "original_text") if not str(intake.get(key) or "").strip()]
        approval_id = "approval_" + uuid4().hex[:18]
        timeline = [self._event("intake_validated", "Intake validado")]
        if missing:
            return {"ok": True, "approval_id": approval_id, "status": "blocked", "blockers": missing, "timeline": timeline + [self._event("approval_blocked", "Faltan datos obligatorios")]}
        artifact_id = "artifact_" + uuid4().hex[:18]
        path = self.artifact_root / f"{artifact_id}.pdf"
        path.write_bytes(self._pdf(str(intake["customer_name"]), str(intake["original_text"])))
        record = {"approval_id": approval_id, "artifact_id": artifact_id, "path": str(path), "timeline": timeline + [self._event("approved", "Aprobacion humana registrada")]}
        self.approvals[approval_id] = record
        if self.db is not None:
            self.db.quoteops_approvals.replace_one({"approval_id": approval_id}, record, upsert=True)
        return {"ok": True, "approval_id": approval_id, "status": "approved", "mode": request.get("mode", "sandbox"), "artifact_id": artifact_id, "pdf_url": f"/api/quote/artifacts/{artifact_id}.pdf", "timeline": self.approvals[approval_id]["timeline"]}

    def deliver(self, request: dict) -> dict:
        approval_id = request.get("approval_id")
        record = self.approvals.get(approval_id)
        if record is None and self.db is not None and approval_id:
            record = self.db.quoteops_approvals.find_one({"approval_id": approval_id}, {"_id": 0})
        mode = request.get("mode", "sandbox")
        channels = request.get("channels") or ["web"]
        if not record:
            return {"ok": True, "status": "blocked", "channels": channels, "mode": mode, "timeline": [self._event("delivery_blocked", "Aprobacion no encontrada")]}
        if mode == "owner" and not self.settings.allow_production_writes:
            return {"ok": True, "status": "blocked", "channels": channels, "mode": mode, "timeline": record["timeline"] + [self._event("delivery_blocked", "Produccion deshabilitada en staging")]}
        delivery_id = "delivery_" + uuid4().hex[:18]
        status = "simulated" if mode == "sandbox" else ("queued" if mode == "owner" else "registered")
        event_kind = {
            "simulated": "delivery_simulated",
            "queued": "delivery_queued",
            "registered": "delivery_registered",
        }[status]
        delivery = {"delivery_id": delivery_id, "approval_id": approval_id, "status": status, "channels": channels, "mode": mode, "timeline": record["timeline"] + [self._event(event_kind, "Entrega registrada sin envio arbitrario")]}
        if self.db is not None:
            # PyMongo adds an ObjectId to inserted dictionaries; persist a copy so API output remains JSON-safe.
            self.db.quoteops_deliveries.insert_one(dict(delivery))
        return {"ok": True, **delivery}

    def artifact_path(self, artifact_id: str):
        path = self.artifact_root / f"{artifact_id}.pdf"
        return path if path.exists() else None

    @staticmethod
    def _event(kind: str, detail: str) -> dict:
        return {"at": time.time(), "kind": kind, "detail": detail}

    @staticmethod
    def _pdf(customer: str, text: str) -> bytes:
        def pdf_text(value: str, limit: int) -> str:
            clean = str(value or "").encode("ascii", "replace").decode("ascii")[:limit]
            return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", " ")

        content = f"BT /F1 12 Tf 50 760 Td 16 TL (RalphiIA QuoteOps) Tj T* (Customer: {pdf_text(customer, 100)}) Tj T* (Quote: {pdf_text(text, 400)}) Tj ET"
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>", b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", f"<< /Length {len(content)} >>\nstream\n{content}\nendstream".encode()]
        out = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(out))
            out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
        xref = len(out)
        out.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        out.extend("".join(f"{n:010d} 00000 n \n" for n in offsets[1:]).encode())
        out.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
        return bytes(out)
