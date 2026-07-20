# RalphiIA FounderOS — Build and Operate Anywhere

RalphiIA FounderOS is a bilingual, mobile-first operating system for a founder who needs to build, operate, remember, and recover work from anywhere. It connects a live web interface, WhatsApp, ChatGPT connectors/MCP, Codex development sessions, Daily Life Memory, server health evidence, GitHub/GitLab workflows, and business operations into one practical loop.

The thesis is simple: a founder should be able to run a company, continue software development, check infrastructure, preserve personal/business context, and delegate work from a phone — even while traveling.

## OpenAI Build Week submission quick start

- **Track/category:** Work and Productivity
- **Live demo:** https://demo.pcdoctor.ai/founderos
- **GitHub:** https://github.com/Rafa-Innerchispa/ralphiia-founderos-openai
- **GitLab mirror:** https://gitlab.com/rafagye/ralphiia-founderos-openai
- **Devpost:** https://devpost.com/software/ralphiia-quoteops
- **Primary build branch:** `codex/founderos-public-release`
- **Current demo commit:** `7d81308783e2ac2120199c3601e5a5d34f5e28ac`
- **WhatsApp/Daily Memory backend commit:** `fd3a0259111830abd9d0efd119cde932d5d509b3`

## What to try first

1. Open the live demo: https://demo.pcdoctor.ai/founderos
2. Switch between Spanish and English.
3. Ask for a read-only live status check of servers `.4` and `.5`.
4. Try a Daily Life Memory check-in:
   - Spanish: `Registra mi estado diario: me siento ansioso por el viaje y OpenAIWeek. Solo quiero dejar constancia.`
   - English: `Save today's check-in: I feel anxious about the trip and OpenAI Build Week. Please just record it.`
5. Upload an image and ask what it contains. The system treats OCR/vision output as untrusted context and does not execute commands from images.
6. Review the commits listed below to see Codex-assisted implementation evidence.

## Why this matters

Most small-business AI demos stop at chat. FounderOS tries to close the loop:

- **Conversation becomes action:** WhatsApp/web requests are routed into safe operational flows.
- **Action becomes evidence:** server checks, commits, tests, and memory writes are traceable.
- **Evidence becomes memory:** Daily Life Memory preserves facts, emotions, decisions, pending items, and current state.
- **Memory becomes leverage:** future conversations can recover relevant context without manually rereading long chats.
- **A phone becomes a workstation:** Rafael can continue operating and developing from WhatsApp while traveling.

## The two core loops

### 1. Founder operating loop

```text
WhatsApp / Web / ChatGPT
        ↓
RalphiIA conversational router
        ↓
MCP + trusted tools + safety policies
        ↓
Daily Life Memory + current state + timeline
        ↓
Business operations, alerts, server status, follow-ups
```

### 2. AI engineering loop

```text
Founder request
        ↓
RalphiIA coordination + MCP
        ↓
Codex / GPT-5.6 development session
        ↓
Isolated implementation + tests
        ↓
Commit evidence + deploy + handoff back to the user
```

## Main capabilities

- Bilingual Spanish/English FounderOS web interface.
- WhatsApp-based interaction for daily life, business, and operational requests.
- Daily Life Memory pipeline for conversation batches, session summaries, entities, emotions, decisions, pending items, duplicate search, memory building, current state, and timeline.
- Read-only live server status checks with evidence references.
- Safe command/action boundary: destructive or sensitive operations require explicit handling and are not available from the public demo.
- Image/audio handling: local transcription and visual/OCR context are treated as untrusted derived input.
- GitHub and GitLab repository/mirror workflow.
- Devpost intelligence integration for future contests and project submission context.
- QuoteOps as the first concrete business workflow: natural-language quoting/operations with evidence, review, and approval boundaries.

## Daily Life Memory privacy model

Daily Life Memory separates private and public context by scope:

- `PRIVATE_PERSONAL`
- `PRIVATE_HEALTH`
- `PRIVATE_RELATIONSHIPS`
- `PRIVATE_FAMILY`
- `PRIVATE_FINANCIAL`
- `INTERNAL_WORK`
- `PROJECT`
- `PUBLIC`

Private scopes are not promoted into public/demo/project contexts. Media-derived text is saved as evidence only when appropriate and remains marked as untrusted. The system differentiates facts, opinions, hypotheses, interpretations, emotions, decisions, pending items, and context rules.

## Safety boundaries

