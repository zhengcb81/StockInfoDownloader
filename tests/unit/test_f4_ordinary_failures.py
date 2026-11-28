"""F4-SID-FAILURES — 下载失败记录防丢与普通任务结算。

RED contract for the F4 card, driven through the *real* public entries in
isolated Python subprocesses (never in-process mocks of the business flow):

* ``FailedDownloadLogger`` must keep a refused batch queued until the write is
  durably on disk, must keep arrivals that land mid-flush, and old failure
  files must stay readable across retries (audit line 12,
  ``log-ack-before-persistence``);
* ``main.py`` must settle what actually happened: a genuine task failure may
  not be reported as "All tasks completed" with exit 0, per-task results stay
  separate, and the ordinary CLI publishes ``feedback-observation/1``
  observations plus a startup receipt through the direct-launch publication
  interface (audit line 13, ``business-failure-classified-expected``);
* adapter CLI failures keep their public error codes but distinguish stage,
  cause types and whether anything was actually sent in the details;
* publication covers the three interface modes (explicit OUT, DIR inbox,
  default owner state root) and the three delivery windows (data without
  ready, ready without ack, concurrent redelivery).

Isolation: every subprocess gets a fresh temp working directory with an
audit-hook ``sitecustomize`` that refuses sockets, a synthetic config and
company list (never the user's on-disk lists), and a mapped owner state root.
Doubles sit only at the disk-fault injection point and the download engine
boundary.  All readbacks run in separate interpreter processes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.native_process_fixture import native_run, native_start

import pytest

REPO = Path(__file__).resolve().parents[2]
MAIN_PY = REPO / "main.py"
FIXTURE = REPO / "tests" / "fixtures" / "feedback_observation" / "listing_identity_rows.json"
PYTHON = [sys.executable, "-B", "-X", "utf8"]

# Inherits nothing feedback-related from the harness environment.
ENV_KEEP = {
    "PATH", "PATHEXT", "COMSPEC", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
    "SYSTEMDRIVE", "USERPROFILE",
}

OFFLINE_SITE = """import sys
def _no_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo"):
        raise RuntimeError("offline fixture")
