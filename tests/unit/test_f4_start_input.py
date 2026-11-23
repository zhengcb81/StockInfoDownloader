"""F4-SID-START-INPUT — 直启任务清单与失败复原.

RED/GREEN contract for the ordinary launch's *input decision*, driven through
the real ``main.py`` in isolated Python subprocesses (never in-process mocks
of the business flow).  Three audited failures are frozen first:

* an explicit ``--companies`` file that cannot be read used to die with a
  native traceback and leave zero feedback;
* a comment-only list used to exit 0 and report "all tasks completed";
* a fully valid config with non-empty ``companies`` used to be shadowed by the
  loader's default-injected empty ``test_cases`` and run zero tasks.

The contract under test (one decision point, the documented priority):

    CLI stock_code > --companies file > config.test_cases
    > config.companies > config.stock_code > nothing to run

An empty list -- the loader's default or an explicitly empty one -- never
shadows a non-empty lower-priority source.  List read failure, explicit empty
work, legitimate all-skipped, a started task whose provider returns zero
candidates and a genuine failure each keep their own outcome; only sub-items
that really start are counted as attempted.

Isolation: every subprocess gets a fresh temp working directory with an
audit-hook ``sitecustomize`` that refuses sockets, a synthetic config and
company list (never the user's on-disk lists), and the owner state root mapped
to a temp directory.  The download engine boundary is the only double; it
counts every call so the number of really started sub-items is read back from
disk.  Feedback variables OUT/DIR are never set here: the default owner
publication path is exercised.  All readbacks and cold reads run in separate
interpreter processes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAIN_PY = REPO / "main.py"
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

# The download engine boundary is the only double: every call is counted on
# disk, so "how many sub-items really started" is read back by another process.
ARGV_DRIVER = '''
import json, runpy, sys
from pathlib import Path
from unittest.mock import patch
from src.downloader import StockDownloader
from src.mapping import MappingManager
from src.models import DownloadResult

spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
count_file = Path(spec["count_file"])
fail = set(spec.get("fail", []))
zero = set(spec.get("zero", []))

def _engine(self, request):
    with count_file.open("a", encoding="ascii") as stream:
        stream.write(request.stock_code + "\\n")
    if request.stock_code in fail:
        raise PermissionError("offline storage fault")
    files = [] if request.stock_code in zero else ["stub.pdf"]
    return DownloadResult(success=True, downloaded_files=files, total_files=len(files))

status = 0
with patch.object(StockDownloader, "download", _engine), \\
        patch.object(MappingManager, "get_stock_name", return_value="fixture"):
    sys.argv = [spec["main"], *spec["argv"]]
    try:
        runpy.run_path(spec["main"], run_name="__main__")
    except SystemExit as stop:
        status = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
print(json.dumps({"exit_code": status}))
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

OWNER = "stockinfo-dl-simple"


# ── isolation helpers ─────────────────────────────────────────────────────


def _work(root: Path) -> Path:
    work = root / "work"
    work.mkdir(parents=True, exist_ok=True)
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


def _write_config(work: Path, **extra) -> Path:
    path = work / "config.json"
    payload = {
        "save_dir": str(work / "downloads"),
        "headless": True,
        "max_retries": 0,
        "pages": [{"name": "research", "suffix": "research", "max_pages": 1}],
    }
    payload.update(extra)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _companies(work: Path, text: str, name: str = "companies.txt") -> Path:
    path = work / name
    path.write_text(text, encoding="utf-8")
    return path


def _run(args: list[str], env: dict, work: Path, payload: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.run(
        args, cwd=work, env=env, capture_output=True, timeout=120, input=payload,
    )


def _readback(pattern: str) -> list:
    """Cold read in a separate, isolated interpreter process."""
    proc = subprocess.run(
        [*PYTHON, "-I", "-c", RECLI, pattern, str(REPO)],
        capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _state(root: Path) -> Path:
    return root / "state"


def _count_file(root: Path) -> Path:
    return root / "engine-calls.txt"


def _stderr_text(proc: subprocess.CompletedProcess) -> str:
    return proc.stderr.decode("utf-8", errors="replace")


def _exit(proc: subprocess.CompletedProcess) -> int:
    """The driver prints the interpreter's exit; a crash has no receipt."""
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if lines:
        try:
            return int(json.loads(lines[-1])["exit_code"])
        except (ValueError, KeyError, TypeError):
            pass
    return proc.returncode


