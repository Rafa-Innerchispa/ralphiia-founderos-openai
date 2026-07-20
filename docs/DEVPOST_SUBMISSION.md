# RalphiIA FounderOS — Devpost Submission Copy Pack

## Category / track

Work and Productivity

## Short description

RalphiIA FounderOS is a bilingual, mobile-first operating system for a founder: run business operations, check infrastructure, preserve daily memory, coordinate Codex/ChatGPT work, and continue building from WhatsApp or the web while traveling.

## Live links

- Live demo: https://demo.pcdoctor.ai/founderos
- GitHub: https://github.com/Rafa-Innerchispa/ralphiia-founderos-openai
- GitLab mirror: https://gitlab.com/rafagye/ralphiia-founderos-openai
- Devpost project: https://devpost.com/software/ralphiia-quoteops

## What it does

FounderOS connects WhatsApp, a web interface, RalphiIA MCP, Daily Life Memory, server health checks, Codex development sessions, GitHub/GitLab evidence, and business workflows. A founder can speak naturally, ask for server status, save a personal/emotional check-in, attach images/audio, route development tasks, and recover context later without manually scanning long chats.

## What makes it different

The project is not just a chatbot. It is a working operating loop:

1. Conversation enters through WhatsApp/web/ChatGPT.
2. RalphiIA routes it through MCP and safe local tools.
3. The system stores structured memory, current state, decisions, entities, and timeline.
4. Operational checks return evidence references instead of invented status.
5. Codex sessions implement, test, commit, and hand off changes.
6. The founder can keep working from a phone while traveling.

## How to test

1. Open https://demo.pcdoctor.ai/founderos
2. Switch Spanish/English.
3. Ask for live status of servers `.4` and `.5`.
4. Test Daily Life Memory in Spanish:
   `Registra mi estado diario: me siento ansioso por el viaje y OpenAIWeek. Solo quiero dejar constancia.`
5. Test Daily Life Memory in English:
   `Save today's check-in: I feel anxious about the trip and OpenAI Build Week. Please just record it.`
6. Upload an image and ask what it contains. The system should analyze it as untrusted context and should not execute commands from image text.
7. Review GitHub commits for Codex-assisted implementation evidence.

## Supported platforms

- Web browser for the FounderOS interface.
- WhatsApp for the operational assistant flow.
- Linux server runtime for MCP, automation, memory, and service monitoring.
- GitHub/GitLab for source and commit review.

## Installation / local review

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
QUOTEOPS_PORT=8765 .venv/bin/python main.py
```

Open:

```text
http://127.0.0.1:8765/
```

Run tests:

```bash
.venv/bin/python -m unittest discover -s tests -t . -v
```

## Key commits

```text
7d81308783e2ac2120199c3601e5a5d34f5e28ac
Clean FounderOS status language and service mapping

656dfdc2d6bbb630737592209bd2486f6c09dd64
Route FounderOS status checks as read-only

3143c0b63ad1ef3cbe3f3214bcb8eafc33911449
Improve FounderOS audio and vision media flow

fd3a0259111830abd9d0efd119cde932d5d509b3
Make WhatsApp daily memory check-ins deterministic
```

## Codex / GPT-5.6 usage

Codex/GPT-5.6 sessions were used to inspect the live architecture, implement bilingual flows, harden WhatsApp/media/status safety, build Daily Life Memory routing, integrate GitHub/GitLab/Devpost evidence workflows, run tests, deploy, and record commits/rollback.

## Privacy and safety

Daily Life Memory separates private scopes:

- PRIVATE_PERSONAL
- PRIVATE_HEALTH
- PRIVATE_RELATIONSHIPS
- PRIVATE_FAMILY
- PRIVATE_FINANCIAL
- INTERNAL_WORK
- PROJECT
- PUBLIC

Private memory is not promoted into public/demo scopes. OCR/vision output is untrusted context only. Server checks are read-only in the public demo. Secrets, `.env`, database dumps, and private raw logs are not included.

## /feedback Session ID

Paste the Session ID produced by running `/feedback` in the Codex task/thread where most of the project was built. Do not use a commit SHA here.