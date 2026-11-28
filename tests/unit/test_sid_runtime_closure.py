"""Exercise the ordinary downloader and its receipt through an offline DOM."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from tests.native_process_fixture import native_check_output, native_run, native_start


ROOT = Path(__file__).resolve().parents[2]
CHILD = """
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, sys.argv[1])
scenario = sys.argv[2]
import main
from src import constants as C
from src.browser import PlaywrightBrowser
from src.downloader import StockDownloader

class PaginationClickError(RuntimeError):
    pass

class Page:
    number = 1

    def evaluate(self, source):
        if ".btn-prev" in source:
            self.query_selector(".btn-prev").click()
            return None
        return {"current_page": self.number, "total_pages": 2}

    def query_selector(self, selector):
        if selector == C.NEXT_PAGE_CSS:
            destination = 2
            disabled = self.number == 2
        elif selector == C.LAST_PAGE_CSS:
            destination = 2
            disabled = self.number == 2
        elif selector in (".btn-prev", C.PREV_PAGE_CSS):
            destination = 1
            disabled = self.number == 1
        else:
            raise AssertionError(selector)

        def click():
            with Path("clicks.log").open("a") as stream:
                print(destination, file=stream)
            if scenario in {"click-failed", "reverse-failed", "limit"}:
                raise PaginationClickError("synthetic fault under test")
            if scenario != "move-stalled":
                self.number = destination

        return SimpleNamespace(is_disabled=lambda: disabled, click=click)

    def wait_for_function(self, _condition, *, arg, timeout):
        if self.number != arg:
            raise TimeoutError("synthetic page arrival deadline")

page = Page()
browser = PlaywrightBrowser.__new__(PlaywrightBrowser)
browser._page = page
browser.navigate = lambda _: True
browser.close = lambda: None
browser.select_menu_item = lambda _: browser.TAB_ACTIVE
browser.find_active_tab_links = lambda: [(f"https://example.invalid/detail/doc{page.number}", f"Report {page.number}")]
browser.find_elements = lambda *_, **_options: [
    SimpleNamespace(get_attribute=lambda _: href, text_content=lambda: text)
    for href, text in browser.find_active_tab_links()
]
browser.get_attribute = lambda element, name: element.get_attribute(name)
browser.get_text = lambda element: element.text_content()

def download(url, target, timeout=60):
    with Path("calls.log").open("a") as stream:
        print(url.rsplit("/", 1)[-1], file=stream)
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-" + b"x" * (C.MIN_FILE_SIZE + 32))
    return True

