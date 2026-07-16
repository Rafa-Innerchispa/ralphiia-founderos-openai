from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from quoteops.contracts import TaxpayerEstablishment, TaxpayerVerification
from quoteops.settings import Settings


class TaxpayerRegistryError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 502,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message
        self.status_code = status_code
        self.retryable = retryable


class TaxpayerRegistryPort(Protocol):
    async def lookup(
        self, value: str, *, force_refresh: bool = False
    ) -> TaxpayerVerification: ...


def normalize_ruc(value: str) -> str:
    clean = str(value or "").strip().replace("-", "").replace(" ", "")
    if not clean.isdigit() or len(clean) != 13:
        raise TaxpayerRegistryError(
            "invalid_ruc_format",
            "El RUC debe contener exactamente 13 dígitos.",
            status_code=422,
        )
    province = int(clean[:2])
    if province not in {*range(1, 25), 30} or clean[-3:] == "000":
        raise TaxpayerRegistryError(
            "invalid_ruc_format",
            "El RUC no tiene una estructura ecuatoriana válida.",
            status_code=422,
        )
    return clean


def ecuador_cedula_checksum_valid(value: str) -> bool:
    clean = str(value or "").strip().replace("-", "").replace(" ", "")
    if not clean.isdigit() or len(clean) != 10:
        return False
    province = int(clean[:2])
    if province not in range(1, 25) or int(clean[2]) > 5:
        return False
    total = 0
    for index, digit in enumerate(clean[:9]):
        product = int(digit) * (2 if index % 2 == 0 else 1)
        total += product - 9 if product > 9 else product
    return (10 - total % 10) % 10 == int(clean[9])


def normalize_ec_identifier(value: str) -> tuple[str, str]:
    clean = str(value or "").strip().replace("-", "").replace(" ", "")
    if len(clean) == 10 and ecuador_cedula_checksum_valid(clean):
        return clean, "cedula"
    if len(clean) == 13:
        ruc = normalize_ruc(clean)
        if ecuador_ruc_checksum_valid(ruc):
            return ruc, "ruc"
    raise TaxpayerRegistryError(
        "invalid_ec_identifier",
        "La cédula o RUC no supera la validación local ecuatoriana.",
        status_code=422,
    )


def ecuador_ruc_checksum_valid(ruc: str) -> bool:
    clean = normalize_ruc(ruc)
    third = int(clean[2])
    if third <= 5:
        coefficients = (2, 1, 2, 1, 2, 1, 2, 1, 2)
        total = sum((int(digit) * coefficient - 9 if int(digit) * coefficient > 9 else int(digit) * coefficient)
                    for digit, coefficient in zip(clean[:9], coefficients))
        check_digit = (10 - total % 10) % 10
        return check_digit == int(clean[9]) and clean[-3:] == "001"
    if third == 6:
        coefficients = (3, 2, 7, 6, 5, 4, 3, 2)
        total = sum(int(digit) * coefficient for digit, coefficient in zip(clean[:8], coefficients))
        check_digit = 11 - total % 11
        if check_digit == 11:
            check_digit = 0
        return check_digit == int(clean[8]) and clean[-4:] == "0001"
    if third == 9:
        coefficients = (4, 3, 2, 7, 6, 5, 4, 3, 2)
        total = sum(int(digit) * coefficient for digit, coefficient in zip(clean[:9], coefficients))
        check_digit = 11 - total % 11
        if check_digit == 11:
            check_digit = 0
        return check_digit == int(clean[9]) and clean[-3:] == "001"
    return False


@dataclass
class _TokenState:
    value: str = ""
    expires_at: float = 0.0


