# RalphiIA QuoteOps

QuoteOps is the separate OpenAI Build Week repository for Ralphi IA.

## Current state

- H1 scaffold complete
- FastAPI skeleton in place
- Reuse map created from the existing Ralphi IA stack
- H2 structured intake analysis endpoint added
- Frontend cockpit added for intake, reuse, and traceability
- H3 tool planning endpoint added for approval and delivery routing
- P0 live RUC trust-anchor flow added with Intuito, RalphiIA/Contífico reconciliation, human approval, and staging idempotency
- Read-only operations cockpit connected to real IESS and Banco del Pacífico staging records

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python main.py
```

## Smoke tests

```bash
.venv/bin/python -m unittest discover -s tests -t . -v
```

## Endpoints

- `GET /`
- `GET /cockpit`
- `GET /health`
- `GET /api/meta`
- `GET /api/ui/bootstrap`
- `GET /api/operations/summary`
- `GET /api/reuse`
- `GET /api/reuse/verify`
- `POST /api/intake/preview`
- `POST /api/intake/analyze`
- `POST /api/plan`
- `GET /api/ruc/status`
- `POST /api/ruc/lookup`
- `POST /api/ruc/confirm`

## Live RUC trust anchor

Owner mode can verify an Ecuadorian RUC against the configured provider, compare the result with the existing RalphiIA identity kernel and Contífico mirror, prefill a customer draft, expose conflicts, and wait for explicit confirmation. Confirmed records are stored in the isolated `ralphiia_quoteops_staging` database by default, with unique RUC indexes and a source identity map.

Credentials are server-side only. Keep `RUC_API_USERNAME` and `RUC_API_PASSWORD` out of source, logs, screenshots, and public CI. Production writes remain disabled unless Rafael grants a separate explicit authorization.

## Operations cockpit

The cockpit exposes a sanitized, read-only projection of IESS vouchers, confirmed WhatsApp payments, Banco del Pacífico statements, reconciliation candidates, and continuity exceptions. Financial evidence under `data/` remains local and is excluded from Git; candidate approval and all production mutations remain blocked behind explicit human authorization.

## Next milestones

- H4: approval and PDF
- H5: delivery and timeline
- H6: sandbox and tests
- H7: README, demo, GitHub
