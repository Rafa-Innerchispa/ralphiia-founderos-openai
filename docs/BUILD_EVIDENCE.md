# Build Evidence

Generate the publishable, deterministic evidence manifest from the repository root:

```bash
/home/rlopez/projects/ralphiia-quoteops/.venv/bin/python scripts/build_evidence_report.py
```

The generated `docs/evidence/manifest.json` inventories Git commits and changed files as measured evidence. It labels repository-derived status separately from pending live captures. It never contacts staging, reads environment variables, exports conversations, or collects usage/token metrics.

The generator rejects secret-like values, bearer tokens, credential assignments, emails, IPv4 addresses, Linux `/home/...` paths, Windows paths, Ecuadorian 10/13-digit identifiers, and 9–15 digit phone numbers. Its input is intentionally limited to Git metadata and the public progress projection. Do not add customer records, provider payloads, screenshots containing personal data, or raw session transcripts to the manifest.

For Devpost/OpenAI, export this manifest together with: a sanitized `git log --stat`, timestamped test output, a separately captured and sanitized staging `/health` and `/openapi.json`, sanitized screenshots, a short demo video, and approved Codex Session IDs as references only. Inspect each artifact before sharing. Do not claim GPT-5.6 as the application runtime: it is construction evidence through sessions, commits, documentation, and video. Do not infer usage or token metrics.

Run the focused checks before handoff:

```bash
/home/rlopez/projects/ralphiia-quoteops/.venv/bin/python -m unittest tests.test_build_evidence_report -v
/home/rlopez/projects/ralphiia-quoteops/.venv/bin/python -m unittest discover -v
git diff --check
```

The source revision is the newest reachable commit with a functional/non-evidence change. Evidence-only commits are ignored, so regenerating after this report is committed or cherry-picked does not create a self-reference loop.

Live staging health/OpenAPI, screenshots, video, and session approval are pending collection by the authorized operator; this offline tool deliberately does not make those requests.