browser.download_file = download
StockDownloader.browser = property(lambda _: browser)
StockDownloader.mapping = property(lambda _: SimpleNamespace(get_org_id=lambda *_a, **_kw: "fixture-org"))
main.get_real_stock_name = lambda _: "Fixture Co"
main.time.sleep = lambda *_: None
sys.argv = ["main.py", "300470", "--config", "config.json"]
main.main()
"""


@pytest.mark.parametrize(
    ("scenario", "limit", "reverse", "exit_code", "calls", "outcome"),
    [
        ("normal", 3, False, 0, ["doc1", "doc2"], "all_completed"),
        ("normal", 2, True, 0, ["doc2", "doc1"], "all_completed"),
        ("limit", 1, False, 0, ["doc1"], "all_completed"),
        ("click-failed", 2, False, 1, ["doc1"], "all_failed"),
        ("move-stalled", 2, False, 1, ["doc1"], "all_failed"),
        ("reverse-failed", 2, True, 1, [], "all_failed"),
    ],
)
def test_owner_pagination_settles_the_actual_coverage(tmp_path, scenario, limit, reverse, exit_code, calls, outcome):
    config = {
        "save_dir": str(tmp_path / "downloads"),
        "max_retries": 0,
        "logging": {"level": "DEBUG", "log_to_file": True, "log_file": str(tmp_path / "owner.log")},
        "pages": [{"suffix": "periodicReports", "max_pages": limit, "reverse_order": reverse}],
    }
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "RESEARCH_FEEDBACK_RUN_ID": "sid-paging",
        "RESEARCH_FEEDBACK_ATTEMPT_ID": "try-1",
        "RESEARCH_FEEDBACK_STATE_ROOT": str(tmp_path / "state"),
    }
    python = [sys.executable, "-B", "-X", "utf8"]
    completed = native_run([*python, "-c", CHILD, str(ROOT), scenario], cwd=tmp_path,
                               env=env, capture_output=True, timeout=20, check=False)
    assert completed.returncode == exit_code, completed.stderr.decode("utf-8", errors="replace")
    assert completed.stdout == b""
    assert ("All tasks completed" in completed.stderr.decode("utf-8")) == (exit_code == 0)
    call_log = tmp_path / "calls.log"
    observed_calls = call_log.read_text().splitlines() if call_log.exists() else []
    assert observed_calls == calls
    assert len(list((tmp_path / "downloads").rglob("*.pdf"))) == len(calls)
    if scenario == "limit":
        assert not (tmp_path / "clicks.log").exists()

    query = [*python, "-m", "src.feedback_publish", "reconcile", "--json"]
    first, second = (json.loads(native_check_output(query, cwd=tmp_path, env=env, timeout=20)) for _ in range(2))
    assert first == second
    receipt, = first["receipts"]
    assert (receipt["run_id"], receipt["attempt_id"]) == ("sid-paging", "try-1")
    assert receipt["terminal"] == {"result": outcome, "exit_code": exit_code}
    checkpoints = receipt["checkpoints"]
    assert all(record["step_id"] and record["observed_at"] for record in checkpoints)
    if exit_code:
        failure, = [record for record in checkpoints if record.get("error_code") == "pagination_failed"]
        assert failure["page"] == 1 and failure["files_confirmed"] == len(calls)
        origin = "TimeoutError" if scenario == "move-stalled" else "PaginationClickError"
        assert failure["cause_types"][-1] == origin
    if calls:
        confirmed = [record for record in checkpoints if record["stage"] == "download" and
                     record["executed_state"] == "confirmed"]
        assert len(confirmed) == len(calls)
        assert (tmp_path / "calls.log").read_text().splitlines() == calls


def _adapter_environment(tmp_path):
    return {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "PYTHONUTF8": "1",
        "RESEARCH_FEEDBACK_RUN_ID": "sid-native",
        "RESEARCH_FEEDBACK_ATTEMPT_ID": "try-2",
        "RESEARCH_FEEDBACK_STATE_ROOT": str(tmp_path / "state"),
    }


def test_adapter_has_an_original_run_before_it_waits_for_stdin(tmp_path):
    config = tmp_path / "sid.json"
    config.write_text('{"logging":{"log_to_file":false}}', encoding="utf-8")
    env = _adapter_environment(tmp_path)
    command = [sys.executable, "-B", "-m", "src.company_wiki_adapter_cli", "discover", "--config", str(config)]
    child = native_start(command, cwd=tmp_path, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        journal = tmp_path / "state" / "runs" / "sid-native__try-2.jsonl"
        deadline = time.monotonic() + 15
        while "awaiting_input" not in (journal.read_text(encoding="utf-8") if journal.is_file() else ""):
            assert child.poll() is None and time.monotonic() < deadline, "start receipt was missing while stdin waited"
            time.sleep(0.03)
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=10)
    inspect = [sys.executable, "-B", "-m", "src.feedback_publish", "reconcile", "--json"]
    first, second = (json.loads(native_check_output(inspect, cwd=tmp_path, env=env, timeout=15))
                     for _ in range(2))
    assert first == second
    receipt, = first["receipts"]
    assert receipt["terminal"] is None
    assert receipt["implementation"].startswith("src-")
    step = receipt["checkpoints"][-1]
    assert (step["stage"], step["sent"]) == ("payload", "not_sent")


def test_adapter_stdin_failure_remains_on_original_run(tmp_path):
    config = tmp_path / "sid.json"
    config.write_text('{"logging":{"log_to_file":false}}', encoding="utf-8")
    env = _adapter_environment(tmp_path)
    script = """
import sys
from src.company_wiki_adapter_cli import main
class BrokenInput:
    def read(self):
        raise OSError(5, "isolated synthetic read failure")
