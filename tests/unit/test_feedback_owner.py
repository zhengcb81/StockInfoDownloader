"""CLI recovery using the native BYD announcement fixture and runtime."""

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

from tests.native_process_fixture import native_run

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/feedback_observation/listing_identity_rows.json"
OWNER = "stockinfo-dl-simple"
PRODUCE = """
import json
import os
from pathlib import Path
from unittest.mock import patch
import sys
from src.cninfo_api import CninfoAnnouncementClient
from src.company_wiki_adapter import DisclosureCandidate
from src.company_wiki_adapter_cli import main
fixture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raw = list(fixture["announcements"])
if sys.argv[3] == "multiple":
    first = raw[0]
    raw.append({**first, "announcementId": "1222881997",
                "adjunctUrl": "finalpage/2025-03-25/1222881997.PDF"})
def offline(*_, **__):
    with Path(sys.argv[2]).open("a", encoding="ascii") as stream:
        stream.write("native-discovery\\n")
    if sys.argv[3] == "stop":
        os._exit(23)
    return {"announcements": raw, "totalRecordNum": len(raw), "totalpages": 1}
def without_security_id(candidate):
    value = original(candidate)
    value.pop("security_id", None)
    return value
original = DisclosureCandidate.to_dict
with patch.object(CninfoAnnouncementClient, "_post_json", offline):
    if sys.argv[3] in {"legacy", "multiple"}:
        with patch.object(DisclosureCandidate, "to_dict", without_security_id):
            raise SystemExit(main(["discover", "--config", sys.argv[4]]))
    raise SystemExit(main(["discover", "--config", sys.argv[4]]))
"""
LOSE_REPLY = """
import os
import sys
from src import feedback_owner
feedback_owner.print = lambda *_: os._exit(37)
raise SystemExit(feedback_owner.main(sys.argv[1:]))
"""


def digest(value):
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def occurrence(row):
    return digest(
        [
            row[k]
            for k in (
                "owner",
                "origin_owner",
                "run_id",
                "attempt_id",
                "step_id",
                "check_id",
            )
        ]
    )


def request(kind, body, identity):
    key = digest([kind, OWNER, *identity])
    return dict(
        schema_version="feedback-action/1",
        action_id=key,
        owner=OWNER,
        kind=kind,
        method="lookup" if kind == "reconcile" else "submit",
        payload=body,
        request_digest=digest([OWNER, kind, key, body]),
    )


def cli(root, action, payload=None, *tail, lost_reply=False):
    route = ["-c", LOSE_REPLY] if lost_reply else ["-m", "src.feedback_owner"]
    invocation = native_run(
        [
            sys.executable,
            "-B",
            *route,
            "--db",
            str(root / "owner.sqlite"),
            "--sidecar-dir",
            str(root),
            action,
            *tail,
        ],
        cwd=ROOT,
        input=json.dumps(payload).encode("ascii") if payload is not None else None,
        capture_output=True,
        timeout=15,
        check=False,
    )
    if lost_reply:
        assert invocation.returncode == 37 and not invocation.stdout, invocation.stderr
        return
    assert invocation.returncode == 0, invocation.stderr
    return json.loads(invocation.stdout)


