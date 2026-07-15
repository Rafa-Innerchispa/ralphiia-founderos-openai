# QuoteOps Delivery Addendum

## Sandbox

Run `.venv/bin/python main.py`, open `/cockpit`, analyze an intake, verify a test RUC, approve in sandbox mode, open the PDF, and simulate delivery. Production writes remain disabled by `QUOTEOPS_ALLOW_PRODUCTION_WRITES=0`.

## Smart Quoter

The legacy service on port 2026 is connected through a read-only adapter. QuoteOps shows its source and blocks legacy writes until the QuoteOps approval gate is satisfied.

## Evidence

See `docs/E2E_STATUS.md`, `docs/SMART_QUOTER_INTEGRATION.md`, and `docs/DEMO_SCRIPT.md` for the reproducible scope and limitations.
