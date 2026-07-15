from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram rejects an outbound delivery."""


class TelegramDelivery:
    """Small, explicit Telegram Bot API client with no credential logging."""

    def __init__(self, bot_token: str, timeout_seconds: float = 12) -> None:
        self.bot_token = bot_token.strip()
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.bot_token)

    def send_message(self, chat_id: str | int, text: str) -> dict[str, Any]:
        return self._post("sendMessage", {"chat_id": chat_id, "text": text})

    def send_document(self, chat_id: str | int, path: str | Path, caption: str = "") -> dict[str, Any]:
        document = Path(path)
        if not document.is_file():
            raise TelegramDeliveryError("document_not_found")
        if not self.configured:
            raise TelegramDeliveryError("telegram_not_configured")
        url = self._url("sendDocument")
        try:
            with document.open("rb") as stream, httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    url,
                    data={"chat_id": str(chat_id), "caption": caption},
                    files={"document": (document.name, stream, "application/pdf")},
                )
        except httpx.HTTPError as exc:
            raise TelegramDeliveryError("telegram_network_error") from exc
        return self._decode(response)

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise TelegramDeliveryError("telegram_not_configured")
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(self._url(method), json=payload)
        except httpx.HTTPError as exc:
            raise TelegramDeliveryError("telegram_network_error") from exc
        return self._decode(response)

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    @staticmethod
    def _decode(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise TelegramDeliveryError("telegram_invalid_response") from exc
        if response.status_code >= 400 or not body.get("ok"):
            raise TelegramDeliveryError("telegram_delivery_rejected")
        return body
