"""Session-wide isolation of the owner feedback state root.

The ordinary CLI (``main.py``) and the adapter CLI publish
``feedback-observation/1`` observations, sanitized details, ready markers and
run/delivery receipts to the owner state root whenever neither
``RESEARCH_FEEDBACK_OUT`` nor ``RESEARCH_FEEDBACK_DIR`` selects another
target.  That default directory is the real public inbox ROOT consumes, so an
unmapped test run would publish synthetic observations as if they were real
(F4-SID-START-INPUT: the adapter regression suites were found doing exactly
that).

Every test therefore gets its own state root under ``tmp_path``, and inherits
no feedback target from the shell that started pytest.  Tests that need an
explicit OUT, DIR or a differently mapped root keep setting their own values;
subprocess tests that build a whitelist environment keep mapping their own.
"""

import pytest

_INHERITED_TARGETS = (
    "RESEARCH_FEEDBACK_OUT",
    "RESEARCH_FEEDBACK_RUN_ID",
    "RESEARCH_FEEDBACK_ATTEMPT_ID",
    "RESEARCH_FEEDBACK_DIR",
)


@pytest.fixture(autouse=True)
def _isolated_feedback_state_root(tmp_path, monkeypatch):
    for name in _INHERITED_TARGETS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RESEARCH_FEEDBACK_STATE_ROOT", str(tmp_path / "feedback-state"))
