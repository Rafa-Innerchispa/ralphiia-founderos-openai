# RalphiIA QuoteOps

QuoteOps is the separate OpenAI Build Week repository for Ralphi IA.

## Current state

- H1 scaffold complete
- FastAPI skeleton in place
- Reuse map created from the existing Ralphi IA stack
- H2 structured intake analysis endpoint added
- Frontend cockpit added for intake, reuse, and traceability

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
- `GET /api/reuse`
- `GET /api/reuse/verify`
- `POST /api/intake/preview`
- `POST /api/intake/analyze`

## Next milestones

- H3: tool adapters
- H4: approval and PDF
- H5: delivery and timeline
- H6: sandbox and tests
- H7: README, demo, GitHub
