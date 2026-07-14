# QuoteOps Reuse Map

## Reuse First

### Core platform already available in Ralphi IA
- `raphiia_openai` FastAPI/MCP stack
- MongoDB `pcdoctor_swarm`
- `RalfIA MCP` tools and coordination channel
- Project lifecycle and service registry on `:2002`
- Existing coordination docs and AG-25 daemon

### Existing tools and flows to reuse
- `create_quote_draft`
- `update_quote_draft`
- `generate_quote_intro`
- `render_quote_document`
- `generate_quote_pdf`
- `send_quote_delivery`
- `get_quote_tracking`
- `list_quote_deliveries`
- `sync_quote_sources`
- `create_receivable_from_quote`

### Existing service capabilities to reuse
- Smart Quoter workflow and quote delivery flow
- WhatsApp / Evolution API integration
- PDF generation pipeline
- Mongo-backed quote and delivery stores
- Service registry and health/watchdog infrastructure
- Local-first runtime preferences for model and data processing

### Existing agent naming and structure to respect
- `AG-25_ralfia_coordination_orchestrator`
- `AG-30_WHATSAPP`
- `AG-31_SERVICE_RECOVERY`
- Project-specific agents should follow `AG-xx_name` only when truly needed

## What is new for QuoteOps

### New repository
- `/home/rlopez/projects/ralphiia-quoteops`

### New application layer
- `quoteops/` FastAPI package
- `QuoteIntake`, `MissingInformation`, `TechnicalRisk`, `ProposalOption`, `ToolDecision`, `QuoteReview`, `MissionState`
- H2 GPT-5.6 structured intake analysis

### New integration layer
- QuoteOps tool router
- Structured Outputs validators
- Adapter wrappers around existing Ralphi IA tools

### New docs to maintain
- `docs/BASELINE_PRE_HACKATHON.md`
- `docs/BUILD_WEEK_CHANGES.md`
- `docs/CODEX_SESSION.md`
- `docs/H1.md`
- `docs/H2.md` and later milestone docs as needed

## What not to duplicate
- Do not duplicate Smart Quoter internals if an adapter is enough
- Do not duplicate WhatsApp delivery logic if the existing delivery module can be called
- Do not duplicate PDF rendering if `render_quote_document` and `generate_quote_pdf` already work
- Do not create a second Mongo schema for the same quote lifecycle

## Decision for now

No new agent is required for H1. QuoteOps can start as a separate repository and use the existing agent and MCP ecosystem through adapters.
