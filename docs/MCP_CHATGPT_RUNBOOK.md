# ChatGPT + QuoteOps MCP Runbook

## Purpose

ChatGPT is the conversational reasoning surface. QuoteOps is the deterministic operations system. ChatGPT may understand long text, images, PDFs, product labels, site photos, and supplier price lists, then call typed MCP tools to persist only structured data.

The current Codex session uses GPT-5.6 Sol to build the product. The QuoteOps server must not claim that GPT-5.6 is its runtime when no authorized OpenAI API key exists.

## Staging status

- QuoteOps exposes a stateless JSON-RPC endpoint at `POST /mcp` on isolated staging.
- Staging authentication uses `QUOTEOPS_MCP_API_KEY` through `Authorization: Bearer` or `X-API-Key`; production mode refuses to expose MCP when the key is absent.
- The endpoint is verified locally but is not routed through the shared public MCP gateway.
- The shared RalphiIA MCP `:8102`, ngrok route, Smart Quoter `:2026`, and production services remain unchanged.

Public or shared-gateway activation requires a separate reviewed change with authentication, rate limiting, gateway routing, and rollback.

## Tool sequence

1. `quoteops_start_or_continue_mission`
2. `quoteops_record_extracted_evidence` for each image, PDF, or document
3. `quoteops_review_extracted_evidence` after Rafael reviews the extraction
4. `quoteops_add_supplier_offer` with the confirmed supplier reference and exact costs
5. `quoteops_review_catalog_draft` for each genuinely new product or service
6. `quoteops_update_decision_brief` with confirmed requirements and unresolved questions
7. `quoteops_upsert_configuration_alternative` for each evidence-backed option `A`, `B`, or `C`
8. `quoteops_review_configuration_alternative` after a human resolves gaps and compatibility
9. `quoteops_select_package` with an approved `A`, `B`, or `C`
10. `quoteops_update_quote` with human-entered selling prices
11. `quoteops_approve_quote` with an explicit approver
12. `quoteops_register_delivery` only after approval

Every mutation requires an idempotency key. Repeating the same key returns the original result.

## Shared channel contract

`POST /api/conversation/channel-events` accepts a normalized channel plus its native payload. A stable `event_id`, `update_id`, or `message_id` becomes a persisted idempotency key. If `mission_id` or `case_ref` is present, the event continues that case; otherwise the first valid message creates a mission and returns its ID. The WhatsApp and Telegram webhooks use the same bridge and signature boundary.

Natural-language channel messages update conversation context. Structured requirement and alternative edits use the typed tools above with `source_channel` set to the actual origin. This keeps web, ChatGPT, and messaging edits in one auditable mission without granting any channel arbitrary database or shell access.

## Configuration safeguards

- Alternative lines accept an exact supplier `offer_line_id` or an unambiguous SKU, quantity, role, compatibility state, rationale, and evidence IDs.
- Alternative inputs do not define `unit_cost`; extra cost fields are rejected by the contract.
- QuoteOps copies costs only from stored supplier offers and recomputes line totals.
- Marking compatibility `verified` requires confirmed evidence plus an approved staging or canonical catalog link.
- A human must approve the complete alternative before it can create editable quote lines.
- The selected assistant/model field is provenance supplied by the operator. It never changes the honest QuoteOps runtime label.

## Multimodal evidence

For every extracted source, ChatGPT records:

- source filename and media type;
- stored attachment ID and SHA-256 when QuoteOps has the original;
- extraction type;
- extracted text when useful;
- facts with normalized value, unit, page/region, and confidence;
- product candidates with brand, model, SKU, and confidence;
- supplier prices with reference, quantity, unit cost, currency, tax state, page/region, and confidence;
- warnings and review status.

If ChatGPT can inspect a file but the original has not been uploaded to QuoteOps, the record is saved as `source_unlinked` with `original_source_not_archived`. It remains searchable and reviewable, but the missing archive is never hidden.

## Commercial safeguards

- Extracted data does not create canonical catalog items.
- New products and services become staging `catalog_draft` records with `approval_required=true`.
- QuoteOps first performs a read-only exact SKU/name lookup. A match is linked instead of duplicated.
- Human approval creates only an isolated `approved_staging` item; canonical promotion remains a separate reviewed release.
- Supplier cost never becomes customer selling price automatically.
- Missing prices remain exactly zero.
- Human approval is mandatory before PDF generation.
- The customer PDF omits internal supplier cost.
- Private external delivery remains blocked while production writes are disabled.

## Shared MCP gap

The RalphiIA codebase already contains `upsert_inventory_offer` and `list_inventory_offers` in its inventory store and tool catalog, but they are not loaded by the live MCP server/profile inspected during this session. QuoteOps therefore keeps supplier offers in isolated staging until a separate MCP release is reviewed. Do not substitute a purchase order for a supplier offer and do not claim the live catalog supports a tool that is not loaded.
