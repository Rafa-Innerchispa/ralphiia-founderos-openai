import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_evidence_report import assert_safe, build_manifest, redact, write_manifest


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


class BuildEvidenceReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "Evidence Test")
        (self.repo / "docs").mkdir()
        (self.repo / "quoteops").mkdir()
        (self.repo / "quoteops" / "service.py").write_text("pass\n", encoding="utf-8")
        (self.repo / "docs" / "PUBLIC_PROGRESS.json").write_text(
            json.dumps({"verification": {"tests_passed": 2, "tests_total": 2, "staging_status": "healthy", "commit": "abc1234"}}),
            encoding="utf-8",
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "Build QuoteOps evidence")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_manifest_is_stable_and_valid_json(self) -> None:
        first = build_manifest(self.repo)
        output = write_manifest(self.repo, self.repo / "manifest.json")
        self.assertEqual(first, build_manifest(self.repo))
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), first)

    def test_evidence_only_commit_does_not_change_manifest_source(self) -> None:
        before = build_manifest(self.repo)
        evidence = self.repo / "docs" / "evidence"
        evidence.mkdir()
        (evidence / "manifest.json").write_text("{}\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "Add evidence artifact")
        self.assertEqual(before, build_manifest(self.repo))

    def test_commit_files_are_sorted_and_observable_data_is_labeled(self) -> None:
        manifest = build_manifest(self.repo)
        self.assertEqual(manifest["commits"][0]["files"], sorted(manifest["commits"][0]["files"]))
        self.assertEqual(manifest["commits"][0]["kind"], "measured")
        self.assertEqual(manifest["staging_health"]["live_probe"]["kind"], "pending")

    def test_redaction_and_rejection_for_sensitive_classes(self) -> None:
        values = (
            ("credential assignment", "token=supersecret"),
            ("bearer token", "Authorization: Bearer abcdefghijk"),
            ("Windows path", r"C:\\private\\file"),
            ("email", "person@example.com"),
            ("IPv4", "192.168.1.4"),
            ("Linux home path", "/home/private/file"),
            ("Ecuadorian 10-digit identifier", "1234567890"),
            ("Ecuadorian 13-digit identifier", "1234567890123"),
            ("phone", "09876543210"),
        )
        for label, value in values:
            with self.subTest(label=label):
                self.assertIn("[REDACTED]", redact(value))
                with self.assertRaises(ValueError):
                    assert_safe(value)

    def test_hashes_dates_and_relative_paths_are_allowed(self) -> None:
        assert_safe("cca1258")
        assert_safe("a" * 40)
        assert_safe("2026-07-16")
        assert_safe("docs/evidence/manifest.json")

    def test_manifest_contains_no_sensitive_patterns(self) -> None:
        assert_safe(build_manifest(self.repo))

    def test_secret_in_commit_metadata_fails_closed(self) -> None:
        (self.repo / "quoteops" / "second.py").write_text("pass\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "token=supersecret")
        with self.assertRaises(ValueError):
            build_manifest(self.repo)
