from quoteops.reuse_catalog import reuse_summary


def test_reuse_summary_has_reuse_and_new_sections():
    summary = reuse_summary()
    assert summary["ok"] is True
    assert summary["reuse_count"] >= 1
    assert summary["new_count"] >= 1
    assert "reuse_first" in summary["catalog"]
    assert "new_for_quoteops" in summary["catalog"]
