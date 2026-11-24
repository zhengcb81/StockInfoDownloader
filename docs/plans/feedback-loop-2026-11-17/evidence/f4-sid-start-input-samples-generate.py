"""Generate the F4-SID-START-INPUT cold-read evidence samples via the real CLI.

Three ordinary launches, each in its own isolated temp root (synthetic company
codes, offline audit hook, mapped owner state root, no OUT/DIR variable):

* ``refusal``  -- ``--companies`` names a file that does not exist (entry read
  failure: exit 1, nothing dispatched, cause chain on record);
* ``no-tasks`` -- ``--companies`` names a comment-only list (explicit empty work
  item: exit 0, ``no_tasks``, 0 attempted, nothing sent);
* ``started``  -- a config whose ``companies`` is non-empty next to the default
  empty ``test_cases`` (two sub-items really start: exit 0, ``all_completed``).

The produced observations, sanitized details, ready markers and run receipts
are copied next to this script with the ``f4-sid-start-input-<case>-`` prefix.
The samples carry no path, command, raw exception text or company-list content.

Run from the repo root:

    C:/Miniconda/python.exe docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-start-input-samples-generate.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests" / "unit"))
import test_f4_start_input as T  # noqa: E402  (sanctioned counting double + helpers)

tmp = Path(tempfile.mkdtemp(prefix="f4si-"))
dest = Path(__file__).resolve().parent
copied = 0


def publish(case, root, proc, calls):
    global copied
    print(f"{case}: exit={T._exit(proc)} engine_calls={calls}")
    for src in sorted((T._state(root) / "observations").glob("*")) + sorted(
        (T._state(root) / "runs").glob("*.json")
    ):
        if src.is_file():
            shutil.copy2(src, dest / f"f4-sid-start-input-{case}-{src.name}")
            copied += 1
    first, second = T._cold_reconcile(root), T._cold_reconcile(root)
    print(f"{case}: cold reconcile x2 identical={first == second} result={json.dumps(first, sort_keys=True)}")


refusal = tmp / "refusal"
T._work(refusal)
T._write_config(refusal / "work")
proc, calls = T._launch(refusal, ["--companies", "missing.txt", "--config", "config.json"])
publish("refusal", refusal, proc, calls)

no_tasks = tmp / "no-tasks"
T._work(no_tasks)
T._write_config(no_tasks / "work")
T._companies(no_tasks / "work", "# synthetic list: nothing to run\n")
proc, calls = T._launch(no_tasks, ["--companies", "companies.txt", "--config", "config.json"])
publish("no-tasks", no_tasks, proc, calls)

started = tmp / "started"
T._work(started)
T._write_config(
    started / "work",
    companies=[{"stock_code": "900001"}, {"stock_code": "900002", "company_name": "synthetic-b"}],
    test_cases=[],
)
proc, calls = T._launch(started, ["--config", "config.json", "--parallel"])
publish("started", started, proc, calls)

print("copied:", copied, "files into", dest)
shutil.rmtree(tmp, ignore_errors=True)
print("temp root removed:", not tmp.exists())
