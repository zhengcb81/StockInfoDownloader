"""Enforce the production scan against the pre-change SID owner baseline."""

from pathlib import Path
import sys

from tests.native_process_fixture import native_run


ROOT = Path(__file__).resolve().parents[2]


def test_actual_sid_source_cannot_add_unreviewed_bypasses():
    result = native_run(
        [sys.executable, "-B", "-m", "tools.anti_trick_gate_spec",
         "scan", "--source", "src", "--source", "main.py",
         "--machine-entry", "src/company_wiki_adapter_cli.py",
         "--machine-entry", "src/feedback_owner.py",
         "--baseline", "tools/s6_source_baseline.json", "--strict"],
        cwd=ROOT, capture_output=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
