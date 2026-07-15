from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4


class QuoteExecutionService:
    """Staging-safe approval, PDF artifact and channel delivery router."""

    def __init__(self, settings) -> None:
        self.settings = settings
        self.artifact_root = Path(settings.quoteops_artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.approvals: dict[str, dict] = {}

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
        self.approvals[approval_id] = {"artifact_id": artifact_id, "path": str(path), "timeline": timeline + [self._event("approved", "Aprobacion humana registrada")]}
        return {"ok": True, "approval_id": approval_id, "status": "approved", "mode": request.get("mode", "sandbox"), "artifact_id": artifact_id, "pdf_url": f"/api/quote/artifacts/{artifact_id}.pdf", "timeline": self.approvals[approval_id]["timeline"]}

    def deliver(self, request: dict) -> dict:
        record = self.approvals.get(request.get("approval_id"))
        mode = request.get("mode", "sandbox")
        channels = request.get("channels") or ["web"]
        if not record:
            return {"ok": True, "status": "blocked", "channels": channels, "mode": mode, "timeline": [self._event("delivery_blocked", "Aprobacion no encontrada")]}
        if mode == "owner" and not self.settings.allow_production_writes:
            return {"ok": True, "status": "blocked", "channels": channels, "mode": mode, "timeline": record["timeline"] + [self._event("delivery_blocked", "Produccion deshabilitada en staging")]}
        return {"ok": True, "delivery_id": "delivery_" + uuid4().hex[:18], "status": "simulated" if mode == "sandbox" else "queued", "channels": channels, "mode": mode, "timeline": record["timeline"] + [self._event("delivery_simulated" if mode == "sandbox" else "delivery_queued", "Entrega registrada sin envio arbitrario")]}

    def artifact_path(self, artifact_id: str):
        path = self.artifact_root / f"{artifact_id}.pdf"
        return path if path.exists() else None

    @staticmethod
    def _event(kind: str, detail: str) -> dict:
        return {"at": time.time(), "kind": kind, "detail": detail}

    @staticmethod
    def _pdf(customer: str, text: str) -> bytes:
        content = f"BT /F1 12 Tf 50 760 Td (RalphiIA QuoteOps) Tj T* (Cliente: {customer[:100]}) Tj T* (Propuesta: {text[:400]}) Tj ET"
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