sys.stdin = BrokenInput()
raise SystemExit(main(["discover", "--config", sys.argv[1]]))
"""
    python = [sys.executable, "-B", "-X", "utf8"]
    completed = native_run([*python, "-c", script, str(config)], cwd=tmp_path, env=env,
                               capture_output=True, check=False, timeout=15)
    assert completed.returncode == 1 and completed.stdout == b""
    assert json.loads(completed.stderr)["error"]["type"] == "OSError"
    cold = json.loads(native_check_output(
        [*python, "-m", "src.feedback_publish", "reconcile", "--json"],
        cwd=tmp_path, env=env, timeout=15,
    ))
    receipt, = cold["receipts"]
    assert (receipt["run_id"], receipt["attempt_id"]) == ("sid-native", "try-2")
    assert receipt["terminal"] == {"result": "failed", "exit_code": 1}
    row, = [record for record in receipt["checkpoints"] if record["executed_state"] == "failed"]
    assert row["sent"] == "not_sent" and row["cause_types"] == ["OSError"]
    assert b"isolated synthetic read failure" not in json.dumps(cold).encode()


def test_unavailable_adapter_diagnostics_do_not_replace_the_wire_result(tmp_path):
    log_target = tmp_path / "log-target"
    log_target.mkdir()
    (tmp_path / "state").touch()
    sidecar = tmp_path / "observations.jsonl"
    sidecar.mkdir()
    config = tmp_path / "sid.json"
    config.write_text(json.dumps({"logging": {"log_file": str(log_target)}}), encoding="utf-8")
    env = {**_adapter_environment(tmp_path), "RESEARCH_FEEDBACK_OUT": str(sidecar)}
    argv = [sys.executable, "-B", "-m", "src.company_wiki_adapter_cli", "discover", "--config", str(config)]
    failed = native_run(argv, input=b'{"entity":"Synthetic"}', cwd=tmp_path, env=env,
                            capture_output=True, check=False, timeout=15)
    assert failed.returncode == 1 and failed.stdout == b""
    lines = failed.stderr.splitlines()
    assert b"diagnostics unavailable" in lines[0] and b"sid-native" in lines[0] and b"try-2" in lines[0]
    assert json.loads(lines[-1])["error"]["message"] == "security_id is required for CN discovery"
    assert str(tmp_path).encode() not in lines[0]


def test_adapter_records_actual_page_observation_and_preserves_the_wire(tmp_path):
    config = tmp_path / "sid.json"
    config.write_text('{"logging":{"log_to_file":false}}', encoding="utf-8")
    env = _adapter_environment(tmp_path)
    script = """
import json, sys
from src.cninfo_api import CninfoAnnouncementClient
from src.company_wiki_adapter_cli import main
def post(self, body, *, budget):
    assert b"pageNum=1" in body
    return {"totalRecordNum": 0, "announcements": [], "hasMore": False, "totalpages": 0}
CninfoAnnouncementClient._post_json = post
raise SystemExit(main(["discover", "--config", sys.argv[1]]))
"""
    payload = {
        "entity": "Synthetic Co", "security_id": "600000", "document_kind": "annual_report",
        "fiscal_year": 2025, "org_id": "test-org",
    }
    python = [sys.executable, "-B", "-X", "utf8"]
    completed = native_run([*python, "-c", script, str(config)], cwd=tmp_path, env=env,
                               input=json.dumps(payload).encode(), capture_output=True, check=False, timeout=15)
    assert completed.returncode == 0 and completed.stderr == b""
    assert json.loads(completed.stdout)["candidates"] == []
    cold = json.loads(native_check_output(
        [*python, "-m", "src.feedback_publish", "reconcile", "--json"], cwd=tmp_path, env=env, timeout=15,
    ))
    receipt, = cold["receipts"]
    assert receipt["terminal"] == {"result": "completed", "exit_code": 0}
    actual = [row for row in receipt["checkpoints"] if row["stage"] == "announcement-page"]
    assert [(row["executed_state"], row["page"], row["sent"]) for row in actual] == [
        ("dispatching", 1, "unknown"), ("observed", 1, "sent"),
    ]
    assert actual[0]["step_id"] == actual[1]["step_id"] and actual[1]["candidate_count"] == 0


@pytest.mark.parametrize("staging_fails", [False, True])
def test_browser_document_transport_uses_its_own_page_and_does_not_retry_a_confirmed_response(
    tmp_path, staging_fails,
):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from src import constants as C
    from src.browser import PlaywrightBrowser

    calls = []

    class DocumentPage:
        @contextmanager
        def expect_download(self, **_options):
            calls.append("expect")
            yield SimpleNamespace(value=SimpleNamespace(save_as=self.save_as))

        def goto(self, _url, **_options):
            calls.append("goto")

        def save_as(self, target):
            Path(target).write_bytes(b"%PDF-" + b"x" * (C.MIN_FILE_SIZE + 32))
            if staging_fails:
                raise PermissionError("isolated staging fault")

        def close(self):
            calls.append("close")

    listing_page = object()
    browser = object.__new__(PlaywrightBrowser)
    browser._page = listing_page
    browser._context = SimpleNamespace(new_page=DocumentPage)
    target = tmp_path / "final.pdf"
    try:
        outcome = browser.download_file("https://example.invalid/detail/doc1", str(target))
    except Exception as error:
        assert staging_fails
        assert error.phase == "staging" and error.sent == "sent"
        assert type(error.__cause__) is PermissionError
        assert list(tmp_path.iterdir()) == []
    else:
        assert not staging_fails and outcome is True
        assert target.is_file()
    assert browser.page is listing_page
    assert calls == ["expect", "goto", "close"]
