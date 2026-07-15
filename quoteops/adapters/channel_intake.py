from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


class ChannelIntakeRouter:
    """Normalizes all inbound channels into one idempotent QuoteOps case."""

    def __init__(self, secret: str = "") -> None:
        self.secret = secret
        self.seen: dict[str, dict] = {}

    def ingest(self, channel: str, payload: dict[str, Any], signature: str = "") -> dict[str, Any]:
        if channel in {"whatsapp", "telegram"} and self.secret and not self._valid_signature(payload, signature):
            return {"ok": False, "status": "rejected", "reason": "invalid_signature"}
        event_id = str(payload.get("event_id") or payload.get("update_id") or payload.get("message_id") or self._digest(payload))
        if event_id in self.seen:
            return {**self.seen[event_id], "deduplicated": True}
        text = str(payload.get("text") or payload.get("message") or payload.get("body") or "").strip()
        contact = str(payload.get("contact") or payload.get("phone") or payload.get("username") or "").strip()
        name = str(payload.get("customer_name") or payload.get("name") or payload.get("from_name") or channel.title()).strip()
        result = {"ok": True, "status": "accepted", "event_id": event_id, "deduplicated": False, "intake": {"source_channel": channel, "customer_name": name, "contact": contact, "original_text": text, "attachments": payload.get("attachments") or []}}
        self.seen[event_id] = result
        return result

    def _valid_signature(self, payload: dict[str, Any], signature: str) -> bool:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        expected = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature.removeprefix("sha256="))

    @staticmethod
    def _digest(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:24]
