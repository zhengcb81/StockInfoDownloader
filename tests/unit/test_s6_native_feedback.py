"""Native S6 feedback contracts with real stdin, stdout and stderr."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from tests.native_process_fixture import native_run, native_start

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.regression
SECRET = "sk-fixtureS6StandaloneToken"
HOST_ENV = {
    "PATH", "PATHEXT", "COMSPEC", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE",
    "TMP", "TEMP", "TMPDIR", "LD_LIBRARY_PATH",
}
ENTRYPOINTS = {
    "ordinary": [str(ROOT / "main.py")],
    "adapter": ["-m", "src.company_wiki_adapter_cli"],
    "feedback-owner": ["-m", "src.feedback_owner"],
    "feedback-publish": ["-m", "src.feedback_publish"],
}


@pytest.fixture()
def offline(tmp_path):
    guard = tmp_path / "offline"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import sys\n"
        "def no_network(event, args):\n"
        "    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):\n"
        "        raise AssertionError('S6 offline fixture')\n"
        "sys.addaudithook(no_network)\n",
        encoding="utf-8",
    )
    env = {key: value for key, value in os.environ.items() if key.upper() in HOST_ENV}
    env.update(
        PYTHONPATH=os.pathsep.join((str(guard), str(ROOT))),
        PYTHONUTF8="1",
        HOME=str(tmp_path),
        USERPROFILE=str(tmp_path),
        RESEARCH_FEEDBACK_STATE_ROOT=str(tmp_path / "state"),
        RESEARCH_FEEDBACK_OUT=str(tmp_path / "observations.jsonl"),
        RESEARCH_FEEDBACK_RUN_ID="s6-native-log",
        RESEARCH_FEEDBACK_ATTEMPT_ID="bad-input",
    )
    return env


def _entry(entry, *args):
    return [sys.executable, "-B", *ENTRYPOINTS[entry], *map(str, args)]


@pytest.mark.parametrize("entry", ENTRYPOINTS)
def test_parse_refusal_has_a_safe_correlated_native_log(tmp_path, offline, entry):
    result = native_run(
        _entry(entry, f"--unknown-{SECRET}", "bad"), cwd=tmp_path, env=offline,
        capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 2 and not result.stdout
    assert b"usage:" in result.stderr and SECRET.encode() not in result.stderr
    content = (tmp_path / "state" / "logs" / f"{entry}.log").read_text(encoding="utf-8")
    assert "s6-native-log" in content and "bad-input" in content
    assert "arguments" in content and "SystemExit" in content
    assert "entry=" + entry in content and re.search(r"code_version=src-[a-f0-9]{64}", content)
    assert SECRET not in content and str(tmp_path) not in content


def test_owner_machine_refusal_preserves_wire_and_root_error(tmp_path, offline):
    result = native_run(
        _entry("feedback-owner", "--db", tmp_path / "owner.sqlite", "reconcile"),
        cwd=tmp_path, env=offline, input=f'{{"private":"{SECRET}",'.encode(),
        capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr) == {"error": "sid_feedback_action_rejected"}
    assert not (tmp_path / "owner.sqlite").exists()
    content = (tmp_path / "state" / "logs" / "feedback-owner.log").read_text(encoding="utf-8")
    assert "s6-native-log" in content and "bad-input" in content
    assert "reconcile" in content and "JSONDecodeError" in content
    assert re.search(r"feedback_owner[.]py:\d+", content)
    assert SECRET not in content


def test_owner_dual_sink_failure_warns_without_invalidating_last_wire_line(tmp_path, offline):
    state = tmp_path / "state"
    state.write_text("preserve", encoding="utf-8")
    (tmp_path / "observations.jsonl").mkdir()
    result = native_run(
        _entry("feedback-owner", "--db", tmp_path / "owner.sqlite", "reconcile"),
        cwd=tmp_path, env=offline, input=b"{", capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 2 and not result.stdout
    lines = result.stderr.splitlines()
    assert json.loads(lines[-1]) == {"error": "sid_feedback_action_rejected"}
    assert any(b"diagnostics unavailable" in line and b"s6-native-log" in line for line in lines[:-1])
    assert state.read_text(encoding="utf-8") == "preserve"
    assert not (tmp_path / "owner.sqlite").exists()


def test_parallel_native_rotation_keeps_all_records_and_filters_credentials(tmp_path, offline):
    log_dir = tmp_path / "#owner%" / ("p" * 80) / ("q" * 80) / ("r" * 80)
    from src.feedback_files import native_path

    native_path(log_dir).mkdir(parents=True)
    target = log_dir / "diagnostics.log"
    script = '''
import sys
from src.logger import setup_logger
logger = setup_logger(console=False, log_file=sys.argv[1], max_bytes=1024, backup_count=45)
for index in range(80):
    logger.warning(
        "observed-%s-%03d Basic Zml4dHVyZTp0b2tlbg== sk-fixtureS6StandaloneToken "
        "tvly-fixtureS6Standalone ghp_fixtureS6Standalone AIzaFixtureS6Standalone",
        sys.argv[2], index,
    )
'''
    children = [
        native_start(
            [sys.executable, "-B", "-c", script, str(target), label], cwd=tmp_path,
            env=offline, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        for label in ("one", "two")
    ]
    try:
        for child in children:
            stdout, stderr = child.communicate(timeout=20)
            assert child.returncode == 0, stderr
            assert not stdout and not stderr
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate()
    paths = [
        path for path in native_path(log_dir).glob("diagnostics.log*")
        if path.name == "diagnostics.log" or path.suffix[1:].isdigit()
    ]
    assert len(paths) > 1
    content = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert sorted(re.findall(r"observed-(?:one|two)-[0-9]{3}", content)) == [
        f"observed-{label}-{index:03d}" for label in ("one", "two") for index in range(80)
    ]
    for value in (
        "Zml4dHVyZTp0b2tlbg==", SECRET, "tvly-fixtureS6Standalone",
        "ghp_fixtureS6Standalone", "AIzaFixtureS6Standalone",
    ):
        assert value not in content



def test_failed_download_record_writes_redacted_legacy_shape(tmp_path, offline):
    path = tmp_path / "failed.json"
    source = r'''
from src.downloader import FailedDownloadLogger
import sys
sink = FailedDownloadLogger(sys.argv[1])
sink.record("600000", "Synthetic", "Fixture",
            "https://fixture-user:fixture-password@localhost/report.pdf?token=fixture-secret",
            "Authorization: Basic\n\tZml4dHVyZTp0b2tlbg== request sk-fixtureS6StandaloneToken")
sink.flush()
'''
    result = native_run(
        [sys.executable, "-B", "-c", source, str(path)], cwd=tmp_path,
        env=offline, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    content = path.read_text(encoding="utf-8")
    record, = json.loads(content)
    assert {"timestamp", "stock_code", "stock_name", "file_name", "url", "error"} == set(record)
    assert record["stock_code"] == "600000" and "localhost/report.pdf" in record["url"]
    for value in ("fixture-user", "fixture-password", "fixture-secret", "Zml4dHVyZTp0b2tlbg==", SECRET):
        assert value not in content


def test_rotation_survives_a_real_reader_holding_the_active_file(tmp_path, offline):
    path = tmp_path / "held.log"
    before = "held-prior " + "x" * 100 + "\n"
    path.write_bytes(before.encode())
    source = '''
import sys
from src.logger import setup_logger
logger = setup_logger(console=False, log_file=sys.argv[1], max_bytes=100, backup_count=3)
logger.warning("written-while-held")
'''
    with path.open("rb") as reader:
        result = native_run([sys.executable, "-B", "-c", source, str(path)], cwd=tmp_path,
                            env=offline, capture_output=True, timeout=15)
        assert not result.stdout and not result.stderr and result.returncode == 0
        assert reader.read().startswith(before.encode())
        if os.name == "nt":
            assert path.read_bytes().startswith(before.encode())
    contents = "\n".join(
        file.read_text(encoding="utf-8")
        for file in tmp_path.glob("held.log*")
        if file.suffix in (".log", ".1", ".2", ".3")
    )
    assert contents.count("held-prior") == 1 and contents.count("written-while-held") == 1


def test_native_truncated_body_keeps_sent_and_cold_reconcile_read_only(tmp_path, offline):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from tests.unit.test_provider_runtime_artifact import CANDIDATE

    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "15000")
            self.send_header("Content-Type", "application/pdf")
            self.end_headers()
            self.wfile.write(b"%PDF-" + b"x" * 1000)

    config = tmp_path / "config.json"
    log_path = tmp_path / "configured.log"
    config.write_text(json.dumps({
        "save_dir": str(tmp_path / "raw"),
        "logging": {"log_file": str(log_path)},
    }), encoding="utf-8")
    staging = tmp_path / "stage"
    staging.mkdir()
    old = staging / "preserved.pdf"
    old.write_bytes(b"%PDF-old")
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            bootstrap = ROOT / "tests" / "fixtures" / "g5_provider"
            native_env = {**offline, "PYTHONPATH": os.pathsep.join((str(bootstrap), str(ROOT))),
                          "G5_LOOPBACK": f"http://127.0.0.1:{server.server_port}"}
            result = native_run(
                _entry("adapter", "fetch", "--config", config, "--staging-dir", staging),
                cwd=tmp_path, env=native_env, input=json.dumps({
                    "adapter_payload_json": json.dumps(CANDIDATE),
                    "acquisition_budget": {"schema_version": "1.0", "max_response_bytes": 20000,
                                           "timeout_seconds": 5, "max_cost_usd": "0"},
                }).encode(),
                capture_output=True, timeout=15,
            )
            assert result.returncode == 1 and not result.stdout
            assert json.loads(result.stderr.splitlines()[-1])["error"]["code"] == "upstream_unavailable"
            assert len(calls) == 1 and calls[0].endswith(".PDF")
            content = log_path.read_text(encoding="utf-8")
            assert "phase=transport sent=sent" in content
            assert "CninfoApiError" in content and "AdapterError" in content
            assert re.search(r"cninfo_api[.]py:\d+ _copy_response", content)
            assert old.read_bytes() == b"%PDF-old" and list(staging.iterdir()) == [old]
            reconciled = native_run(
                _entry("feedback-publish", "reconcile", "--json"), cwd=tmp_path, env=offline,
                capture_output=True, timeout=15,
            )
            assert reconciled.returncode == 0, reconciled.stderr
            report = json.loads(reconciled.stdout)
            assert report["receipts"] and "s6-native-log" in reconciled.stdout.decode()
            assert len(calls) == 1  # Neither retry nor another provider transport on cold reconcile.
        finally:
            server.shutdown()
            thread.join()



@pytest.mark.parametrize("after_dispatch", [False, True], ids=["waiting-input", "headers-received"])
def test_force_stop_is_cold_readable_without_new_transport(tmp_path, offline, after_dispatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Event, Thread
    from time import monotonic, sleep
    from tests.unit.test_provider_runtime_artifact import CANDIDATE

    releases = Event()
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", "15000")
            self.end_headers()
            self.wfile.flush()
            releases.wait(15)

    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")
    stage = tmp_path / "stage"
    run_dir = tmp_path / "state" / "runs"
    run_file = run_dir / "s6-native-log__bad-input.json"
    checkpoint_file = run_file.with_suffix(".jsonl")
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            bootstrap = ROOT / "tests" / "fixtures" / "g5_provider"
            env = {**offline, "PYTHONPATH": os.pathsep.join((str(bootstrap), str(ROOT))),
                   "G5_LOOPBACK": f"http://127.0.0.1:{server.server_port}"}
            child = native_start(
                _entry("adapter", "fetch", "--config", config, "--staging-dir", stage),
                cwd=tmp_path, env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            try:
                if after_dispatch:
                    child.stdin.write(json.dumps({
                        "adapter_payload_json": json.dumps(CANDIDATE),
                    }).encode())
                    child.stdin.close()
                expected = "headers_received" if after_dispatch else "awaiting_input"
                deadline = monotonic() + 12
                while monotonic() < deadline:
                    if checkpoint_file.exists() and expected in checkpoint_file.read_text(encoding="utf-8"):
                        break
                    if child.poll() is not None:
                        pytest.fail(f"native child exited before the {expected} checkpoint")
                    sleep(0.02)
                else:
                    pytest.fail(f"native child did not record the {expected} checkpoint")
                assert child.poll() is None
                child.kill()
                child.wait(timeout=10)
                assert child.returncode != 0
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
                for pipe in (child.stdin, child.stdout, child.stderr):
                    pipe.close()
            releases.set()
            first = run_file.read_bytes()
            before_calls = tuple(calls)
            assert len(before_calls) == int(after_dispatch)
            readback = native_run(
                _entry("feedback-publish", "reconcile", "--json"),
                cwd=tmp_path, env=offline, capture_output=True, timeout=15,
            )
            assert readback.returncode == 0, readback.stderr
            receipt, = json.loads(readback.stdout)["receipts"]
            assert (receipt["run_id"], receipt["attempt_id"], receipt["terminal"]) == (
                "s6-native-log", "bad-input", None,
            )
            assert any(row["executed_state"] == expected for row in receipt["checkpoints"])
            assert run_file.read_bytes() == first
            if after_dispatch:
                from tests.unit.test_feedback_owner import OWNER, occurrence, request

                sidecar = tmp_path / "observations.jsonl"
                started, = [row for row in map(json.loads, sidecar.read_text(encoding="utf-8").splitlines())
                            if row["check_id"] == "action-started"]
                started = {"origin_owner": OWNER, **started}
                occurrence_id = occurrence(started)
                action = request("reconcile", {"observation": started, "occurrence_id": occurrence_id}, [occurrence_id])
                db = tmp_path / "owner.sqlite"
                check = native_run(
                    _entry("feedback-owner", "--db", db, "--sidecar", sidecar, "reconcile"),
                    cwd=tmp_path, env=offline, input=json.dumps(action).encode(),
                    capture_output=True, timeout=15,
                )
                assert check.returncode == 0, check.stderr
                assert json.loads(check.stdout)["result"] == {
                    "status": "cost_unknown", "cost_state": "unknown", "job_status": "unconfirmed",
                    "evidence_ref": f"sid-occurrence:{occurrence_id}",
                }
                assert not db.exists()
            assert tuple(calls) == before_calls
            assert not list(stage.glob("*.pdf"))
        finally:
            releases.set()
            server.shutdown()
            thread.join()



def test_held_archive_resumes_once_without_repeating_prior_shifts(tmp_path, offline):
    path = tmp_path / "archive.log"
    path.write_bytes(b"old-active " + b"x" * 1050 + b"\n")
    for index in range(1, 4):
        (tmp_path / f"archive.log.{index}").write_bytes(f"old-archive-{index}\n".encode())

    source = '''
import sys
from src.logger import setup_logger
logger = setup_logger(console=False, log_file=sys.argv[1], max_bytes=1024, backup_count=4)
for field in sys.argv[2:]:
    logger.warning("native-%s", field)
'''

    def child(*labels):
        result = native_run([sys.executable, "-B", "-c", source, str(path), *labels],
                            cwd=tmp_path, env=offline, capture_output=True, timeout=15)
        assert result.returncode == 0 and not result.stdout and not result.stderr

    with (tmp_path / "archive.log.1").open("rb") as held:
        child("while-1", "while-2", "while-3")
        assert held.read() == b"old-archive-1\n"
    child("after-release")
    assert not list(tmp_path.glob("archive.log.rotating.*"))
    content = "\n".join(file.read_text(encoding="utf-8") for file in tmp_path.glob("archive.log*")
                        if file.suffix != ".lock")
    for message in (
        "old-active", "old-archive-1", "old-archive-2", "old-archive-3",
        "native-while-1", "native-while-2", "native-while-3", "native-after-release",
    ):
        assert content.count(message) == 1