def producer(root, mode, *, explicit_state=True):
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    config = root / "config.json"
    config.write_text("{}", encoding="utf-8")
    body = {**fixture["request"], "org_id": fixture["announcements"][0]["orgId"]}
    invocation = native_run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            "-c",
            PRODUCE,
            str(FIXTURE),
            str(root / "calls"),
            mode,
            str(config),
        ],
        cwd=ROOT,
        input=json.dumps(body).encode("ascii"),
        capture_output=True,
        env={
            **{
                key: value
                for key, value in os.environ.items()
                if key.upper()
                in {
                    "PATH",
                    "SYSTEMROOT",
                    "WINDIR",
                    "USERPROFILE",
                    "APPDATA",
                    "LOCALAPPDATA",
                    "TEMP",
                    "TMP",
                }
            },
            "RESEARCH_FEEDBACK_OUT": str(root / f"{mode}.jsonl"),
            **({"RESEARCH_FEEDBACK_STATE_ROOT": str(root / "owner-state")} if explicit_state else {}),
            "RESEARCH_FEEDBACK_RUN_ID": "f4-sid-fixture",
            "RESEARCH_FEEDBACK_ATTEMPT_ID": mode,
        },
        timeout=15,
        check=False,
    )
    return invocation


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="On POSIX the OS account database supplies the home")
def test_explicit_feedback_output_preserves_original_attempt_without_home(tmp_path, monkeypatch):
    for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "RESEARCH_FEEDBACK_STATE_ROOT"):
        monkeypatch.delenv(key, raising=False)
    result = producer(tmp_path, "legacy", explicit_state=False)

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert list((tmp_path / ".stockinfo-dl-simple" / "runs").glob("*"))
    records = observations(tmp_path, "legacy")
    assert records
    assert {(row["run_id"], row["attempt_id"]) for row in records} == {("f4-sid-fixture", "legacy")}
    assert (tmp_path / "calls").read_text().splitlines() == ["native-discovery"]


