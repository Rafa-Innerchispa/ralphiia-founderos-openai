from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any


class PublicProgressFeed:
    """Build a deliberately small public projection of QuoteOps progress."""

    _PRIVATE_PATTERNS = (
        re.compile(r"\b[0-9]{10}(?:[0-9]{3})?\b"),
        re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]+)?"),
        re.compile(r"(?:/home/|/Users/|[A-Za-z]:\\)[^\s,;]+"),
        re.compile(
            r"(?i)\b(?:bearer|token|password|secret|api[_-]?key)\b\s*[:=]?\s*[^\s,;]+"
        ),
    )
    _TRACE_STATUSES = {"ready", "ok", "warning", "error", "not_configured"}
    _SUMMARY_STATUSES = {"active", "paused", "completed", "blocked"}
    _STAGING_STATUSES = {"healthy", "degraded", "offline", "not_verified"}
    _DECISION_STATUSES = {"accepted", "reviewing", "superseded"}
    _EVENT_STATUSES = {"completed", "in_progress", "blocked"}
    _EVENT_TYPES = {"milestone", "commit", "verification", "decision", "release"}
    _EVIDENCE_KEYS = {"commit", "tests", "verification"}

    def __init__(self, manifest_path: Path, *, trace_store=None, repo_root: Path | None = None) -> None:
        self.manifest_path = Path(manifest_path)
        self.trace_store = trace_store
        self.repo_root = Path(repo_root) if repo_root else self.manifest_path.parent.parent

    def snapshot(self, language: str = "es") -> dict[str, Any]:
        language = "en" if language == "en" else "es"
        source = self._load_manifest()
        summary_source = source.get("summary") if isinstance(source.get("summary"), dict) else {}
        verification_source = (
            source.get("verification") if isinstance(source.get("verification"), dict) else {}
        )
        summary = {
            "title": self._localized(summary_source, "title", language, "QuoteOps"),
            "status": self._choice(
                summary_source.get("status"), self._SUMMARY_STATUSES, "active"
            ),
            "phase": self._localized(summary_source, "phase", language, "H2"),
            "progress_percent": self._bounded_int(
                summary_source.get("progress_percent"), 0, 100, 0
            ),
        }
        verification = {
            "tests_passed": self._bounded_int(
                verification_source.get("tests_passed"), 0, 1_000_000, 0
            ),
            "tests_total": self._bounded_int(
                verification_source.get("tests_total"), 0, 1_000_000, 0
            ),
            "staging_status": self._choice(
                verification_source.get("staging_status"),
                self._STAGING_STATUSES,
                "not_verified",
            ),
            "commit": self._current_commit()
            or self._safe_commit(verification_source.get("commit")),
        }
        decisions = self._localized_records(
            source.get("decisions"), language, record_kind="decision"
        )[:30]
        events = self._localized_records(
            source.get("events"), language, record_kind="event"
        )[:50]
        integrations = self._public_integrations()
        refresh_seconds = self._bounded_int(source.get("refresh_seconds"), 10, 300, 15)
        revision_source = {
            "project": "ralphiia-quoteops",
            "language": language,
            "summary": summary,
            "verification": verification,
            "decisions": decisions,
            "events": events,
            "integrations": integrations,
        }
        revision = sha256(
            json.dumps(revision_source, ensure_ascii=True, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        return {
            "ok": True,
            "project": "ralphiia-quoteops",
            "language": language,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "revision": revision,
            "refresh_seconds": refresh_seconds,
            "summary": summary,
            "verification": verification,
            "decisions": decisions,
            "events": events,
            "integrations": integrations,
        }

    def _load_manifest(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _localized_records(
        self, records: Any, language: str, *, record_kind: str
    ) -> list[dict[str, Any]]:
        if not isinstance(records, list):
            return []
        public: list[dict[str, Any]] = []
        for raw in records:
            if not isinstance(raw, dict):
                continue
            item = {
                "id": self._safe_id(raw.get("id")),
                "title": self._localized(raw, "title", language, "Update"),
                "summary": self._localized(raw, "summary", language, ""),
            }
            if not item["id"]:
                continue
            if record_kind == "decision":
                item.update(
                    {
                        "status": self._choice(
                            raw.get("status"), self._DECISION_STATUSES, "reviewing"
                        ),
                        "decided_at": self._safe_timestamp(raw.get("decided_at")),
                    }
                )
            else:
                evidence = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
                item.update(
                    {
                        "type": self._choice(raw.get("type"), self._EVENT_TYPES, "milestone"),
                        "status": self._choice(
                            raw.get("status"), self._EVENT_STATUSES, "in_progress"
                        ),
                        "occurred_at": self._safe_timestamp(raw.get("occurred_at")),
                        "evidence": {
                            str(key): self._safe_text(value, 120)
                            for key, value in evidence.items()
                            if key in self._EVIDENCE_KEYS
                        },
                    }
                )
            public.append(item)
        time_key = "decided_at" if record_kind == "decision" else "occurred_at"
        return sorted(public, key=lambda item: item[time_key], reverse=True)

    def _public_integrations(self) -> list[dict[str, str]]:
        if self.trace_store is None:
            return []
        public = []
        for trace in self.trace_store.snapshot():
            name = self._safe_text(trace.get("integration"), 80)
            if not name:
                continue
            public.append(
                {
                    "name": name,
                    "status": self._choice(
                        trace.get("status"), self._TRACE_STATUSES, "warning"
                    ),
                }
            )
        return public

    def _current_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=12", "HEAD"],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=1,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return self._safe_commit(result.stdout.strip())

    def _localized(
        self, source: dict[str, Any], field: str, language: str, fallback: str
    ) -> str:
        value = source.get(f"{field}_{language}")
        if value is None or value == "":
            value = source.get(f"{field}_es", source.get(field, fallback))
        return self._safe_text(value, 800 if field == "summary" else 200)

    def _safe_text(self, value: Any, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        for pattern in self._PRIVATE_PATTERNS:
            text = pattern.sub("[redacted]", text)
        return text[:limit]

    @staticmethod
    def _safe_id(value: Any) -> str:
        clean = re.sub(r"[^a-z0-9_-]", "-", str(value or "").strip().lower())
        return clean[:100].strip("-")

    @staticmethod
    def _safe_timestamp(value: Any) -> str:
        text = str(value or "").strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime(1970, 1, 1, tzinfo=timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _safe_commit(value: Any) -> str:
        text = str(value or "").strip().lower()
        return text if re.fullmatch(r"[a-f0-9]{7,40}", text) else "unknown"

    @staticmethod
    def _bounded_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return fallback
        return min(max(number, minimum), maximum)

    @staticmethod
    def _choice(value: Any, allowed: set[str], fallback: str) -> str:
        text = str(value or "")
        return text if text in allowed else fallback
