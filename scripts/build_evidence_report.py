#!/usr/bin/env python3
"""Create a deterministic, publishable Build Week evidence manifest.

The report intentionally uses repository metadata and approved public/change-log
claims only.  It never calls staging, reads environment variables, or exports
session transcripts.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]+"),
    re.compile(r"\b(?:sk|rk|ghp)_[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b"),
    re.compile(r"(?<![\w.-])/home/[^\s\"'<>]+"),
    re.compile(r"(?<!\d)\d{10}(?!\d)"),
    re.compile(r"(?<!\d)\d{13}(?!\d)"),
    re.compile(r"(?<!\d)\d{9,15}(?!\d)"),
)
EVIDENCE_PATHS = (
    "scripts/build_evidence_report.py",
    "tests/test_build_evidence_report.py",
    "docs/BUILD_EVIDENCE.md",
    "docs/CODEX_BUILD_LOG.md",
    "docs/evidence/",
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _commit_files(repo: Path, revision: str) -> list[str]:
    return _git(repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", revision).splitlines()


def _is_evidence_path(path: str) -> bool:
    return path in EVIDENCE_PATHS[:-1] or path.startswith(EVIDENCE_PATHS[-1])


def source_revision(repo: Path) -> str:
    """Find the newest commit with a non-evidence change reachable from HEAD."""
    for revision in _git(repo, "rev-list", "HEAD").splitlines():
        files = _commit_files(repo, revision)
        if any(not _is_evidence_path(path) for path in files):
            return revision
    raise ValueError("no functional/non-evidence commit found")


def assert_safe(value: Any) -> None:
    """Reject data that must never be published in the evidence bundle."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            raise ValueError("sensitive value detected; refusing to write manifest")


def redact(text: str) -> str:
    """Replace sensitive-looking material in a human-facing, bounded string."""
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def build_week_commits(repo: Path, source_ref: str) -> list[dict[str, Any]]:
    """Return reachable commits that have Build Week documentation or QuoteOps changes."""
    rows = _git(repo, "log", "--reverse", "--format=%H%x1f%h%x1f%ad%x1f%s", "--date=short", source_ref).splitlines()
    commits: list[dict[str, Any]] = []
    for row in rows:
        full, short, date, subject = row.split("\x1f", 3)
        files = _commit_files(repo, full)
        # The isolated Build Week work began with its public documentation;
        # later QuoteOps commits are included when their file list is relevant.
        if not any(name.startswith(("quoteops/", "tests/", "docs/", "main.py")) for name in files):
            continue
        # Git subjects are external input too: fail closed rather than quietly
        # publishing a commit message that might have contained a secret.
        assert_safe(subject)
        assert_safe(files)
        commits.append({
            "kind": "measured",
            "commit": short,
            "date": date,
            "subject": subject,
            "files": sorted(files),
        })
    return commits


def public_progress(repo: Path) -> dict[str, Any]:
    path = repo / "docs/PUBLIC_PROGRESS.json"
    if not path.exists():
        return {"kind": "pending", "reason": "public progress projection unavailable"}
    data = json.loads(path.read_text(encoding="utf-8"))
    verification = data.get("verification", {})
    return {
        "kind": "derived",
        "source": "docs/PUBLIC_PROGRESS.json",
        "tests_passed": verification.get("tests_passed"),
        "tests_total": verification.get("tests_total"),
        "staging_status": verification.get("staging_status"),
        "source_commit": verification.get("commit"),
    }


def build_manifest(repo: Path) -> dict[str, Any]:
    source_ref = source_revision(repo)
    commits = build_week_commits(repo, source_ref)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_from": {
            "kind": "measured",
            "functional_source_ref": _git(repo, "rev-parse", "--short", source_ref),
            "policy": "newest reachable commit with a non-evidence file change",
        },
        "scope": {
            "kind": "derived",
            "name": "QuoteOps Build Week",
            "environment": "staging evidence only",
            "production_writes": "not performed",
            "smart_quoter": "read-only; not restarted",
        },
        "commits": commits,
        "observable_tests": public_progress(repo),
        "staging_health": {
            "kind": "derived",
            "value": public_progress(repo).get("staging_status"),
            "source": "docs/PUBLIC_PROGRESS.json verification.staging_status",
            "live_probe": {"kind": "pending", "reason": "not performed by this offline generator"},
        },
        "openapi": {
            "kind": "derived",
            "version": "0.8.0",
            "source": "docs/CODEX_SESSION.md (verification note)",
            "live_export": {"kind": "pending", "reason": "capture a sanitized staging /openapi.json separately"},
        },
        "runtime": {
            "kind": "derived",
            "application_label": "deterministic_rules / Codex-built / MCP runtime",
            "gpt_5_6": "build evidence only; not asserted as application runtime",
            "usage_or_token_metrics": {"kind": "pending", "reason": "not collected or inferred"},
        },
        "codex_session_references": {
            "kind": "derived",
            "source": "docs/CODEX_SESSION.md",
            "policy": "references only; no transcript, participant, client, or provider payload exported",
            "gpt_5_6_evidence": "record through approved session references, commits, documentation, and demo video",
        },
        "export_checklist": {
            "kind": "pending",
            "items": [
                "sanitized commit log and this manifest",
                "test command output with timestamps",
                "sanitized staging health and OpenAPI captures",
                "sanitized screenshots and demo video",
                "approved Codex Session IDs (references only)",
            ],
        },
    }
    assert_safe(manifest)
    return manifest


def write_manifest(repo: Path, output: Path) -> Path:
    manifest = build_manifest(repo)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/manifest.json"))
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    try:
        write_manifest(repo, output)
    except (ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"build evidence report failed: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
