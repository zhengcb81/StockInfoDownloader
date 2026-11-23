"""MB-SID runtime artifact check — the delivered CLI in a browser-free tree.

The card has no installer for this repo, so the runtime is an explicit
manifest: the transitive closure of ``src.company_wiki_adapter_cli`` is copied
to a scratch artifact directory, an empty working directory runs
``python -m src.company_wiki_adapter_cli`` with only that artifact root on the
import path, and a ``sitecustomize`` double serves the HTTP fixtures.

Nothing here touches the real checkout's imports, the browser layer, the
downloader, or a real network.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.provider_runtime_fixture import RUNTIME_FILES, copy_runtime

WORKTREE = Path(__file__).resolve().parents[2]
FIXTURE_JSON = WORKTREE / "tests" / "fixtures" / "cninfo" / "byd_fy2024_announcement.json"

PDF_BODY = b"%PDF-1.4\n" + b"mb11-sid-artifact-check\n" * 64

CANDIDATE = {
    "candidate_id": "cninfo:1222881505",
    "provider": "cninfo",
    "provider_document_id": "1222881505",
    "identity_method": "announcement_id",
    "market": "CN",
    "entity": "002594",
    "title": "比亚迪2024年年度报告",
    "source_url": (
        "https://www.cninfo.com.cn/new/disclosure/detail?announcementId=1222881505"
    ),
    "document_kind": "annual_report",
    "form_type": "annual_report",
    "filing_date": "2025-03-25",
    "fiscal_year": 2024,
    "fiscal_period": "FY",
    "language": "zh-CN",
    "amended": False,
    "transport_url": "https://static.cninfo.com.cn/finalpage/2025-03-25/1222881505.PDF",
}

_SITECUSTOMIZE = '''
"""HTTP double injected through PYTHONPATH; the artifact stays untouched."""

import json
import os
import urllib.request

_MODE = os.environ.get("SID_FIXTURE_MODE", "ok")
_LOG = os.environ.get("SID_FIXTURE_LOG")
_IDENTITY = os.environ.get("SID_IDENTITY_JSON", "{}").encode("utf-8")
_ANNOUNCEMENT = os.environ.get("SID_ANNOUNCEMENT_JSON", "{}").encode("utf-8")
_PDF = os.environ.get("SID_PDF_PATH")


class _Body:
    def __init__(self, body, content_type):
        self._body = body
        self._offset = 0
        self.status = 200
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(body))}

    def read(self, size=-1):
        if size < 0:
            chunk = self._body[self._offset:]
        else:
            chunk = self._body[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _log(kind):
    if not _LOG:
        return
    with open(_LOG, "a", encoding="utf-8") as stream:
        stream.write(kind + "\\n")


def _urlopen(request, *args, **kwargs):
    data = getattr(request, "data", None)
    if data:
        body = data.decode("utf-8", "replace")
        if "searchkey" in body:
            _log("identity")
            return _Body(_IDENTITY, "application/json")
        _log("announcement")
        return _Body(_ANNOUNCEMENT, "application/json")
    _log("pdf")
    payload = b""
    if _PDF:
        with open(_PDF, "rb") as stream:
            payload = stream.read()
    if _MODE == "bad_pdf":
        return _Body(b"<html>challenge</html>" + b"x" * 512, "application/pdf")
    return _Body(payload, "application/pdf")


urllib.request.urlopen = _urlopen
'''


@pytest.fixture()
def artifact(tmp_path):
    root = tmp_path / "artifact"
    copy_runtime(root)

    doubles = tmp_path / "doubles"
    doubles.mkdir()
    (doubles / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")

    empty_cwd = tmp_path / "cwd"
    empty_cwd.mkdir()
    return root, doubles, empty_cwd


def _env(artifact_root, doubles, **extra):
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PYTHONHOME", "SID_FIXTURE_MODE"}
        and not k.upper().startswith("RESEARCH_FEEDBACK_")
    }
    env["PYTHONPATH"] = os.pathsep.join([str(doubles), str(artifact_root)])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # The parent sends UTF-8 JSON over stdin; make the isolated child decode
    # that protocol consistently on Windows hosts whose locale is GBK/CP936.
    env["PYTHONUTF8"] = "1"
    env.update({k: str(v) for k, v in extra.items()})
    return env


def _run(artifact_root, doubles, empty_cwd, argv, payload, **extra):
    return subprocess.run(
        [sys.executable, "-B", "-m", "src.company_wiki_adapter_cli", *argv],
        cwd=str(empty_cwd),
        env=_env(artifact_root, doubles, **extra),
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )


def _write_config(empty_cwd: Path) -> Path:
    config = empty_cwd / "config.json"
    config.write_text(
        json.dumps(
            {
                "save_dir": str(empty_cwd / "downloads"),
                "max_retries": 1,
                "headless": True,
                "logging": {"level": "WARNING", "log_to_file": False},
                "pages": [],
                "companies": [],
                "test_cases": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return config


def test_artifact_runtime_has_no_browser_or_downloader_modules(artifact):
    artifact_root, _doubles, _cwd = artifact

    present = {path.name for path in (artifact_root / "src").iterdir()}
    assert "browser.py" not in present
    assert "downloader.py" not in present
    assert "mapping.py" not in present
    assert "models.py" not in present


@pytest.mark.parametrize("feedback_mode", ["default", "enabled", "unwritable", "invalid_context"])
def test_artifact_discover_and_fetch_work_from_an_empty_cwd(
    artifact, tmp_path, feedback_mode
):
    artifact_root, doubles, empty_cwd = artifact
    config = _write_config(empty_cwd)
    staging = tmp_path / "staging"
    request_log = tmp_path / "requests.log"
    pdf_path = tmp_path / "payload.pdf"
    pdf_path.write_bytes(PDF_BODY)

    fixture = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    identity = {
        "totalRecordNum": 1,
        "totalpages": 1,
        "hasMore": False,
        "announcements": [
            {
                "announcementId": "1222881505",
                "announcementTime": 1742832000000,
                "announcementTitle": "比亚迪2024年年度报告",
                "secCode": "002594",
                "secName": "比亚迪",
                "orgId": "gshk0001211",
                "adjunctType": "PDF",
                "adjunctUrl": "finalpage/2025-03-25/1222881505.PDF",
            }
        ],
    }
    common = {
        "SID_FIXTURE_LOG": request_log,
        "SID_IDENTITY_JSON": json.dumps(identity, ensure_ascii=False),
        "SID_ANNOUNCEMENT_JSON": json.dumps(fixture, ensure_ascii=False),
        "SID_PDF_PATH": pdf_path,
        "RESEARCH_FEEDBACK_STATE_ROOT": tmp_path / "state",
    }

    discover_out = tmp_path / "discover-observations.jsonl"
    fetch_out = tmp_path / "fetch-observations.jsonl"
    if feedback_mode == "unwritable":
        discover_out.mkdir()
        fetch_out.mkdir()
    discover_feedback = (
        {"RESEARCH_FEEDBACK_OUT": discover_out} if feedback_mode != "default" else {}
    )
    fetch_feedback = (
        {"RESEARCH_FEEDBACK_OUT": fetch_out} if feedback_mode != "default" else {}
    )

    if feedback_mode == "invalid_context":
        discover_feedback["RESEARCH_FEEDBACK_RUN_ID"] = "not/a/logical/id"
        fetch_feedback["RESEARCH_FEEDBACK_RUN_ID"] = "not/a/logical/id"

    discover = _run(
        artifact_root,
        doubles,
        empty_cwd,
        ["discover", "--config", str(config)],
        {
            "entity": "比亚迪",
            "market": "CN",
            "security_id": "002594",
            "document_kind": "annual_report",
            "fiscal_year": 2024,
            "acquisition_budget": {
                "schema_version": "1.0",
                "max_response_bytes": 200000,
                "timeout_seconds": 30,
                "max_cost_usd": "0",
            },
        },
        **common,
        **discover_feedback,
    )

    assert discover.returncode == 0, discover.stderr
    discovered = json.loads(discover.stdout)
    assert discovered["status"] == "ok"
    assert discovered["candidates"], "the fixture must yield the 2024 annual report"
    assert discovered["acquisition_usage"]["response_bytes"] > 0
    # Only the protocol document reached stdout.
    assert discover.stdout.count("\n") <= 1
    # Discover writes nothing but the caller's staging area (which it never got).
    assert list(empty_cwd.rglob("*.pdf")) == []
    assert not staging.exists()

    fetch = _run(
        artifact_root,
        doubles,
        empty_cwd,
        ["fetch", "--staging-dir", str(staging), "--config", str(config)],
        {
            **CANDIDATE,
            "adapter_payload_json": json.dumps(CANDIDATE, ensure_ascii=False),
            "acquisition_budget": {
                "schema_version": "1.0",
                "max_response_bytes": 200000,
                "timeout_seconds": 30,
                "max_cost_usd": "0",
            },
        },
        **common,
        **fetch_feedback,
    )

    assert fetch.returncode == 0, fetch.stderr
    receipt = json.loads(fetch.stdout)["receipt"]
    assert receipt["content_sha256"] == hashlib.sha256(PDF_BODY).hexdigest()
    assert receipt["byte_size"] == len(PDF_BODY)
    staged = sorted(path.name for path in staging.iterdir())
    assert staged == [Path(receipt["staged_path"]).name]
    assert list(staging.glob("*.part")) == []
    if feedback_mode == "enabled":
        for path, check, expected in (
            (discover_out, "candidate-listing-identity", "verified"),
            (fetch_out, "staged-fetch-receipt", "staged"),
        ):
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            assert all(item["schema_version"] == "feedback-observation/1" for item in events)
            identities = {(item["step_id"], item["check_id"]) for item in events}
            assert len(identities) == len(events), events
            assert any(item["check_id"] == "action-started" and
                       item["disposition"] == "expected" for item in events), events
            assert any(item["check_id"] == check and item["actual"] == expected
                       for item in events), events
            assert any(item["check_id"] == "acquisition-budget" and
                       item["actual"] == "within_budget" for item in events), events
    elif feedback_mode in {"default", "invalid_context"}:
        assert not discover_out.exists() and not fetch_out.exists()
        assert not Path(str(discover_out) + ".details.jsonl").exists()
        assert not Path(str(fetch_out) + ".details.jsonl").exists()
        inbox = tmp_path / "state" / "observations"
        markers = [json.loads(path.read_bytes()) for path in inbox.glob("*.ready")]
        if feedback_mode == "default":
            assert {row["check_id"] for row in markers} >= {
                "candidate-listing-identity", "staged-fetch-receipt", "action-started",
            }
            assert all(row["schema_version"] == "sid-ready/1" for row in markers)
        else:
            assert not markers

    # The artifact tree itself stayed read-only.
    assert sorted(p.name for p in (artifact_root / "src").iterdir()) == sorted(
        RUNTIME_FILES
    )


def test_discovery_steps_separate_sibling_periods_and_keep_replay_identity(artifact, tmp_path):
    artifact_root, doubles, empty_cwd = artifact
    config = _write_config(empty_cwd)
    fixture = json.loads(FIXTURE_JSON.read_text(encoding="utf-8"))
    request = {
        "entity": "比亚迪",
        "market": "CN",
        "security_id": "002594",
        "document_kind": "annual_report",
        "org_id": "gshk0001211",
        "acquisition_budget": {
            "schema_version": "1.0", "max_response_bytes": 200000,
            "timeout_seconds": 30, "max_cost_usd": "0",
        },
    }
    checks_by_call = []
    for index, year in enumerate((2024, 2023, 2024)):
        sidecar = tmp_path / f"period-{index}.jsonl"
        payload = {**request, "fiscal_year": year}
        if index == 2:
            payload = dict(reversed(list(payload.items())))
        result = _run(
            artifact_root, doubles, empty_cwd, ["discover", "--config", str(config)],
            payload,
            SID_ANNOUNCEMENT_JSON=json.dumps(fixture, ensure_ascii=False),
            RESEARCH_FEEDBACK_OUT=sidecar,
            RESEARCH_FEEDBACK_RUN_ID="sibling-discovery",
            RESEARCH_FEEDBACK_ATTEMPT_ID="try-1",
        )
        assert result.returncode == 0, result.stderr
        candidates = json.loads(result.stdout)["candidates"]
        assert candidates and {row["fiscal_year"] for row in candidates} == {year}
        observations = [json.loads(line) for line in sidecar.read_text(encoding="utf-8").splitlines()]
        assert {row["check_id"] for row in observations} == {
            "action-started", "candidate-listing-identity", "acquisition-budget",
        }
        checks_by_call.append({(row["step_id"], row["check_id"]) for row in observations})
    assert checks_by_call[0].isdisjoint(checks_by_call[1])
    assert checks_by_call[0] == checks_by_call[2]


def test_artifact_fetch_failure_leaves_no_part_file(artifact, tmp_path):
    artifact_root, doubles, empty_cwd = artifact
    config = _write_config(empty_cwd)
    staging = tmp_path / "staging"

    result = _run(
        artifact_root,
        doubles,
        empty_cwd,
        ["fetch", "--staging-dir", str(staging), "--config", str(config)],
        {
            **CANDIDATE,
            "adapter_payload_json": json.dumps(CANDIDATE, ensure_ascii=False),
        },
        SID_FIXTURE_MODE="bad_pdf",
    )

    assert result.returncode == 1
    assert result.stdout == ""
    error = json.loads(result.stderr.strip().splitlines()[-1])["error"]
    assert error["code"] == "pdf_magic_invalid"
    assert error["retryable"] is False
    assert list(staging.glob("*.part")) == []
    assert list(staging.glob("*.pdf")) == []
