"""Regenerate the F4-SID-FAILURES cold-read evidence samples via the real CLI.

Runs one failing and one successful ordinary launch in isolated temp roots
(synthetic company codes, offline audit hook, mapped owner state root) and
copies the produced observations, details, ready markers and run receipts
into this evidence directory with the ``f4-sid-`` prefix.

Run from the repo root:

    C:/Miniconda/python.exe docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-samples-generate.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tests" / "unit"))
import test_f4_ordinary_failures as T  # noqa: E402  (sanctioned doubles + helpers)

tmp = Path(tempfile.mkdtemp(prefix="f4ev-"))
work = T._work(tmp)
config = T._config(work)
state = work / "state"

# The failing run: download engine raises PermissionError (audit line 13).
proc = T._run(
    [*T.PYTHON, "-c", T.SINGLE_DRIVER, str(T.MAIN_PY), "900001", str(config)],
    T._env(work, state_root=state), work,
)
print("failing run exit:", T._receipt(proc)["exit_code"])

# The control: same isolated root, sibling attempt with explicit host ids.
ok = T._run(
    [*T.PYTHON, "-c", T.SINGLE_OK_DRIVER, str(T.MAIN_PY), "900002", str(config)],
    T._env(work, state_root=state, RESEARCH_FEEDBACK_RUN_ID="sid-sample",
           RESEARCH_FEEDBACK_ATTEMPT_ID="try-sample"), work,
)
print("success run exit:", T._receipt(ok)["exit_code"])

dest = Path(__file__).resolve().parent
copied = 0
for src in sorted((state / "observations").glob("*")) + sorted((state / "runs").glob("*.json")):
    if src.is_file():
        shutil.copy2(src, dest / f"f4-sid-{src.name}")
        copied += 1
print("copied:", copied, "files into", dest)
shutil.rmtree(tmp, ignore_errors=True)
