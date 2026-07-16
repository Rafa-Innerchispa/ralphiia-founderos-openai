import json
import subprocess
from pathlib import Path

import pytest

from scripts.build_evidence_report import assert_safe, build_manifest, redact, write_manifest


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Evidence Test")
    (tmp_path / "docs").mkdir()
    (tmp_path / "quoteops").mkdir()
    (tmp_path / "quoteops" / "service.py").write_text("pass\n")
    (tmp_path / "docs" / "PUBLIC_PROGRESS.json").write_text(json.dumps({"verification": {"tests_passed": 2, "tests_total": 2, "staging_status": "healthy", "commit": "abc1234"}}))
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "Build QuoteOps evidence")
    return tmp_path


def test_manifest_is_stable_and_valid_json(repo: Path, tmp_path: Path) -> None:
    first = build_manifest(repo)
    output = write_manifest(repo, tmp_path / "manifest.json")
    assert first == build_manifest(repo)
    assert json.loads(output.read_text()) == first


def test_commit_files_are_sorted_and_observable_data_is_labeled(repo: Path) -> None:
    manifest = build_manifest(repo)
    assert manifest["commits"][0]["files"] == sorted(manifest["commits"][0]["files"])
    assert manifest["commits"][0]["kind"] == "measured"
    assert manifest["staging_health"]["live_probe"]["kind"] == "pending"


def test_redaction_and_secret_rejection() -> None:
    assert "[REDACTED]" in redact("token=supersecret")
    assert "[REDACTED]" in redact(r"C:\private\file")
    with pytest.raises(ValueError):
        assert_safe("Authorization: Bearer abcdefghijk")


def test_manifest_contains_no_secret_patterns(repo: Path) -> None:
    manifest = build_manifest(repo)
    assert_safe(manifest)


def test_secret_in_commit_metadata_fails_closed(repo: Path) -> None:
    (repo / "quoteops" / "second.py").write_text("pass\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "token=supersecret")
    with pytest.raises(ValueError):
        build_manifest(repo)