def _launch(
    root: Path,
    argv: list[str],
    *,
    fail: tuple[str, ...] = (),
    zero: tuple[str, ...] = (),
    **env_extra: str,
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run the real ``main.py`` once; return the process and its engine calls."""
    work = _work(root)
    spec = {
        "main": str(MAIN_PY),
        "argv": [str(item) for item in argv],
        "count_file": str(_count_file(root)),
        "fail": list(fail),
        "zero": list(zero),
    }
    (work / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
    proc = _run(
        [*PYTHON, "-c", ARGV_DRIVER, str(work / "spec.json")],
        _env(work, state_root=_state(root), **env_extra), work,
    )
    count = _count_file(root)
    calls = count.read_text(encoding="ascii").splitlines() if count.exists() else []
    return proc, calls


def _observations(root: Path) -> list[dict]:
    return _readback(str(_state(root) / "observations" / "feedback-*.jsonl"))


def _details(root: Path) -> list[dict]:
    return _readback(str(_state(root) / "observations" / "feedback-*.details.jsonl"))


def _settlement(rows: list[dict]) -> dict:
    found = [row for row in rows if row.get("check_id") == "ordinary-run-settlement"]
    assert len(found) == 1, f"exactly one settlement expected, got {found}"
    return found[0]


def _settlement_detail(root: Path) -> dict:
    found = [
        item for item in _details(root)
        if str(item.get("details_ref", "")).startswith("details:settlement-")
    ]
    assert len(found) == 1, f"exactly one settlement detail expected, got {found}"
    return found[0]


def _started(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("check_id") == "action-started"]


def _receipts(root: Path) -> list[dict]:
    return _readback(str(_state(root) / "runs" / "*.json"))


def _cold_reconcile(root: Path, work_subdir: str = "work") -> dict:
    """Cold read of the settlement through the public ``src.feedback_owner``."""
    from src.feedback_candidate_capture import digest

    row = dict(_settlement(_observations(root)))
    row.setdefault("origin_owner", OWNER)
    identity = digest([
        row.get(name) or OWNER
        for name in ("owner", "origin_owner", "run_id", "attempt_id", "step_id", "check_id")
    ])
    action = digest(["reconcile", OWNER, identity])
    body = {"occurrence_id": identity, "observation": row}
    record = {
        "schema_version": "feedback-action/1", "owner": OWNER, "kind": "reconcile",
        "method": "lookup", "action_id": action, "payload": body,
        "request_digest": digest([OWNER, "reconcile", action, body]),
    }
    work = root / work_subdir
    command = [
        *PYTHON, "-m", "src.feedback_owner", "--db", str(root / "actions.sqlite"),
        "--sidecar-dir", str(_state(root) / "observations"), "reconcile",
    ]
    proc = _run(command, _env(work, state_root=_state(root)), work,
                payload=json.dumps(record).encode("utf-8"))
    assert proc.returncode == 0, proc.stderr
    assert not (root / "actions.sqlite").exists(), "a cold read never creates state"
    return json.loads(proc.stdout)


def _cold_reconcile_twice(root: Path) -> tuple[dict, dict]:
    return _cold_reconcile(root), _cold_reconcile(root)


# ── the three audited failures ────────────────────────────────────────────


class TestAuditedFailures:
    def test_missing_list_is_a_refusal_not_a_traceback(self, tmp_path):
        """Audited 1: an unreadable explicit list exits 1 with zero feedback."""
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        proc, calls = _launch(
            tmp_path, ["--companies", "missing.txt", "--config", config.name],
        )
        assert _exit(proc) == 1
        assert "Traceback" not in _stderr_text(proc)
        assert calls == [], "a refused entry dispatches nothing"
        assert not (tmp_path / "work" / "logs" / "progress.json").exists()
        settlement = _settlement(_observations(tmp_path))
        assert settlement["actual"] == "not_started"
        detail = _settlement_detail(tmp_path)
        assert detail["stage"] == "companies"
        assert detail["executed_state"] == "not_started"
        assert detail["sent"] == "not_sent"
        assert detail["exit_code"] == 1
        assert detail["attempted"] == 0
        assert detail["cause_chain"][0] == "ConfigError"
        assert _started(_observations(tmp_path)) == []

    def test_comment_only_list_is_an_explicit_empty_work_item(self, tmp_path):
        """Audited 2: zero entries is a legitimate empty run, never 'all done'."""
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        _companies(tmp_path / "work", "# only a comment\n\n   \n")
        proc, calls = _launch(
            tmp_path, ["--companies", "companies.txt", "--config", config.name],
        )
        assert _exit(proc) == 0, "a legitimate zero-task run is not a failure"
        assert "All tasks completed" not in _stderr_text(proc)
        assert "No tasks to run" in _stderr_text(proc)
        assert "Traceback" not in _stderr_text(proc)
        assert calls == []
        settlement = _settlement(_observations(tmp_path))
        assert settlement["actual"] == "no_tasks"
        assert settlement["disposition"] == "expected"
        detail = _settlement_detail(tmp_path)
        assert detail["attempted"] == 0
        assert (detail["succeeded"], detail["failed"], detail["skipped"]) == (0, 0, 0)
        assert detail["sent"] == "not_sent"
        assert _started(_observations(tmp_path)) == []
        assert _receipts(tmp_path)[0]["terminal"]["result"] == "no_tasks"

    def test_config_companies_actually_start(self, tmp_path):
        """Audited 3: a valid config's companies are not shadowed by defaults."""
        _work(tmp_path)
        _write_config(
            tmp_path / "work",
            companies=[{"stock_code": "900001"}, {"stock_code": "900002", "company_name": "b"}],
            test_cases=[],  # what the loader injects by default
            stock_code="900009",
        )
        proc, calls = _launch(tmp_path, ["--config", "config.json"])
        assert _exit(proc) == 0
        assert sorted(calls) == ["900001", "900002"]
        assert "All tasks completed" in _stderr_text(proc)
        detail = _settlement_detail(tmp_path)
        assert (detail["attempted"], detail["succeeded"], detail["failed"]) == (2, 2, 0)
        progress = json.loads(
            (tmp_path / "work" / "logs" / "progress.json").read_text(encoding="utf-8")
        )
        assert sorted(progress["completed"]) == ["900001", "900002"]


# ── one decision point: the documented priority ───────────────────────────


class TestInputPriority:
    def test_explicit_list_overrides_every_config_source(self, tmp_path):
        _work(tmp_path)
        _write_config(
            tmp_path / "work",
            test_cases=[{"stock_code": "900004", "suffix": "research"}],
            companies=[{"stock_code": "900002"}],
            stock_code="900009",
        )
        _companies(tmp_path / "work", "900001 explicit-a\n")
        _, calls = _launch(
            tmp_path, ["--companies", "companies.txt", "--config", "config.json"],
        )
        assert calls == ["900001"]

    def test_cli_positional_keeps_the_highest_priority(self, tmp_path):
        _work(tmp_path)
        _write_config(tmp_path / "work", companies=[{"stock_code": "900002"}])
        _companies(tmp_path / "work", "900001 explicit-a\n")
        _, calls = _launch(
            tmp_path,
            ["900010", "--companies", "companies.txt", "--config", "config.json"],
        )
        assert calls == ["900010"]

    def test_config_test_cases_outrank_config_companies(self, tmp_path):
        _work(tmp_path)
        _write_config(
            tmp_path / "work",
            test_cases=[{"stock_code": "900004", "suffix": "research"}],
            companies=[{"stock_code": "900002"}],
            stock_code="900009",
        )
        proc, calls = _launch(tmp_path, ["--config", "config.json"])
        assert _exit(proc) == 0
        assert calls == ["900004"]
        assert not (tmp_path / "work" / "logs" / "progress.json").exists(), (
            "test cases are not a company-list run"
        )

    def test_config_stock_code_runs_when_both_lists_are_empty(self, tmp_path):
        _work(tmp_path)
        _write_config(
            tmp_path / "work", companies=[], test_cases=[], stock_code="900009",
        )
        proc, calls = _launch(tmp_path, ["--config", "config.json"])
        assert _exit(proc) == 0
        assert calls == ["900009"]

    def test_no_input_at_all_is_no_tasks_not_a_failure(self, tmp_path):
        _work(tmp_path)
        _write_config(tmp_path / "work")
        proc, calls = _launch(tmp_path, ["--config", "config.json"])
        assert _exit(proc) == 0
        assert "All tasks completed" not in _stderr_text(proc)
        assert calls == []
        assert _settlement(_observations(tmp_path))["actual"] == "no_tasks"


# ── each outcome keeps its own shape ──────────────────────────────────────


class TestOutcomesStayDistinct:
    def test_all_skipped_is_legitimate_and_not_confused_with_real_work(self, tmp_path):
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        _companies(tmp_path / "work", "900001 a\n900002 b\n")
        logs = tmp_path / "work" / "logs"
        logs.mkdir()
        (logs / "progress.json").write_text(json.dumps({
            "started_at": "2020-01-01T00:00:00", "last_updated": "2020-01-01T00:00:00",
            "companies_file": "companies.txt", "total": 2,
            "completed": ["900001", "900002"], "failed": [],
        }), encoding="utf-8")
        proc, calls = _launch(
            tmp_path, ["--companies", "companies.txt", "--config", config.name],
        )
        assert _exit(proc) == 0
        assert calls == []
        assert "Traceback" not in _stderr_text(proc)
        settlement = _settlement(_observations(tmp_path))
        assert settlement["actual"] == "all_completed"
        assert settlement["disposition"] == "expected"
        detail = _settlement_detail(tmp_path)
        assert (detail["attempted"], detail["skipped"], detail["sent"]) == (0, 2, "not_sent")
        assert _started(_observations(tmp_path)) == []
        first, second = _cold_reconcile_twice(tmp_path)
        assert first == second
        assert first["result"]["job_status"] == "succeeded"
        assert first["result"]["cost_state"] == "not_applicable"

    def test_provider_zero_candidates_is_a_started_task(self, tmp_path):
        """Zero candidates is the provider's answer to a task that did start."""
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        proc, calls = _launch(
            tmp_path, ["900005", "--config", config.name], zero=("900005",),
        )
        assert _exit(proc) == 0
        assert calls == ["900005"]
        rows = _observations(tmp_path)
        terminal = [r for r in rows if r.get("check_id") == "ordinary-download-task"][0]
        assert terminal["actual"] == "completed"
        assert len(_started(rows)) == 1
        detail = _settlement_detail(tmp_path)
        assert (detail["attempted"], detail["succeeded"]) == (1, 1)
        assert "sent" not in detail, "a started task cannot claim nothing was sent"

    def test_genuine_failure_still_fails(self, tmp_path):
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        _companies(tmp_path / "work", "900001 a\n")
        proc, calls = _launch(
            tmp_path, ["--companies", "companies.txt", "--config", config.name],
            fail=("900001",),
        )
        assert _exit(proc) == 1
        assert calls == ["900001"]
        assert "Traceback" not in _stderr_text(proc)
        detail = _settlement_detail(tmp_path)
        assert (detail["attempted"], detail["succeeded"], detail["failed"]) == (1, 0, 1)
        assert _settlement(_observations(tmp_path))["actual"] == "all_failed"
        first, _ = _cold_reconcile_twice(tmp_path)
        assert first["result"]["job_status"] == "failed"
        assert first["result"]["cost_state"] == "unknown"


# ── entry read failures: cause chain, no dispatch, no cost ─────────────────


class TestEntryReadFailures:
    def test_missing_list_cold_reads_failed_known_not_sent(self, tmp_path):
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        proc, calls = _launch(
            tmp_path, ["--companies", "missing.txt", "--config", config.name],
        )
        assert _exit(proc) == 1 and calls == []
        assert _receipts(tmp_path)[0]["terminal"]["result"] == "not_started"
        first, second = _cold_reconcile_twice(tmp_path)
        assert first == second
        assert first["result"]["job_status"] == "failed"
        assert first["result"]["status"] == "known"
        assert first["result"]["cost_state"] == "not_applicable"

    def test_unreadable_list_keeps_its_io_cause_distinct_from_a_wrong_path(self, tmp_path):
        """Two read failures with the same outer type stay distinguishable."""
        parameter_root = tmp_path / "parameter"
        _work(parameter_root)
        _write_config(parameter_root / "work")
        missing_proc, missing_calls = _launch(
            parameter_root, ["--companies", "missing.txt", "--config", "config.json"],
        )
        assert _exit(missing_proc) == 1 and missing_calls == []
        assert "Traceback" not in _stderr_text(missing_proc)
        parameter_chain = _settlement_detail(parameter_root)["cause_chain"]

        # A directory stands in for a list the process cannot read: exists,
        # but the read itself raises a native OS error.
        io_root = tmp_path / "io"
        _work(io_root)
        _write_config(io_root / "work")
        (io_root / "work" / "list-dir").mkdir()
        io_proc, io_calls = _launch(
            io_root, ["--companies", "list-dir", "--config", "config.json"],
        )
        assert _exit(io_proc) == 1 and io_calls == []
        assert "Traceback" not in _stderr_text(io_proc)
        io_detail = _settlement_detail(io_root)
        assert io_detail["stage"] == "companies"
        assert io_detail["sent"] == "not_sent"
        io_chain = io_detail["cause_chain"]
        assert io_chain[0] == "ConfigError", "one typed entry error for every cause"
        assert io_chain != parameter_chain
        assert len(io_chain) >= 2 and io_chain[1] != "ConfigError"
        assert io_chain[1] in {"PermissionError", "IsADirectoryError", "OSError"}
        first, second = _cold_reconcile_twice(io_root)
        assert first == second
        assert first["result"]["job_status"] == "failed"
        assert first["result"]["cost_state"] == "not_applicable"

    def test_broken_config_keeps_its_native_cause_chain(self, tmp_path):
        _work(tmp_path)
        (tmp_path / "work" / "bad.json").write_text("{", encoding="ascii")
        proc, calls = _launch(tmp_path, ["900001", "--config", "bad.json"])
        assert _exit(proc) == 1 and calls == []
        assert "Traceback" not in _stderr_text(proc)
        detail = _settlement_detail(tmp_path)
        assert detail["stage"] == "config"
        assert detail["sent"] == "not_sent"
        assert detail["attempted"] == 0
        assert detail["cause_chain"][:2] == ["ConfigError", "JSONDecodeError"]
        first, second = _cold_reconcile_twice(tmp_path)
        assert first == second
        assert first["result"]["job_status"] == "failed"
        assert first["result"]["cost_state"] == "not_applicable"

    def test_feedback_unavailable_keeps_the_business_result(self, tmp_path):
        """Diagnostics can never change what the business entry returns."""
        _work(tmp_path)
        config = _write_config(tmp_path / "work")
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("occupied", encoding="ascii")
        proc, calls = _launch(
            tmp_path, ["--companies", "missing.txt", "--config", config.name],
            RESEARCH_FEEDBACK_STATE_ROOT=str(blocker),
        )
        assert _exit(proc) == 1 and calls == []
        assert "Traceback" not in _stderr_text(proc)


# ── the explicit OUT mode reports the same vocabulary ─────────────────────


def test_explicit_out_reports_no_tasks(tmp_path):
    _work(tmp_path)
    out = tmp_path / "out.jsonl"
    config = _write_config(tmp_path / "work")
    proc, calls = _launch(
        tmp_path, ["--config", "config.json"],
        RESEARCH_FEEDBACK_OUT=str(out),
        RESEARCH_FEEDBACK_RUN_ID="host-run", RESEARCH_FEEDBACK_ATTEMPT_ID="host-1",
    )
    assert _exit(proc) == 0 and calls == []
    rows = [row for row in _readback(str(out)) if row.get("run_id") == "host-run"]
    settlement = _settlement(rows)
    assert settlement["actual"] == "no_tasks"
    assert settlement["attempt_id"] == "host-1"