sys.addaudithook(_no_network)
"""

LOG_WRITER = '''
import json, os, sys
from pathlib import Path
from unittest.mock import patch
from src.downloader import FailedDownloadLogger

sink = FailedDownloadLogger(sys.argv[1])
sink.record("900001", "synthetic-a", "doc-one", "fixture-url-1", "offline failure one")
sink.record("900002", "synthetic-b", "doc-two", "fixture-url-2", "offline failure two")
original_replace = os.replace
replaces = {"count": 0}

def first_persistence_refused(src, dst, *args, **kwargs):
    if Path(dst) == sink.log_file and replaces["count"] == 0:
        replaces["count"] += 1
        raise PermissionError("offline log write fault")
    return original_replace(src, dst, *args, **kwargs)

with patch("os.replace", first_persistence_refused):
    sink.flush()  # the first durability barrier is refused
    after_refused = len(sink.get_failed())
sink.record("900003", "synthetic-c", "doc-three", "fixture-url-3", "arrived after refusal")

def enqueue_mid_flush(src, dst, *args, **kwargs):
    if Path(dst) == sink.log_file:
        sink.record("900004", "synthetic-d", "doc-four", "fixture-url-4", "enqueued mid-flush")
    return original_replace(src, dst, *args, **kwargs)

with patch("os.replace", enqueue_mid_flush):
    sink.flush()  # one more failure lands while this flush is being written
    pending_after_success = len(sink.get_failed())
sink.flush()  # plain recovery flush for whatever stayed queued
print(json.dumps({
    "after_refused": after_refused,
    "pending_after_success": pending_after_success,
    "pending_final": len(sink.get_failed()),
}))
'''

MIGRATION_WRITER = '''
import json, os, sys
from pathlib import Path
from unittest.mock import patch
from src.downloader import FailedDownloadLogger

sink = FailedDownloadLogger(sys.argv[1])
sink.record("900009", "synthetic-new", "new-doc", "fixture-url-new", "new failure")
original_replace = os.replace
replaces = {"count": 0}

def first_persistence_refused(src, dst, *args, **kwargs):
    if Path(dst) == sink.log_file and replaces["count"] == 0:
        replaces["count"] += 1
        raise PermissionError("offline log write fault")
    return original_replace(src, dst, *args, **kwargs)

with patch("os.replace", first_persistence_refused):
    sink.flush()
sink.flush()
print(json.dumps({"pending_final": len(sink.get_failed())}))
'''

SINGLE_DRIVER = '''
import json, runpy, sys
from unittest.mock import patch
from src.downloader import StockDownloader
from src.mapping import MappingManager

def _engine_fault(self, request):
    raise PermissionError("offline storage fault")

status = 0
with patch.object(StockDownloader, "download", _engine_fault), \\
        patch.object(MappingManager, "get_stock_name", return_value="fixture"):
    sys.argv = [sys.argv[1], sys.argv[2], "--config", sys.argv[3]]
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as stop:
        status = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
print(json.dumps({"exit_code": status}))
'''

SINGLE_OK_DRIVER = '''
import json, runpy, sys
from unittest.mock import patch
from src.downloader import StockDownloader
from src.mapping import MappingManager
from src.models import DownloadResult

def _engine_ok(self, request):
    return DownloadResult(success=True, downloaded_files=["stub.pdf"], total_files=1)

status = 0
with patch.object(StockDownloader, "download", _engine_ok), \\
        patch.object(MappingManager, "get_stock_name", return_value="fixture"):
    sys.argv = [sys.argv[1], sys.argv[2], "--config", sys.argv[3]]
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as stop:
        status = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
print(json.dumps({"exit_code": status}))
'''

MULTI_DRIVER = '''
import json, runpy, sys
from unittest.mock import patch
from src.downloader import StockDownloader
from src.mapping import MappingManager
from src.models import DownloadResult

fail = set(sys.argv[2].split(","))

def _engine(self, request):
    if request.stock_code in fail:
        raise PermissionError("offline storage fault")
    return DownloadResult(success=True, downloaded_files=["stub.pdf"], total_files=1)

status = 0
with patch.object(StockDownloader, "download", _engine), \\
        patch.object(MappingManager, "get_stock_name", return_value="fixture"):
    sys.argv = [sys.argv[1], "--companies", sys.argv[3], "--config", sys.argv[4]]
    try:
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as stop:
        status = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
print(json.dumps({"exit_code": status}))
'''

KILL_DRIVER = '''
import json, os, runpy, sys
from pathlib import Path
from unittest.mock import patch
from src.downloader import StockDownloader
from src.mapping import MappingManager

marker = Path(sys.argv[3])

def _die_mid_task(self, request):
    marker.write_text("reached engine", encoding="ascii")
    os._exit(9)

with patch.object(StockDownloader, "download", _die_mid_task), \\
        patch.object(MappingManager, "get_stock_name", return_value="fixture"):
    main_py = sys.argv[1]
    sys.argv = [main_py, sys.argv[2], "--config", sys.argv[4]]
    runpy.run_path(main_py, run_name="__main__")
'''

ADAPTER_DISCOVER_DRIVER = '''
import json, sys
from pathlib import Path
from unittest.mock import patch
from src.cninfo_api import CninfoAnnouncementClient
from src.company_wiki_adapter_cli import main
from src.company_wiki_adapter import DisclosureCandidate

case, sample, config = sys.argv[1:4]
original = DisclosureCandidate.to_dict

def post(*args, **kwargs):
    if case == "provider-timeout":
        raise TimeoutError("synthetic offline timeout")
    records = json.loads(Path(sample).read_text(encoding="utf8"))["announcements"]
    return {"announcements": records, "totalRecordNum": len(records), "totalpages": 1}

def serialized(candidate):
    value = original(candidate)
    if case == "missing-candidate-id":
        del value["security_id"]
    return value

with patch.object(CninfoAnnouncementClient, "_post_json", post), \\
        patch.object(DisclosureCandidate, "to_dict", serialized):
    raise SystemExit(main(["discover", "--config", config]))
'''

ADAPTER_FETCH_DRIVER = '''
import json, sys
from src.company_wiki_adapter_cli import main
raise SystemExit(main(["fetch", "--config", sys.argv[1], "--staging-dir", sys.argv[2]]))
'''

# A-table row 3: a normal empty result keeps its own no_candidates semantics.
ADAPTER_EMPTY_DRIVER = '''
import json, sys
from unittest.mock import patch
from src.cninfo_api import CninfoAnnouncementClient
from src.company_wiki_adapter_cli import main

def post(*args, **kwargs):
    return {"announcements": [], "totalRecordNum": 0, "totalpages": 1}

with patch.object(CninfoAnnouncementClient, "_post_json", post):
    raise SystemExit(main(["discover", "--config", sys.argv[1]]))
'''

# The budget refusal control goes through the real bounded-response
# enforcement: only the external transport (urlopen) is replaced, so the
# declared Content-Length is charged against the small response budget.
ADAPTER_BUDGET_DRIVER = '''
import json, sys
import urllib.request
from unittest.mock import patch
from src.company_wiki_adapter_cli import main

class _FakeResponse:
    status = 200
    headers = {"Content-Length": "1000000"}

    def read(self, n=-1):
        return b"x" * 1000000

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

with patch.object(urllib.request, "urlopen", lambda *a, **k: _FakeResponse()):
    raise SystemExit(main(["discover", "--config", sys.argv[1]]))
'''

PUBLISH_KILL_BEFORE_READY = '''
import os, sys
from pathlib import Path
from src import feedback_publish as fp

class DieBeforeReady(fp.Publisher):
    def _write_ready(self, ready_path, payload):
        os._exit(9)

publisher = DieBeforeReady(
    run_id="run-kill-ready", attempt_id="try-kill-ready", version="test-v1",
    target=("dir", Path(sys.argv[1])), state_root=Path(sys.argv[2]),
)
publisher.publish(
    step_id="step-kill-ready", check_id="ordinary-download-task",
    expected="completed", actual="failed", disposition="deviation",
    details={"cause_chain": ["PermissionError", "terminal"], "stage": "download-engine"},
)
'''

PUBLISH_KILL_BEFORE_ACK = '''
import os, sys
from pathlib import Path
from src import feedback_publish as fp

class DieBeforeAck(fp.Publisher):
    def _ack(self, occurrence):
        os._exit(9)

publisher = DieBeforeAck(
    run_id="run-kill-ack", attempt_id="try-kill-ack", version="test-v1",
    target=("dir", Path(sys.argv[1])), state_root=Path(sys.argv[2]),
)
publisher.publish(
    step_id="step-kill-ack", check_id="ordinary-download-task",
    expected="completed", actual="failed", disposition="deviation",
    details={"cause_chain": ["PermissionError", "terminal"], "stage": "download-engine"},
)
'''

RECLI = (
    "import json, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[2])\n"
    "from src.feedback_files import native_path\n"
    "pattern = Path(sys.argv[1])\nrows = []\n"
    "for entry in sorted(native_path(pattern.parent).glob(pattern.name)):\n"
    "    path = str(entry)\n"
    "    text = native_path(entry).read_text(encoding='utf-8')\n"
    "    if path.endswith('.ready'):\n"
    "        rows.append(json.loads(text))\n"
    "    elif path.endswith('.json'):\n"
    "        row = json.loads(text)\n"
    "        rows.extend(row) if isinstance(row, list) else rows.append(row)\n"
    "    else:\n"
    "        rows.extend(json.loads(line) for line in text.splitlines() if line.strip())\n"
    "print(json.dumps(rows))\n"
)


# ── isolation helpers ─────────────────────────────────────────────────────


def _work(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir()
    (work / "sitecustomize.py").write_text(OFFLINE_SITE, encoding="ascii")
    return work


def _env(work: Path, state_root: Path | None = None, **extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k.upper() in ENV_KEEP}
    env.update(
        PYTHONPATH=os.pathsep.join((str(work), str(REPO))),
        PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    for name in (
        "RESEARCH_FEEDBACK_OUT", "RESEARCH_FEEDBACK_RUN_ID",
        "RESEARCH_FEEDBACK_ATTEMPT_ID", "RESEARCH_FEEDBACK_DIR",
        "RESEARCH_FEEDBACK_STATE_ROOT", "RESEARCH_FEEDBACK_SID_CAPTURE_DIR",
    ):
        env.pop(name, None)
    if state_root is not None:
        env["RESEARCH_FEEDBACK_STATE_ROOT"] = str(state_root)
    env.update(extra)
    return env


def _config(work: Path) -> Path:
    path = work / "config.json"
    path.write_text(
        json.dumps({
            "save_dir": str(work / "downloads"),
            "headless": True,
            "max_retries": 0,
            "pages": [{"name": "research", "suffix": "research", "max_pages": 1}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _companies(work: Path, codes: list[str]) -> Path:
    path = work / "companies.txt"
    path.write_text(
        "\n".join(f"{code} synthetic-{code}" for code in codes) + "\n",
        encoding="utf-8",
    )
    return path


def _run(
    args: list[str], env: dict, work: Path, timeout: int = 120, payload: bytes = b"",
) -> subprocess.CompletedProcess:
    return native_run(
        args, cwd=work, env=env, capture_output=True, timeout=timeout, input=payload,
    )


def _receipt(proc: subprocess.CompletedProcess) -> dict:
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1]) if lines else {}


def _readback(pattern: str) -> list:
    """Cold read in a separate, isolated interpreter process."""
    proc = native_run(
        [*PYTHON, "-I", "-c", RECLI, pattern, str(REPO)],
        capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _inbox(work: Path, name: str = "inbox") -> dict:
    directory = work / name
    return {
        "dir": directory,
        "data": sorted(
            p for p in directory.glob("feedback-*.jsonl")
            if not p.name.endswith(".details.jsonl")
        ),
        "ready": sorted(directory.glob("feedback-*.ready")),
        "details": sorted(directory.glob("feedback-*.details.jsonl")),
        "other": sorted(
            p for p in directory.glob("*")
            if not (p.name.endswith(".jsonl") or p.name.endswith(".ready"))
        ),
    }


def _state(work: Path) -> Path:
    return work / "state"


def _stdout_text(proc: subprocess.CompletedProcess) -> str:
    return proc.stdout.decode("utf-8", errors="replace")


def _stderr_text(proc: subprocess.CompletedProcess) -> str:
    return proc.stderr.decode("utf-8", errors="replace")


def _is_safe(value) -> bool:
    if isinstance(value, str):
        return ".." not in value and "://" not in value and "\\" not in value
    if isinstance(value, list):
        return all(_is_safe(item) for item in value)
    return isinstance(value, (int, float, bool)) or value is None


# ── A1: the failure log survives a refused write ──────────────────────────


class TestFailureLogPersistence:
    def test_refused_flush_keeps_batch_until_persisted(self, tmp_path):
        """Audit line 12: a refused write must not acknowledge the batch.

        Two distinct failures are recorded, the first persistence is refused,
        one more failure arrives after the refusal and one *during* the
        recovered flush.  A separate process then cold-reads the file: every
        original occurrence survives exactly once.
        """
        work = _work(tmp_path)
        log_file = work / "failed_downloads.json"
        proc = _run([*PYTHON, "-c", LOG_WRITER, str(log_file)], _env(work), work)
        assert proc.returncode == 0, proc.stderr
        state = _receipt(proc)
        # The refused batch is still queued after the refused flush.
        assert state["after_refused"] == 2
        # The mid-flush arrival stays queued for the next flush.
        assert state["pending_after_success"] == 1
        assert state["pending_final"] == 0
        rows = _readback(str(log_file))
        assert len(rows) == 4
        keys = {(row["stock_code"], row["file_name"]) for row in rows}
        assert keys == {
            ("900001", "doc-one"), ("900002", "doc-two"),
            ("900003", "doc-three"), ("900004", "doc-four"),
        }

    def test_legacy_records_survive_refused_and_recovered_flush(self, tmp_path):
        """Old failure files stay readable; retries must not lose either side."""
        work = _work(tmp_path)
        log_file = work / "failed_downloads.json"
        legacy = [{
            "timestamp": "2020-01-01T00:00:00", "stock_code": "600000",
            "stock_name": "legacy", "file_name": "old-report",
            "url": "fixture-url", "error": "old failure",
        }]
        log_file.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
        proc = _run([*PYTHON, "-c", MIGRATION_WRITER, str(log_file)], _env(work), work)
        assert proc.returncode == 0, proc.stderr
        assert _receipt(proc)["pending_final"] == 0
        rows = _readback(str(log_file))
        assert len(rows) == 2
        assert rows[0]["stock_code"] == "600000"
        assert rows[0]["error"] == "old failure"
        assert rows[1]["stock_code"] == "900009"

    def test_flush_failure_keeps_pending_and_later_arrivals_in_memory(self, tmp_path):
        """Fast in-process variant: refusal at the durability barrier keeps
        this batch and later items, in order."""
        import os
        from unittest.mock import patch
        from src.downloader import FailedDownloadLogger

        log_file = tmp_path / "failed.json"
        sink = FailedDownloadLogger(str(log_file))
        sink.record("900001", "a", "doc", "url", "err")
        real_replace = os.replace

        def refused(src, dst, *args, **kwargs):
            if Path(dst) == sink.log_file:
                raise PermissionError("offline log write fault")
            return real_replace(src, dst, *args, **kwargs)

        with patch("os.replace", refused):
            sink.flush()
        assert len(sink.get_failed()) == 1
        assert not log_file.exists()
        sink.record("900002", "b", "doc2", "url2", "err2")
        sink.flush()  # recovery
        assert sink.get_failed() == []
        rows = json.loads(log_file.read_text(encoding="utf-8"))
        assert [row["stock_code"] for row in rows] == ["900001", "900002"]


# ── A2: ordinary tasks settle honestly ────────────────────────────────────


class TestOrdinarySettlement:
    def test_single_failed_task_is_not_reported_as_success(self, tmp_path):
        """Audit line 13: PermissionError task may not end as exit 0 all-done."""
        work = _work(tmp_path)
        config = _config(work)
        proc = _run(
            [*PYTHON, "-c", SINGLE_DRIVER, str(MAIN_PY), "900001", str(config)],
            _env(work, state_root=_state(work)), work,
        )
        receipt = _receipt(proc)
        assert receipt["exit_code"] != 0
        assert "All tasks completed" not in _stderr_text(proc)
        assert "Task failed" in _stderr_text(proc)
        assert "Traceback" not in _stderr_text(proc)

        rows = _readback(str(_state(work) / "observations" / "feedback-*.jsonl"))
        terminals = [row for row in rows if row.get("check_id") == "ordinary-download-task"]
        assert terminals, "failed task must be observable"
        assert terminals[0]["actual"] == "failed"
        assert terminals[0]["disposition"] == "deviation"
        assert terminals[0]["owner"] == "stockinfo-dl-simple"
        assert "version" in terminals[0]
        settlement = [row for row in rows if row.get("check_id") == "ordinary-run-settlement"]
        assert settlement and settlement[0]["actual"] == "all_failed"
        assert settlement[0]["disposition"] == "deviation"

        details = _readback(str(_state(work) / "observations" / "feedback-*.details.jsonl"))
        task_detail = next(
            d for d in details
            if d.get("details_ref", "").startswith("details:download-") and "stage" in d
        )
        assert task_detail["stage"] == "download-engine"
        assert task_detail["executed_state"] == "attempted"
        assert "PermissionError" in task_detail["cause_chain"]
        settlement_detail = next(
            d for d in details if d.get("details_ref", "").startswith("details:settlement-")
        )
        assert settlement_detail["exit_code"] != 0
        assert settlement_detail["failed"] == 1

    def test_two_tasks_settle_separately_one_success_one_failure(self, tmp_path):
        work = _work(tmp_path)
        config = _config(work)
        companies = _companies(work, ["900001", "900002"])
        proc = _run(
            [*PYTHON, "-c", MULTI_DRIVER, str(MAIN_PY), "900001", str(companies), str(config)],
            _env(work, state_root=_state(work)), work,
        )
        assert _receipt(proc)["exit_code"] != 0
        assert "All tasks completed" not in _stderr_text(proc)

        progress = json.loads(
            (work / "logs" / "progress.json").read_text(encoding="utf-8")
        )
        assert progress["completed"] == ["900002"]
        assert progress["failed"] == ["900001"]

        rows = _readback(str(_state(work) / "observations" / "feedback-*.jsonl"))
        terminals = [r for r in rows if r.get("check_id") == "ordinary-download-task"]
        assert len(terminals) == 2
        by_actual = {r["actual"] for r in terminals}
        assert by_actual == {"completed", "failed"}
        assert len({r["step_id"] for r in terminals}) == 2
        detail_rows = _readback(
            str(_state(work) / "observations" / "feedback-*.details.jsonl")
        )
        stock_failed = [
            d for d in detail_rows
            if d.get("stock_code") == "900001" and "cause_chain" in d
        ]
        assert stock_failed and "PermissionError" in stock_failed[0]["cause_chain"]
        stock_ok = [
            d for d in detail_rows
            if d.get("stock_code") == "900002" and "stage" in d
        ]
        assert stock_ok
        # the failed task's details_ref names the same step as its terminal row
        failed_step = next(
            r["step_id"] for r in terminals if r["actual"] == "failed"
        )
        assert stock_failed[0]["details_ref"] == f"details:{failed_step}"
        settlement = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
        assert settlement[0]["actual"] == "partial"

        receipts = _readback(str(_state(work) / "runs" / "*.json"))
        assert len(receipts) == 1
        assert receipts[0]["terminal"]["result"] == "partial"

    def test_two_simultaneous_failures_stay_two_occurrences(self, tmp_path):
        """B: two different events failing in the same run are settled as two
        distinct occurrences — separate failed terminals, one all_failed
        settlement, and a sibling receipt that is never confused with them."""
        work = _work(tmp_path)
        config = _config(work)
        companies = _companies(work, ["900001", "900003"])
        proc = _run(
            [*PYTHON, "-c", MULTI_DRIVER, str(MAIN_PY), "900001,900003",
             str(companies), str(config)],
            _env(work, state_root=_state(work)), work,
        )
        assert _receipt(proc)["exit_code"] != 0
        rows = _readback(str(_state(work) / "observations" / "feedback-*.jsonl"))
        terminals = [r for r in rows if r.get("check_id") == "ordinary-download-task"]
        assert len(terminals) == 2
        assert {r["actual"] for r in terminals} == {"failed"}
        assert all(r["disposition"] == "deviation" for r in terminals)
        assert len({r["step_id"] for r in terminals}) == 2
        detail_rows = _readback(
            str(_state(work) / "observations" / "feedback-*.details.jsonl")
        )
        failed_codes = {
            d.get("stock_code") for d in detail_rows
            if d.get("stock_code") and "cause_chain" in d
        }
        assert failed_codes == {"900001", "900003"}
        settlement = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
        assert settlement and settlement[0]["actual"] == "all_failed"
        receipts = _readback(str(_state(work) / "runs" / "*.json"))
        assert receipts and receipts[0]["terminal"]["result"] == "all_failed"

    def test_successful_task_still_reports_all_completed(self, tmp_path):
        """Control: a genuine success keeps the historical success shape."""
        work = _work(tmp_path)
        config = _config(work)
        proc = _run(
            [*PYTHON, "-c", SINGLE_OK_DRIVER, str(MAIN_PY), "900002", str(config)],
            _env(work, state_root=_state(work)), work,
        )
        assert _receipt(proc)["exit_code"] == 0
        assert "All tasks completed" in _stderr_text(proc)
        rows = _readback(str(_state(work) / "observations" / "feedback-*.jsonl"))
        terminals = [r for r in rows if r.get("check_id") == "ordinary-download-task"]
        assert terminals and terminals[0]["actual"] == "completed"
        assert terminals[0]["disposition"] == "expected"
        settlement = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
        assert settlement and settlement[0]["actual"] == "all_completed"
        assert settlement[0]["disposition"] == "expected"

    def test_broken_config_records_stage_without_side_effects(self, tmp_path):
        work = _work(tmp_path)
        bad = work / "bad.json"
        bad.write_text("{", encoding="ascii")
        proc = _run(
            [*PYTHON, str(MAIN_PY), "900001", "--config", "bad.json"],
            _env(work, state_root=_state(work)), work,
        )
        assert proc.returncode != 0
        assert not (work / "downloads").exists(), "side effects must not start"
        assert not (work / "logs" / "progress.json").exists()
        rows = _readback(str(_state(work) / "observations" / "feedback-*.jsonl"))
        settlement = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
        assert settlement and settlement[0]["actual"] == "not_started"
        details = _readback(str(_state(work) / "observations" / "feedback-*.details.jsonl"))
        assert details and details[0].get("stage") == "config"
        receipts = _readback(str(_state(work) / "runs" / "*.json"))
        assert receipts and receipts[0]["terminal"]["result"] == "not_started"


# ── adapter CLI: same fault set, distinguishable causes ──────────────────


class TestAdapterFailureDistinction:
    def _fixture_payload(self, tmp_path: Path, kind: str, *, zero_budget: bool = False) -> tuple[Path, str]:
        work = _work(tmp_path)
        (work / "valid.json").write_text("{}", encoding="ascii")
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        discover = {**fixture["request"], "org_id": fixture["announcements"][0]["orgId"]}
        # max_cost_usd "0" makes the budget refusal control; the other
        # discover cases run without a budget so the transport double drives
        # the outcome.
        payload_value = (
            {"adapter_payload_json": json.dumps(fixture["legacy_claim_verified"])}
            if kind == "fetch"
            else {**discover, **({"acquisition_budget": {
                "schema_version": "1.0", "max_response_bytes": 65536,
                "timeout_seconds": 5, "max_cost_usd": "0",
            }} if zero_budget else {})}
        )
        return work, json.dumps(payload_value)

    def _run_adapter(self, work: Path, driver: str, args: list[str], payload: str):
        out = work / "out.jsonl"
        env = _env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="audit",
                   RESEARCH_FEEDBACK_ATTEMPT_ID="first")
        proc = _run([*PYTHON, "-c", driver, *args], env, work, payload=payload.encode("utf-8"))
        return proc, out

    def test_bad_action_preserves_public_cli_shape(self, tmp_path):
        work = _work(tmp_path)
        state = _state(work)
        proc = _run(
            [*PYTHON, "-B", "-m", "src.company_wiki_adapter_cli", "--bad-action"],
            _env(work, state_root=state), work,
        )
        assert proc.returncode == 2  # argparse refusal keeps its public shape
        inbox = _inbox(state, "observations")
        assert len(inbox["ready"]) == 1
        event, = _readback(str(inbox["data"][0]))
        detail, = _readback(str(inbox["details"][0]))
        assert event["refusal_code"] == "invalid_arguments"
        assert detail["sent"] == "not_sent" and detail["stage"] == "arguments"

    def test_payload_rejection_records_stage(self, tmp_path):
        work = _work(tmp_path)
        (work / "valid.json").write_text("{}", encoding="ascii")
        out = work / "out.jsonl"
        env = _env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="audit",
                   RESEARCH_FEEDBACK_ATTEMPT_ID="first")
        proc = _run(
            [*PYTHON, "-m", "src.company_wiki_adapter_cli", "discover", "--config", "valid.json"],
            env, work, payload=b"{",
        )
        assert proc.returncode == 1
        rows = _readback(str(out))
        terminals = [r for r in rows if r.get("check_id") == "candidate-listing-identity"]
        assert terminals
        details = _readback(str(out) + ".details.jsonl")
        assert details and details[0].get("stage") == "payload"
        assert details[0].get("sent") == "not_sent"

    def test_fetch_staging_file_distinct_from_transport(self, tmp_path):
        work, payload = self._fixture_payload(tmp_path, "fetch")
        stage = work / "already-a-file"
        stage.touch()
        proc, out = self._run_adapter(
            work, ADAPTER_FETCH_DRIVER, ["valid.json", str(stage)], payload,
        )
        assert proc.returncode == 1
        last = proc.stderr.splitlines()[-1]
        envelope = json.loads(last)
        assert envelope["status"] == "failed"
        assert envelope["error"]["code"] == "upstream_unavailable"  # compat outer code
        details = _readback(str(out) + ".details.jsonl")
        row = next(d for d in details if d.get("stage") == "staging")
        # A raw OSError in fetch can be pre-send staging setup *or* a
        # post-response local write; unknown is the only honest sent state.
        assert row["sent"] == "unknown"
        assert "FileExistsError" in row["cause_types"]

    def test_fetch_phase_oserror_never_claims_not_sent(self, tmp_path):
        """A raw OSError at the fetch boundary must never report zero cost.

        The fetch phase spans pre-send staging setup *and* post-response
        local writes, so a raw OSError there (staging dir refusal, disk
        full, permission while staging) keeps ``sent`` unknown —
        确知未发送才可报零.
        """
        driver = '''
import json, sys
from unittest.mock import patch
from src.cninfo_api import CninfoAnnouncementClient
from src.company_wiki_adapter_cli import main

def _local_write_fault(self, **kwargs):
    raise PermissionError("offline local write fault after transport")

with patch.object(CninfoAnnouncementClient, "fetch_pdf", _local_write_fault):
    raise SystemExit(main(["fetch", "--config", sys.argv[1], "--staging-dir", sys.argv[2]]))
'''
        work, payload = self._fixture_payload(tmp_path, "fetch")
        staging = work / "staging-dir"
        staging.mkdir()
        proc, out = self._run_adapter(
            work, driver, ["valid.json", str(staging)], payload,
        )
        assert proc.returncode == 1
        details = _readback(str(out) + ".details.jsonl")
        row = next(d for d in details if d.get("stage") == "staging")
        assert row["sent"] == "unknown", "post-transport failure cannot claim not_sent"
        assert "PermissionError" in row["cause_types"]
        assert row.get("code_site") == "company_wiki_adapter_cli.py:failure-handler"

    def test_discover_transport_timeout_distinct(self, tmp_path):
        work, payload = self._fixture_payload(tmp_path, "discover")
        proc, out = self._run_adapter(
            work, ADAPTER_DISCOVER_DRIVER,
            ["provider-timeout", str(FIXTURE), "valid.json"], payload,
        )
        assert proc.returncode == 1
        details = _readback(str(out) + ".details.jsonl")
        row = next(d for d in details if d.get("stage") == "transport")
        assert row["sent"] == "unknown"
        assert "TimeoutError" in row["cause_types"]

    def test_valid_candidates_control(self, tmp_path):
        work, payload = self._fixture_payload(tmp_path, "discover")
        proc, out = self._run_adapter(
            work, ADAPTER_DISCOVER_DRIVER,
            ["valid-candidate", str(FIXTURE), "valid.json"], payload,
        )
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert len(result["candidates"]) >= 1
        rows = _readback(str(out))
        terminals = [r for r in rows if r.get("check_id") == "candidate-listing-identity"]
        assert terminals and terminals[0]["actual"] == "verified"
        assert terminals[0]["disposition"] == "expected"

    def test_missing_identity_control(self, tmp_path):
        work, payload = self._fixture_payload(tmp_path, "discover")
        proc, out = self._run_adapter(
            work, ADAPTER_DISCOVER_DRIVER,
            ["missing-candidate-id", str(FIXTURE), "valid.json"], payload,
        )
        assert proc.returncode == 0
        rows = _readback(str(out))
        terminals = [r for r in rows if r.get("check_id") == "candidate-listing-identity"]
        assert terminals
        assert terminals[0]["actual"] == "missing"
        assert terminals[0]["disposition"] == "deviation"
        assert terminals[0]["issue_key"] == "verified-candidate-id-missing"

    def test_no_candidates_control(self, tmp_path):
        """A-table row 3: a normal empty result is its own honest semantic.

        The provider legitimately reports zero announcements for the window:
        the CLI succeeds with an empty candidate list and the observation
        records ``no_candidates`` as expected — never folded into a failure.
        """
        work, payload = self._fixture_payload(tmp_path, "discover")
        proc, out = self._run_adapter(
            work, ADAPTER_EMPTY_DRIVER, ["valid.json"], payload,
        )
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["candidates"] == []
        rows = _readback(str(out))
        terminals = [r for r in rows if r.get("check_id") == "candidate-listing-identity"]
        assert terminals and terminals[0]["actual"] == "no_candidates"
        assert terminals[0]["disposition"] == "expected"

    def test_budget_refusal_control(self, tmp_path):
        work, payload = self._fixture_payload(tmp_path, "discover")
        budget_payload = json.loads(payload)
        budget_payload["acquisition_budget"] = {
            "schema_version": "1.0", "max_response_bytes": 100,
            "timeout_seconds": 5, "max_cost_usd": "1",
        }
        proc, out = self._run_adapter(
            work, ADAPTER_BUDGET_DRIVER, ["valid.json"], json.dumps(budget_payload),
        )
        assert proc.returncode == 1
        envelope = json.loads(proc.stderr.splitlines()[-1])
        assert envelope["error"]["code"] == "budget_exceeded"
        rows = _readback(str(out))
        budget_rows = [r for r in rows if r.get("check_id") == "acquisition-budget"]
        assert budget_rows and budget_rows[0]["actual"] != "within_budget"


# ── direct-launch publication interface ──────────────────────────────────


class TestPublicationInterface:
    def _run_ok(self, work: Path, config: Path, **env_extra) -> subprocess.CompletedProcess:
        return _run(
            [*PYTHON, "-c", SINGLE_OK_DRIVER, str(MAIN_PY), "900002", str(config)],
            _env(work, **env_extra), work,
        )

    def test_explicit_out_keeps_single_use_file(self, tmp_path):
        work = _work(tmp_path)
        config = _config(work)
        out = work / "out.jsonl"
        proc = self._run_ok(work, config, RESEARCH_FEEDBACK_OUT=str(out),
                            RESEARCH_FEEDBACK_RUN_ID="host-run", RESEARCH_FEEDBACK_ATTEMPT_ID="host-1",
                            RESEARCH_FEEDBACK_STATE_ROOT=str(_state(work)))
        assert _receipt(proc)["exit_code"] == 0
        rows = _readback(str(out))
        assert rows, "explicit OUT keeps the single-use sidecar"
        assert all(row["run_id"] == "host-run" and row["attempt_id"] == "host-1" for row in rows)
        assert Path(str(out) + ".details.jsonl").exists()
        assert not (_state(work) / "observations").exists(), "OUT wins, no inbox copy"

    def test_dir_only_publishes_ready_bound_inbox(self, tmp_path):
        work = _work(tmp_path)
        config = _config(work)
        inbox = _inbox(work)
        proc = self._run_ok(work, config, RESEARCH_FEEDBACK_DIR=str(inbox["dir"]),
                            RESEARCH_FEEDBACK_STATE_ROOT=str(_state(work)))
        assert _receipt(proc)["exit_code"] == 0
        after = _inbox(work)
        assert after["data"] and after["ready"] and after["details"]
        assert not after["other"], "only bound triples live in the inbox"
        ready = json.loads(after["ready"][0].read_text(encoding="utf-8"))
        assert ready["schema_version"] == "sid-ready/1"
        assert ready["owner"] == "stockinfo-dl-simple"
        for value in ready.values():
            assert _is_safe(value), "ready markers carry no paths or commands"
        assert len(ready["occurrence_id"]) == 64
        pending = _readback(str(_state(work) / "pending" / "*.json"))
        assert pending == [], "successful delivery acknowledges the pending record"

    def test_default_state_root_observations(self, tmp_path):
        work = _work(tmp_path)
        config = _config(work)
        # default mode: neither OUT nor DIR; state root mapped to a temp dir
        proc = self._run_ok(work, config, RESEARCH_FEEDBACK_STATE_ROOT=str(_state(work)))
        assert _receipt(proc)["exit_code"] == 0
        rows = _readback(str(_state(work) / "observations" / "feedback-*.jsonl"))
        assert rows
        assert Path(_state(work)).is_dir()

    def test_out_wins_over_dir(self, tmp_path):
        work = _work(tmp_path)
        config = _config(work)
        out = work / "out.jsonl"
        inbox = _inbox(work)
        proc = self._run_ok(
            work, config,
            RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_DIR=str(inbox["dir"]),
            RESEARCH_FEEDBACK_STATE_ROOT=str(_state(work)),
        )
        assert _receipt(proc)["exit_code"] == 0
        assert out.exists() and not inbox["dir"].exists()

    def test_data_without_ready_window_redelivers_same_identity(self, tmp_path):
        work = _work(tmp_path)
        inbox = _inbox(work)
        state = _state(work)
        proc = _run(
            [*PYTHON, "-c", PUBLISH_KILL_BEFORE_READY, str(inbox["dir"]), str(state)],
            _env(work), work,
        )
        assert proc.returncode == 9  # killed between data and ready
        killed_data = sorted(
            p for p in inbox["dir"].glob("feedback-*.jsonl")
            if not p.name.endswith(".details.jsonl")
        )
        assert killed_data and not list(inbox["dir"].glob("feedback-*.ready"))
        pending = _readback(str(state / "pending" / "*.json"))
        assert pending, "unsent delivery stays pending"

        republish = _run(
            [*PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"],
            _env(work, state_root=state), work,
        )
        assert republish.returncode == 0, republish.stderr
        after = _inbox(work)
        assert len(after["data"]) == 1 and len(after["ready"]) == 1
        assert after["data"][0].name == killed_data[0].name, "same delivery identity"
        ready = json.loads(after["ready"][0].read_text(encoding="utf-8"))
        assert ready["step_id"] == "step-kill-ready"
        assert ready["check_id"] == "ordinary-download-task"
        assert _readback(str(state / "pending" / "*.json")) == []

    def test_ready_without_ack_window_redelivers_without_duplicates(self, tmp_path):
        work = _work(tmp_path)
        inbox = _inbox(work)
        state = _state(work)
        proc = _run(
            [*PYTHON, "-c", PUBLISH_KILL_BEFORE_ACK, str(inbox["dir"]), str(state)],
            _env(work), work,
        )
        assert proc.returncode == 9  # delivered, but the ack was lost
        data_before = sorted(
            p for p in inbox["dir"].glob("feedback-*.jsonl")
            if not p.name.endswith(".details.jsonl")
        )
        assert len(data_before) == 1
        republish = _run(
            [*PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"],
            _env(work, state_root=state), work,
        )
        assert republish.returncode == 0, republish.stderr
        after = _inbox(work)
        assert len(after["data"]) == 1 and len(after["ready"]) == 1
        assert after["data"][0].name == data_before[0].name
        assert _readback(str(state / "pending" / "*.json")) == []

    def test_parallel_republishers_deliver_once(self, tmp_path):
        work = _work(tmp_path)
        inbox = _inbox(work)
        state = _state(work)
        _run(
            [*PYTHON, "-c", PUBLISH_KILL_BEFORE_ACK, str(inbox["dir"]), str(state)],
            _env(work), work,
        )
        first = native_start(
            [*PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"],
            cwd=work, env=_env(work, state_root=state),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        second = native_start(
            [*PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"],
            cwd=work, env=_env(work, state_root=state),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        for child in (first, second):
            out, err = child.communicate(timeout=120)
            assert child.returncode == 0, err
        after = _inbox(work)
        assert len(after["data"]) == 1 and len(after["ready"]) == 1
        assert _readback(str(state / "pending" / "*.json")) == []

    def test_duplicate_occurrence_publishes_once(self, tmp_path):
        work = _work(tmp_path)
        state = _state(work)
        driver = (
            "import json, sys\n"
            "from pathlib import Path\n"
            "from src import feedback_publish as fp\n"
            "for attempt in (1, 2):\n"
            "    publisher = fp.Publisher(\n"
            "        run_id='run-dup', attempt_id='try-dup', version='test-v1',\n"
            "        target=('dir', Path(sys.argv[1])), state_root=Path(sys.argv[2]))\n"
            "    status = publisher.publish(\n"
            "        step_id='step-dup', check_id='ordinary-download-task',\n"
            "        expected='completed', actual='failed', disposition='deviation')\n"
            "    print(status)\n"
        )
        proc = _run(
            [*PYTHON, "-c", driver, str(_inbox(work)["dir"]), str(state)], _env(work), work,
        )
        assert proc.returncode == 0, proc.stderr
        statuses = [line.strip() for line in _stdout_text(proc).splitlines() if line.strip()]
        assert statuses == ["delivered", "delivered"], "re-send of one occurrence stays one delivery"
        after = _inbox(work)
        assert len(after["data"]) == 1 and len(after["ready"]) == 1

    def test_unwritable_media_keeps_business_result(self, tmp_path):
        work = _work(tmp_path)
        blocker = work / "not-a-dir"
        blocker.write_text("occupied", encoding="ascii")
        config = _config(work)
        proc = _run(
            [*PYTHON, "-c", SINGLE_DRIVER, str(MAIN_PY), "900001", str(config)],
            _env(work, state_root=blocker), work,
        )
        receipt = _receipt(proc)
        assert receipt["exit_code"] != 0, "business settlement must survive"
        assert "Task failed" in _stderr_text(proc)
        assert "Traceback" not in _stderr_text(proc)

    def test_delivery_failure_keeps_pending_and_reconciles_cold(self, tmp_path):
        """Delivery refusal only affects delivery state; the business result,
        the original request and the metering stay untouched, and a later
        process can reconcile the pending interval cold (read-only)."""
        work = _work(tmp_path)
        state = _state(work)
        config = _config(work)
        state.mkdir(parents=True, exist_ok=True)
        (state / "observations").write_text("occupied", encoding="ascii")
        proc = _run(
            [*PYTHON, "-c", SINGLE_DRIVER, str(MAIN_PY), "900001", str(config)],
            _env(work, state_root=state), work,
        )
        assert _receipt(proc)["exit_code"] != 0, "business result unchanged"
        assert "Task failed" in _stderr_text(proc) and "Traceback" not in _stderr_text(proc)
        receipts = _readback(str(state / "runs" / "*.json"))
        assert receipts and receipts[0]["terminal"]["result"] == "all_failed"
        pending = _readback(str(state / "pending" / "*.json"))
        assert pending, "undelivered observations stay pending"

        recon = _run(
            [*PYTHON, "-B", "-m", "src.feedback_publish", "reconcile", "--json"],
            _env(work, state_root=state), work,
        )
        assert recon.returncode == 0
        report = json.loads(recon.stdout)
        assert report["receipts"] and report["receipts"][0]["terminal"]["result"] == "all_failed"
        assert len(report["pending"]) == len(pending)

    def test_kill_mid_task_leaves_unconfirmed_receipt_and_next_attempt_independent(
        self, tmp_path
    ):
        work = _work(tmp_path)
        state = _state(work)
        config = _config(work)
        marker = work / "engine-marker"
        _run(
            [*PYTHON, "-c", KILL_DRIVER, str(MAIN_PY), "900001", str(marker), str(config)],
            _env(work, state_root=state), work,
        )
        assert marker.exists(), "the engine really was reached"
        receipts = _readback(str(state / "runs" / "*.json"))
        assert len(receipts) == 1 and receipts[0]["terminal"] is None

        # A later, different attempt succeeds and stays independent.
        ok = _run(
            [*PYTHON, "-c", SINGLE_OK_DRIVER, str(MAIN_PY), "900002", str(config)],
            _env(work, state_root=state, RESEARCH_FEEDBACK_RUN_ID="sid-later",
                 RESEARCH_FEEDBACK_ATTEMPT_ID="try-later"),
            work,
        )
        assert _receipt(ok)["exit_code"] == 0
        receipts = _readback(str(state / "runs" / "*.json"))
        assert len(receipts) == 2
        by_run = {r["run_id"]: r for r in receipts}
        killed = [r for rid, r in by_run.items() if rid != "sid-later"]
        assert killed and killed[0]["terminal"] is None
        assert by_run["sid-later"]["terminal"]["result"] == "all_completed"



def test_two_native_logger_instances_keep_both_failures(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from unittest.mock import patch
    from src import downloader

    path = tmp_path / "failed.json"
    first, second = [downloader.FailedDownloadLogger(str(path)) for _ in range(2)]
    first.record("900001", "fixture", "notice", "fixture", "denied")
    second.record("900002", "fixture", "notice", "fixture", "denied")
    first_writing, peer_done = Event(), Event()
    real_write = downloader._atomic_write_json

    def writer(destination, rows):
        if rows[-1]["stock_code"] == "900001":
            first_writing.set()
            peer_done.wait(0.4)
        real_write(destination, rows)

    def peer_flush():
        assert first_writing.wait(5)
        second.flush()
        peer_done.set()

    with patch.object(downloader, "_atomic_write_json", writer), ThreadPoolExecutor(2) as workers:
        original = workers.submit(first.flush)
        other = workers.submit(peer_flush)
        original.result(10)
        other.result(10)
    peer = native_run(
        [*PYTHON, "-I", "-c",
         "import json,sys; print(json.dumps([r['stock_code'] for r in json.load(open(sys.argv[1]))]))",
         str(path)], capture_output=True, timeout=15, check=True,
    )
    assert set(json.loads(peer.stdout)) == {"900001", "900002"}


def test_native_fsync_refusal_cleans_all_three_writers(tmp_path, monkeypatch):
    from src import downloader, feedback_publish

    def refuse(_):
        raise OSError("fixture fsync refusal")

    monkeypatch.setattr(os, "fsync", refuse)
    for writer, payload in ((downloader._atomic_write_json, []),
                            (feedback_publish._atomic_json, {}),
                            (feedback_publish._atomic_lines, ["{}"])):
        with pytest.raises(OSError, match="fixture fsync refusal"):
            writer(tmp_path / (writer.__name__ + ".json"), payload)
    assert not list(tmp_path.iterdir())


def test_default_adapter_failure_and_old_directory_cold_reconcile(tmp_path):
    from src.feedback_candidate_capture import digest

    work = _work(tmp_path)
    state = _state(work)
    old = work / "old-sidecars"
    old.mkdir()
    (work / "cfg.json").write_text("{}", encoding="ascii")
    env = _env(work, state_root=state, RESEARCH_FEEDBACK_RUN_ID="same-original-run",
               RESEARCH_FEEDBACK_ATTEMPT_ID="exact-attempt")
    proc = _run(
        [*PYTHON, "-m", "src.company_wiki_adapter_cli", "discover", "--config", "cfg.json"],
        env, work, payload=b"{",
    )
    assert proc.returncode == 1
    inbox = _inbox(state, "observations")
    assert len(inbox["ready"]) == 2
    observations = _readback(str(inbox["dir"] / "feedback-*.jsonl"))
    first, = [row for row in observations if row.get("check_id") == "action-started"]
    assert first["terminal_check_id"] == "candidate-listing-identity"
    detail, = _readback(str(inbox["details"][0]))
    assert detail["sent"] == "not_sent"
    own = "stockinfo-dl-simple"
    identity = digest([first.get(name) or own for name in
                       ("owner", "origin_owner", "run_id", "attempt_id", "step_id", "check_id")])
    action = digest(["reconcile", own, identity])
    first.setdefault("origin_owner", own)
    body = {"occurrence_id": identity, "observation": first}
    record = {"schema_version": "feedback-action/1", "owner": own, "kind": "reconcile",
              "method": "lookup", "action_id": action, "payload": body,
              "request_digest": digest([own, "reconcile", action, body])}
    command = [*PYTHON, "-m", "src.feedback_owner", "--db", str(work / "actions.sqlite"),
               "--sidecar-dir", str(old), "--sidecar-dir", str(inbox["dir"]), "reconcile"]
    results = [json.loads(_run(command, env, work, payload=json.dumps(record).encode()).stdout) for _ in range(2)]
    assert results[0] == results[1]
    assert results[0]["result"]["job_status"] == "failed"
    assert results[0]["result"]["cost_state"] == "not_applicable"
    assert not (work / "actions.sqlite").exists()


def test_acknowledged_native_observation_is_not_offered_twice(tmp_path):
    from src.feedback_files import native_path
    from src.feedback_publish import Publisher

    from shutil import rmtree

    inbox = native_path(tmp_path / "outbox" / ("nested" * 20) / ("nested" * 20))
    try:
        publisher = Publisher(run_id="original", attempt_id="one", version="fixture",
                              target=("dir", inbox), state_root=tmp_path / "state")
        args = dict(step_id="first", check_id="ordinary-download-task", expected="completed",
                    actual="failed", disposition="deviation", details={"cause_types": ["OSError"]})
        assert publisher.publish(**args) == "delivered"
        marker, = inbox.glob("*.ready")
        original = marker.with_suffix(".jsonl").read_bytes()
        marker.unlink()  # original ROOT receipt
        assert publisher.publish(**args) == "delivered"
        assert not list(inbox.glob("*.ready"))
        assert marker.with_suffix(".jsonl").read_bytes() == original
    finally:
        if inbox.exists():
            rmtree(inbox)



def test_first_run_receipt_terminal_survives_parallel_settlement(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from src import feedback_publish as publish

    assert publish.write_startup_receipt("original", "one", root=tmp_path)
    first_writing = Event()
    second_started = Event()
    original = publish._atomic_json

    def controlled_write(path, payload):
        if payload["terminal"]["result"] == "failed":
            first_writing.set()
            assert second_started.wait(10)
            assert not second_write.wait(0.2)
        else:
            second_write.set()
        return original(path, payload)

    def settle_later():
        second_started.set()
        return publish.finish_receipt("original", "one", {"result": "all_completed"}, root=tmp_path)

    second_write = Event()
    monkeypatch.setattr(publish, "_atomic_json", controlled_write)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(publish.finish_receipt, "original", "one", {"result": "failed"}, root=tmp_path)
        assert first_writing.wait(10)
        second = executor.submit(settle_later)
        assert first.result(20) and second.result(20)
    original_receipt, = publish.read_receipts(tmp_path)
    assert original_receipt["terminal"] == {"result": "failed"}