class IntuitoAzureRucAdapter:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.transport = transport
        self._token_state = _TokenState()
        self._token_lock = asyncio.Lock()
        self._cache: dict[str, tuple[float, TaxpayerVerification]] = {}

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.ruc_api_live_enabled
            and self.settings.ruc_api_username
            and self.settings.ruc_api_password
        )

    async def lookup(self, value: str, *, force_refresh: bool = False) -> TaxpayerVerification:
        ruc = normalize_ruc(value)
        now = time.time()
        cached = self._cache.get(ruc)
        if cached and cached[0] > now and not force_refresh:
            return cached[1].model_copy(update={"cache_status": "fresh_cache"})
        if not self.configured:
            raise TaxpayerRegistryError(
                "ruc_provider_not_configured",
                "La consulta RUC en vivo no está habilitada en el servidor.",
                status_code=503,
            )

        timeout = httpx.Timeout(self.settings.ruc_api_timeout_seconds)
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            token = await self._get_token(client, force=False)
            response = await self._lookup_with_bounded_retry(client, ruc, token)
            if response.status_code == 401:
                token = await self._get_token(client, force=True)
                response = await self._lookup_with_bounded_retry(client, ruc, token)
            verification = self._parse_lookup_response(ruc, response)

        self._cache[ruc] = (
            now + max(1, self.settings.ruc_api_cache_ttl_seconds),
            verification,
        )
        return verification

    async def _get_token(self, client: httpx.AsyncClient, *, force: bool) -> str:
        async with self._token_lock:
            if not force and self._token_state.value and self._token_state.expires_at > time.time() + 30:
                return self._token_state.value
            try:
                response = await client.post(
                    f"{self.settings.ruc_api_token_base_url.rstrip('/')}/v1/deuna/creacion-token",
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                    json={
                        "usuario": self.settings.ruc_api_username,
                        "pass": self.settings.ruc_api_password,
                    },
                )
            except httpx.TimeoutException as exc:
                raise TaxpayerRegistryError("token_timeout", "El proveedor de token no respondió a tiempo.", retryable=True) from exc
            except httpx.HTTPError as exc:
                raise TaxpayerRegistryError("token_network_error", "No se pudo conectar con el proveedor de token.", retryable=True) from exc
            payload = _safe_json(response)
            token = _extract_token(payload)
            if response.status_code not in {200, 201} or not token:
                raise TaxpayerRegistryError(
                    "token_rejected" if response.status_code in {400, 401, 403} else "token_upstream_error",
                    "El proveedor no entregó un token utilizable.",
                    status_code=502,
                    retryable=response.status_code >= 500,
                )
            self._token_state = _TokenState(token, _token_expiry(token))
            return token

    async def _lookup_with_bounded_retry(
        self, client: httpx.AsyncClient, ruc: str, token: str
    ) -> httpx.Response:
        url = f"{self.settings.ruc_api_lookup_base_url.rstrip('/')}/api/ruc/{quote(ruc, safe='')}"
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await client.get(
                    url,
                    headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.15 * (2**attempt))
                    continue
                raise TaxpayerRegistryError(
                    "lookup_network_error",
                    "No se pudo completar la verificación del RUC.",
                    retryable=True,
                ) from exc
            if response.status_code < 500 or attempt == 2:
                return response
            await asyncio.sleep(0.15 * (2**attempt))
        raise TaxpayerRegistryError("lookup_network_error", "No se pudo completar la verificación.") from last_error

    def _parse_lookup_response(self, ruc: str, response: httpx.Response) -> TaxpayerVerification:
        payload = _safe_json(response)
        if response.status_code == 401:
            raise TaxpayerRegistryError("unauthorized_after_refresh", "El proveedor rechazó la autenticación.", status_code=502)
        if response.status_code == 404:
            message = _response_message(payload).lower()
            if "faltante" in message or "información" in message or "informacion" in message:
                code = "taxpayer_information_missing"
                public = "El RUC existe, pero el proveedor reporta información faltante."
            else:
                code = "ruc_not_found"
                public = "El proveedor no encontró información válida para ese RUC."
            raise TaxpayerRegistryError(code, public, status_code=404)
        if response.status_code not in {200, 201}:
            raise TaxpayerRegistryError(
                "lookup_upstream_error",
                "El proveedor de RUC devolvió un error.",
                status_code=502,
                retryable=response.status_code >= 500,
            )
        main = ((payload.get("data") or {}).get("main") if isinstance(payload, dict) else None) or []
        if isinstance(main, dict):
            main = [main]
        if not main or not isinstance(main[0], dict):
            raise TaxpayerRegistryError("malformed_provider_response", "La respuesta del proveedor no tiene el formato esperado.")
        record = main[0]
        establishments_raw = record.get("addit") or []
        if isinstance(establishments_raw, dict):
            establishments_raw = [establishments_raw]
        establishments = [
            TaxpayerEstablishment(
                commercial_name=str(item.get("nombreFantasiaComercial") or "").strip(),
                number=str(item.get("numeroEstablecimiento") or "").strip(),
                establishment_type=str(item.get("tipoEstablecimiento") or "").strip(),
                full_address=str(item.get("direccionCompleta") or "").strip(),
            )
            for item in establishments_raw
            if isinstance(item, dict)
        ]
        retrieved_at = datetime.now(timezone.utc).isoformat()
        verification_id = "rucv_" + sha256(f"{ruc}:{retrieved_at}".encode()).hexdigest()[:18]
        return TaxpayerVerification(
            verification_id=verification_id,
            ruc=str(record.get("numeroRuc") or ruc).strip(),
            legal_name=str(record.get("razonSocial") or "").strip(),
            commercial_name=str(record.get("nombreComercial") or "").strip(),
            activity=str(record.get("actividadContribuyente") or "").strip(),
            legal_representative=str(record.get("representanteLegal") or "").strip(),
            establishments=establishments,
            retrieved_at=retrieved_at,
            checksum_valid=ecuador_ruc_checksum_valid(ruc),
            cache_status="live",
        )


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise TaxpayerRegistryError("malformed_provider_response", "El proveedor devolvió una respuesta no válida.") from exc
    return value if isinstance(value, dict) else {}


def _extract_token(payload: dict[str, Any]) -> str:
    data = payload.get("data") or {}
    if isinstance(data, dict):
        value = data.get("response") or data.get("token")
        if isinstance(value, str):
            return value.strip()
    return ""


def _token_expiry(token: str) -> float:
    try:
        segment = token.split(".")[1]
        segment += "=" * (-len(segment) % 4)
        payload = json.loads(base64.urlsafe_b64decode(segment.encode()))
        exp = float(payload.get("exp", 0))
        if exp > time.time() + 60:
            return exp
    except (ValueError, IndexError, KeyError, json.JSONDecodeError):
        pass
    return time.time() + 3600


def _response_message(payload: dict[str, Any]) -> str:
    return str(payload.get("message") or payload.get("msgRetorno") or payload.get("error") or "")
