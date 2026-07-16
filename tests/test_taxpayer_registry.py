import asyncio
import unittest

import httpx

from quoteops.adapters.customer_identity import compare_customer
from quoteops.adapters.taxpayer_registry import (
    IntuitoAzureRucAdapter,
    TaxpayerRegistryError,
    ecuador_cedula_checksum_valid,
    ecuador_ruc_checksum_valid,
    normalize_ec_identifier,
    normalize_ruc,
)
from quoteops.contracts import IdentityMatch
from quoteops.settings import Settings


class TestTaxpayerRegistry(unittest.TestCase):
    def test_local_validation_rejects_without_network(self) -> None:
        with self.assertRaises(TaxpayerRegistryError):
            normalize_ruc("09923ABC")
        self.assertTrue(ecuador_ruc_checksum_valid("0992364866001"))

    def test_cedula_and_ruc_share_local_identifier_boundary(self) -> None:
        self.assertTrue(ecuador_cedula_checksum_valid("1710034065"))
        self.assertEqual(normalize_ec_identifier("1710034065"), ("1710034065", "cedula"))
        self.assertEqual(normalize_ec_identifier("0992364866001"), ("0992364866001", "ruc"))
        with self.assertRaises(TaxpayerRegistryError):
            normalize_ec_identifier("1710034064")

    def test_live_contract_token_cache_and_normalization(self) -> None:
        calls = {"token": 0, "lookup": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("creacion-token"):
                calls["token"] += 1
                return httpx.Response(200, json={"data": {"response": "opaque-token"}, "error": False})
            calls["lookup"] += 1
            return httpx.Response(
                200,
                json={
                    "data": {
                        "main": [
                            {
                                "numeroRuc": "0992364866001",
                                "razonSocial": "Empresa Verificada S.A.",
                                "nombreComercial": "Empresa Demo",
                                "actividadContribuyente": "Servicios tecnológicos",
                                "representanteLegal": "Representante",
                                "identificacionLegal": "must-not-be-returned",
                                "addit": [
                                    {
                                        "numeroEstablecimiento": "001",
                                        "tipoEstablecimiento": "MATRIZ",
                                        "direccionCompleta": "Guayaquil",
                                    }
                                ],
                            }
                        ]
                    }
                },
            )

        adapter = IntuitoAzureRucAdapter(
            Settings(
                ruc_api_live_enabled=True,
                ruc_api_username="test-user",
                ruc_api_password="test-password",
            ),
            transport=httpx.MockTransport(handler),
        )
        first = asyncio.run(adapter.lookup("0992364866001"))
        second = asyncio.run(adapter.lookup("0992364866001"))
        self.assertEqual(first.legal_name, "Empresa Verificada S.A.")
        self.assertEqual(first.establishments[0].full_address, "Guayaquil")
        self.assertNotIn("identificacionLegal", first.model_dump())
        self.assertEqual(second.cache_status, "fresh_cache")
        self.assertEqual(calls, {"token": 1, "lookup": 1})

    def test_401_refreshes_token_exactly_once(self) -> None:
        calls = {"token": 0, "lookup": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("creacion-token"):
                calls["token"] += 1
                return httpx.Response(200, json={"data": {"response": f"token-{calls['token']}"}})
            calls["lookup"] += 1
            if calls["lookup"] == 1:
                return httpx.Response(401, json={"message": "unauthorized"})
            return httpx.Response(
                200,
                json={
                    "data": {
                        "main": [
                            {"numeroRuc": "0992364866001", "razonSocial": "Empresa S.A.", "addit": []}
                        ]
                    }
                },
            )

        adapter = IntuitoAzureRucAdapter(
            Settings(
                ruc_api_live_enabled=True,
                ruc_api_username="test-user",
                ruc_api_password="test-password",
            ),
            transport=httpx.MockTransport(handler),
        )
        result = asyncio.run(adapter.lookup("0992364866001"))
        self.assertEqual(result.legal_name, "Empresa S.A.")
        self.assertEqual(calls, {"token": 2, "lookup": 2})

    def test_comparison_exposes_name_conflict_without_overwrite(self) -> None:
        adapter_result = asyncio.run(
            IntuitoAzureRucAdapter(
                Settings(
                    ruc_api_live_enabled=True,
                    ruc_api_username="test-user",
                    ruc_api_password="test-password",
                ),
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json={"data": {"response": "token"}})
                    if request.url.path.endswith("creacion-token")
                    else httpx.Response(
                        200,
                        json={"data": {"main": [{"numeroRuc": "0992364866001", "razonSocial": "Nombre Oficial S.A.", "addit": []}]}},
                    )
                ),
            ).lookup("0992364866001")
        )
        comparison, draft = compare_customer(
            adapter_result,
            [
                IdentityMatch(
                    source="ops_clients",
                    source_id="client_1",
                    ruc="0992364866001",
                    legal_name="Nombre Antiguo",
                )
            ],
        )
        self.assertTrue(comparison.exact_ruc_match)
        self.assertEqual(comparison.recommended_action, "link_existing")
        self.assertEqual(comparison.conflicts[0].field, "legal_name")
        self.assertEqual(draft.legal_name, "Nombre Oficial S.A.")


if __name__ == "__main__":
    unittest.main()