def observations(root, mode):
    return [
        {**json.loads(line), "origin_owner": OWNER}
        for line in (root / f"{mode}.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def issue_payload(root):
    entry = next(
        row
        for row in observations(root, "legacy")
        if row.get("issue_key") == "verified-candidate-id-missing"
    )
    key = occurrence(entry)
    return (
        entry,
        key,
        request("triage", {"occurrence_id": key, "observation": entry}, [key]),
    )


def test_live_cli_captured_deviation_repairs_original_candidate_and_preserves_billing(
    tmp_path,
):
    completed = producer(tmp_path, "normal")
    assert completed.returncode == 0, completed.stderr
    (normal,) = json.loads(completed.stdout)["candidates"]
    assert normal["security_id"] == "002594"
    assert not (tmp_path / ".sid-candidate-captures").exists()
    completed = producer(tmp_path, "legacy")
    assert completed.returncode == 0, completed.stderr
    (original,) = json.loads(completed.stdout)["candidates"]
    assert "security_id" not in original
    assert (tmp_path / "calls").read_text().splitlines() == [
        "native-discovery",
        "native-discovery",
    ]

    issue, key, triage = issue_payload(tmp_path)
    assert issue["evidence_ref"].startswith("sid-candidate-capture:")
    selected = cli(tmp_path, "triage", triage)
    assert selected["result"]["decision"] == "repair"
    issue_ref, generation = (selected["result"][k] for k in ("issue_ref", "generation"))
    repair = request(
        "repair",
        {"issue_ref": issue_ref, "generation": generation},
        [issue_ref, generation],
    )
    cli(tmp_path, "repair", repair, lost_reply=True)
    saved = cli(tmp_path, "get-action", None, repair["action_id"])["receipt"]
    fixed = saved["result"]["fixed_version"]
    assert saved["request"] == repair
    assert cli(tmp_path, "repair", repair)["result"] == saved["result"]
    projection = cli(tmp_path, "get-publication", None, repair["action_id"])[
        "publication"
    ]
    assert projection["candidate"] == normal
    assert projection["occurrence_id"] == key

    base = dict(
        issue_ref=issue_ref,
        fixed_version=fixed,
        occurrence_id=key,
        original_occurrence_id=key,
    )
    replay = request(
        "replay",
        {
            **base,
            "issue_owner": OWNER,
            "observation": issue,
            "acquisition": "reuse_only",
        },
        [key, OWNER, issue_ref, fixed],
    )
    replayed = cli(tmp_path, "replay", replay)["result"]
    assert replayed["verdict"] == "verified" and replayed["verified_version"] == fixed
    report = request(
        "report",
        {
            **base,
            "origin_owner": OWNER,
            "verdict": "verified",
            "evidence_ref": replayed["evidence_ref"],
        },
        [key, OWNER, issue_ref, fixed, "verified"],
    )
    cli(tmp_path, "report", report, lost_reply=True)
    assert cli(tmp_path, "report", report) == {"result": {"recorded": True}}
    assert (
        cli(tmp_path, "get-action", None, report["action_id"])["receipt"]["request"]
        == report
    )
    with closing(sqlite3.connect(tmp_path / "owner.sqlite")) as connection:
        assert connection.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 4
    assert (tmp_path / "calls").read_text().splitlines() == [
        "native-discovery",
        "native-discovery",
    ]


def test_started_attempt_and_a_different_completed_attempt_are_kept_separate(tmp_path):
    assert producer(tmp_path, "stop").returncode == 23
    assert producer(tmp_path, "normal").returncode == 0
    (started,) = observations(tmp_path, "stop")
    key = occurrence(started)
    result = cli(
        tmp_path,
        "reconcile",
        request("reconcile", {"occurrence_id": key, "observation": started}, [key]),
    )
    assert result["result"]["cost_state"] == "unknown"
    assert result["result"]["job_status"] == "unconfirmed"
    assert not (tmp_path / "owner.sqlite").exists()
    assert (tmp_path / "calls").read_text().splitlines() == [
        "native-discovery",
        "native-discovery",
    ]


@pytest.mark.parametrize(
    "failure", ["changed_capture", "missing_capture", "foreign_original"]
)
def test_candidate_evidence_cannot_be_swapped(tmp_path, failure):
    assert producer(tmp_path, "legacy").returncode == 0
    actual, key, triage = issue_payload(tmp_path)
    (capture,) = (tmp_path / ".sid-candidate-captures").glob("*.json")
    if failure == "changed_capture":
        payload = json.loads(capture.read_text(encoding="utf-8"))
        payload["native_security_id"] = "000001"
        capture.write_text(json.dumps(payload), encoding="utf-8")
    elif failure == "missing_capture":
        capture.unlink()
    else:
        actual["attempt_id"] = "different-attempt"
        key = occurrence(actual)
        triage = request("triage", {"occurrence_id": key, "observation": actual}, [key])
    assert cli(tmp_path, "triage", triage) == {"result": {"decision": "needs_evidence"}}


@pytest.mark.parametrize(
    ("field", "suffix"),
    [("transport_url", "?opaque=placeholder"), ("source_url", "&opaque=")],
)
def test_capture_skips_opaque_url_queries(tmp_path, field, suffix):
    from src.feedback_candidate_capture import capture_missing_identity

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    old = fixture["legacy_claim_verified"]
    unsafe = {**old, field: old[field] + suffix}
    row = {
        "owner": OWNER,
        "origin_owner": OWNER,
        "run_id": "run",
        "attempt_id": "attempt",
        "step_id": "step",
        "check_id": "check",
        "version": "1.3.0",
    }
    assert (
        capture_missing_identity(
            tmp_path / "events.jsonl",
            row,
            "002594",
            unsafe,
            {**unsafe, "security_id": "002594"},
        )
        is None
    )
    assert not (tmp_path / ".sid-candidate-captures").exists()

    assert capture_missing_identity(
        tmp_path / "events.jsonl",
        row,
        "002594",
        old,
        {**old, "security_id": "002594"},
    )


@pytest.mark.parametrize("mode", ["legacy", "multiple"])
def test_missing_complete_proof_keeps_original_business_response(tmp_path, mode):
    if mode == "legacy":
        (tmp_path / ".sid-candidate-captures").write_bytes(b"unavailable")
    original = producer(tmp_path, mode)
    assert original.returncode == 0, original.stderr
    candidates = json.loads(original.stdout)["candidates"]
    assert len(candidates) == (2 if mode == "multiple" else 1)
    assert all("security_id" not in candidate for candidate in candidates)
    issue = next(
        row
        for row in observations(tmp_path, mode)
        if row.get("issue_key") == "verified-candidate-id-missing"
    )
    assert "evidence_ref" not in issue
    key = occurrence(issue)
    action = request("triage", {"occurrence_id": key, "observation": issue}, [key])
    assert cli(tmp_path, "triage", action) == {"result": {"decision": "needs_evidence"}}
