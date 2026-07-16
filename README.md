# RalphiIA QuoteOps

QuoteOps turns a natural-language project conversation into a verified, editable, human-approved quote. It is a separate OpenAI Build Week repository and runs on the isolated RalphiIA staging host.

## Product flow

1. Start with a long project description and optional files.
2. Continue the conversation while QuoteOps builds a progressive case file.
3. Validate a 10-digit Ecuadorian cédula locally or a 13-digit RUC through authorized Intuito access.
4. Reconcile the identity read-only against RalphiIA and Contífico to avoid duplicates.
5. Review site, confirmed scope, assumptions, risks, questions, and technical options.
6. Prepare an editable quote whose prices start at zero.
7. Enter real commercial values, obtain human approval, generate a real PDF, and register delivery.

The first supported real case is FEMAR's access-control replacement or rehabilitation project. The interface works in Spanish and English on mobile and desktop, and its translation catalog can be extended with additional locales.

## Runtime truth

The product does not claim that GPT-5.6 is running when no API key is configured. In that state the UI shows `Codex-built / MCP runtime`, and project analysis follows deterministic rules plus the existing RalphiIA services. If an authorized `OPENAI_API_KEY` and `QUOTEOPS_ENABLE_OPENAI=1` are supplied, the optional structured-analysis adapter can report its configured API model explicitly.

GPT-5.6 evidence for Build Week is captured by the Codex development sessions, commit history, this README, and the demo video. The application remains useful without a paid model runtime.

## Real integrations

- MCP availability through the RalphiIA endpoint.
- Intuito Azure token and RUC lookup adapters.
- RalphiIA party/client identity readers and Contífico mirror.
- Smart Quoter `:2026` diagnosis/refinement through a read-only adapter.
- MongoDB staging mission, identity, approval, and delivery records.
- Local PDF artifact generation after human approval.

The side panel shows source, call, status, latency, observation time, and a sanitized result for each integration. Credentials and raw sensitive provider responses are not exposed.

## Safety boundary

- `QUOTEOPS_ALLOW_PRODUCTION_WRITES=0` by default.
- Private authorized data remains in isolated staging collections.
- Judges use an isolated/test account and delivery registration does not trigger arbitrary external sends.
- Smart Quoter is read-only from QuoteOps.
- Files are stored under the QuoteOps artifact root with sanitized names, a 25 MB limit, and SHA-256 evidence.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run staging

```bash
QUOTEOPS_PORT=8765 .venv/bin/python main.py
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -t . -v
```

## Main endpoints

- `GET /`
- `GET /health`
- `GET /api/ui/bootstrap`
- `GET /api/integrations/trace`
- `POST /api/conversation/messages`
- `GET /api/conversation/missions/{mission_id}`
- `POST /api/conversation/missions/{mission_id}/attachments`
- `PUT /api/conversation/missions/{mission_id}/quote`
- `POST /api/conversation/missions/{mission_id}/approve`
- `POST /api/conversation/missions/{mission_id}/deliver`
- `POST /api/customer/lookup`
- `POST /api/ruc/lookup`
- `POST /api/ruc/confirm`

Legacy intake, channel, operations, Smart Quoter, IESS, approval, PDF, and delivery endpoints remain available for existing integrations.

## Codex acceleration

Codex with GPT-5.6 was used to inspect the live staging architecture, audit the legacy Smart Quoter boundary, design typed conversation contracts, implement the bilingual experience, add deterministic mission logic, instrument integration traces, write tests, and verify staging end to end. The work is tracked in `docs/CODEX_SESSION.md` and `docs/BUILD_WEEK_CHANGES.md`.
