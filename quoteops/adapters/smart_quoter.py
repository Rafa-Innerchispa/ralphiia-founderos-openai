from __future__ import annotations

from typing import Any

import httpx


class SmartQuoterAdapter:
    """Read-only bridge to the existing Smart Quoter service on port 2026."""

    def __init__(self, base_url: str = "http://127.0.0.1:2026", timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def client_lookup(self, client_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/api/quote/client-lookup/{client_id}")
        return self._response(response)

    async def diagnose(self, transcription: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=max(self.timeout, 95.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/quote/diagnose",
                json={"transcription": transcription},
            )
        return self._response(response)

    async def refine(self, current_analysis: dict[str, Any], prompt: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=max(self.timeout, 95.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/quote/diagnose/refine",
                json={"current_analysis": current_analysis, "prompt": prompt},
            )
        return self._response(response)

    @staticmethod
    def _response(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {"ok": False, "error": "smart_quoter_invalid_json"}
        if response.is_error:
            return {"ok": False, "status_code": response.status_code, "error": payload}
        return {"ok": True, "status_code": response.status_code, "data": payload}