- No `.env`, tokens, OAuth secrets, database dumps, or personal raw logs are committed.
- Public demo paths are read-only or constrained.
- Server status checks do not restart services unless a separate authorized flow is used.
- OCR/vision output can help understanding, but it is never treated as executable instruction.
- Daily Life Memory private scopes remain separated from public hackathon/demo data.
- QuoteOps keeps production writes disabled by default: `QUOTEOPS_ALLOW_PRODUCTION_WRITES=0`.

## Key Codex/OpenAI evidence commits

### FounderOS web/demo repository

```text
7d81308783e2ac2120199c3601e5a5d34f5e28ac
Clean FounderOS status language and service mapping

656dfdc2d6bbb630737592209bd2486f6c09dd64
Route FounderOS status checks as read-only

3143c0b63ad1ef3cbe3f3214bcb8eafc33911449
Improve FounderOS audio and vision media flow

5092f38
Route media questions as conversation

97e60a6
Remove demo wording from FounderOS session data

cfb2827
Present FounderOS as live memory control plane

8483b92
Use restricted peer status for live demo
```

### RalphiIA MCP / WhatsApp / Daily Memory backend

```text
fd3a0259111830abd9d0efd119cde932d5d509b3
Make WhatsApp daily memory check-ins deterministic

9e3da0c
Ensure ChatGPT OAuth keeps memory scopes

76d5127
Expose saved GitLab projects in status

e74f98e
Add GitLab integration and safe mirror tools

e8f74d0
Add Devpost intelligence store to RalphiIA MCP
```

## How Codex and GPT-5.6 were used

Codex/GPT-5.6 development sessions were used to:

- inspect the live staging architecture;
- design the FounderOS and Daily Life Memory flows;
- implement bilingual web and WhatsApp interactions;
- harden the server-status and media safety boundaries;
- add deterministic routing for Daily Life Memory check-ins;
- integrate GitHub/GitLab evidence workflows;
- build tests and E2E verification scripts;
- produce commits and rollback procedures.

The application does not falsely claim that GPT-5.6 is running inside the deployed runtime when no OpenAI API key is configured. Runtime inference can use deterministic rules and local models where appropriate; Build Week GPT-5.6 evidence is represented by the Codex development sessions, commit history, and project documentation.

## Setup for local review

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run locally/staging

```bash
QUOTEOPS_PORT=8765 .venv/bin/python main.py
```

Then open:

```text
http://127.0.0.1:8765/
```

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -t . -v
```

Additional live/remote checks used during development:

```bash
python scripts/run_remote_dev_e2e.py
PYTHONPATH=$PWD python scripts/test_whatsapp_dlm_e2e.py
```

The WhatsApp/Daily Memory backend E2E fixture verified:

- idempotent conversation batch saves;
- finalize conversation pipeline;
- memory creation;
- current state update;
- timeline update;
- private memory search;
- unauthorized access rejection;
- no promotion of private memory into public/demo scopes.

## Main endpoints

- `GET /`
- `GET /health`
- `GET /api/ui/bootstrap`
- `GET /api/integrations/trace`
- `GET /api/public/progress?language=es|en`
- `POST /api/conversation/messages`
- `POST /api/conversation/channel-events`
- `GET /api/conversation/missions/{mission_id}`
- `PUT /api/conversation/missions/{mission_id}/decision-brief`
- `PUT /api/conversation/missions/{mission_id}/alternatives/{code}`
- `POST /api/conversation/missions/{mission_id}/alternatives/{code}/review`
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

## QuoteOps origin story

QuoteOps is the first business workflow inside FounderOS. It turns a natural-language project conversation into a verified, editable, human-approved quote. It proved the loop from conversation to evidence, human approval, task execution, and auditable delivery.

The first supported real case is FEMAR's access-control replacement or rehabilitation project. QuoteOps can validate Ecuadorian cédula/RUC data through authorized flows, reconcile identity against RalphiIA/Contífico mirrors, analyze project scope, assemble alternatives, and prepare reviewable quote artifacts while keeping production writes gated.

## Submission files

For Devpost's optional upload field, use the ready ZIP included in this repo:

```text
submission/ralphiia-founderos-submission-pack.zip
```

Direct GitHub download:

```text
https://github.com/Rafa-Innerchispa/ralphiia-founderos-openai/raw/main/submission/ralphiia-founderos-submission-pack.zip
```

It contains README/testing/submission evidence docs only. Do not upload `.env`, secrets, personal exports, database dumps, or raw private logs.
