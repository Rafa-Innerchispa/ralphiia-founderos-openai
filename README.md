# RalphiIA QuoteOps

QuoteOps turns a natural-language project conversation into a verified, editable, human-approved quote. It is a separate OpenAI Build Week repository and runs on the isolated RalphiIA staging host.

## Product flow

1. Start with a long project description and optional files.
2. Continue the conversation while QuoteOps builds a progressive case file.
3. Validate a 10-digit Ecuadorian cédula locally or a 13-digit RUC through authorized Intuito access.
4. Reconcile the identity read-only against RalphiIA and Contífico to avoid duplicates.
5. Review site, confirmed scope, assumptions, risks, questions, and technical options.
6. Let ChatGPT extract structured, reviewable evidence from images, PDFs, product labels, and supplier price lists through MCP.
7. Compare three packages: selective rehabilitation, hybrid modernization, and full renewal.
8. Prepare an editable quote whose selling prices start at zero while verified supplier costs remain internal.
9. Enter real commercial values, obtain human approval, generate a real PDF, and register delivery.

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
- A staging MCP JSON-RPC surface with typed mission, multimodal evidence, supplier-cost, package, pricing, approval, and delivery tools.
- Read-only exact SKU/name reconciliation before any staging catalog draft is created, plus explicit human approval for genuinely new items.

The side panel shows source, call, status, latency, observation time, and a sanitized result for each integration. Credentials and raw sensitive provider responses are not exposed.

## Public build progress

`GET /api/public/progress?language=es|en` exposes a small, read-only feed for the separately owned Astro website. It contains curated milestones, decisions, test evidence, the current commit, and integration name/status pairs. It never exposes mission text, customer identity, attachments, provider payloads, internal paths, IP addresses, credentials, latency, or trace results.

The response includes a stable `revision` plus `refresh_seconds=15`, allowing a static site to poll for changes without rebuilding. Astro ownership and deployment remain outside this repository.

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
- `GET /api/public/progress?language=es|en`
- `POST /api/conversation/messages`
- `GET /api/conversation/missions/{mission_id}`
- `POST /api/conversation/missions/{mission_id}/attachments`
- `POST /api/conversation/missions/{mission_id}/evidence/extractions`
- `POST /api/conversation/missions/{mission_id}/evidence/{evidence_id}/review`
- `POST /api/conversation/missions/{mission_id}/supplier-offers`
- `POST /api/conversation/missions/{mission_id}/catalog-drafts/{catalog_draft_id}/review`
- `POST /api/conversation/missions/{mission_id}/packages/select`
- `PUT /api/conversation/missions/{mission_id}/quote`
- `POST /api/conversation/missions/{mission_id}/approve`
- `POST /api/conversation/missions/{mission_id}/deliver`
- `POST /api/customer/lookup`
- `POST /api/ruc/lookup`
- `POST /api/ruc/confirm`
- `GET /api/mcp/tools`
- `POST /api/mcp/call`
- `POST /mcp`

The QuoteOps MCP surface is staged but is not routed through the shared production MCP gateway. See `docs/MCP_CHATGPT_RUNBOOK.md` for the activation boundary and the exact ChatGPT flow.

Legacy intake, channel, operations, Smart Quoter, IESS, approval, PDF, and delivery endpoints remain available for existing integrations.

## Codex acceleration

Codex with GPT-5.6 was used to inspect the live staging architecture, audit the legacy Smart Quoter boundary, design typed conversation contracts, implement the bilingual experience, add deterministic mission logic, instrument integration traces, write tests, and verify staging end to end. The work is tracked in `docs/CODEX_SESSION.md` and `docs/BUILD_WEEK_CHANGES.md`.
