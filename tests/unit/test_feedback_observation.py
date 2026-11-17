"""feedback-observation/1 — SID candidate identity + staged-fetch feedback.

These tests are the RED contract for the FB-SID card.  They are deliberately
written against the *public* observation module and the public JSON CLI, never
against provider-private state:

* one CNINFO-shaped page supplies a verified row, a missing-``secCode`` row and
  a different-stock row; exact/latest must keep only the verified candidate and
  record the two rejects as legitimate (``expected``), never as a defect;
* a historical payload that *claims* a verified candidate without the native
  ``security_id`` evidence must become a named deviation whose first evidence
  is preserved;
* observations are one-line UTF-8 JSONL on an injected sidecar, never on the
  business stdout/stderr, carry no raw response / bytes / URL query / physical
  path, survive a write failure without changing the business result, and keep
  ``unknown`` when a started action has no terminal state;
* re-importing the same observation adds nothing, a new attempt is distinct,
  and the same judged root cause folds into one issue card.

Fixtures come from ``tests/fixtures/feedback_observation`` (derived from the
local BYD capture).  No network, user config or company list is touched.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src import company_wiki_adapter_cli as cli
from src import constants as C
from src import feedback_observation as fb
from src.acquisition_budget import AcquisitionBudgetExceeded

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "feedback_observation"
    / "listing_identity_rows.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _obs(**overrides):
    # schema_version/owner are derived by make_observation, never passed in.
    value = {
        "run_id": "run-a",
        "attempt_id": "try-1",
        "step_id": "step-1",
        "check_id": fb.CHECK_CANDIDATE_IDENTITY,
        "expected": "verified",
        "actual": "verified",
        "version": "fixture-v1",
    }
    value.update(overrides)
    return value


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _invoke(monkeypatch, payload, *, adapter, argv=("discover",), env=None):
    """Run the real CLI main() with injected streams and optional feedback env."""
    stdout, stderr = io.StringIO(), io.StringIO()
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    monkeypatch.setattr(cli.sys, "stderr", stderr)
    monkeypatch.setattr(cli, "_build_adapter", lambda _config: adapter)
    for key in (fb.ENV_OUT, fb.ENV_RUN_ID, fb.ENV_ATTEMPT_ID):
        monkeypatch.delenv(key, raising=False)
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, str(value))
    code = cli.main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


class _DiscoverAdapter:
    """Public-shape adapter stub: returns candidates, applies a budget charge."""

    def __init__(self, candidates, *, charge=0, raise_exc=None):
        self.candidates = candidates
        self.charge = charge
        self.raise_exc = raise_exc
        self.downloader = MagicMock()

    def discover(self, request, *, acquisition_budget=None):
        if acquisition_budget is not None and self.charge:
            acquisition_budget.consume_response_bytes(self.charge)
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.candidates

    def fetch(self, candidate, staging_dir, *, acquisition_budget=None):
        return MagicMock(to_dict=lambda: {"candidate_id": candidate.candidate_id})


# ---------------------------------------------------------------------------
# Node 1 — wire format and the three-row identity difference
# ---------------------------------------------------------------------------


def test_wire_format_requires_every_mandatory_string_field():
    obs = fb.make_observation(**_obs())
    for field in fb.REQUIRED_FIELDS:
        assert isinstance(obs[field], str) and obs[field], field
    assert obs["schema_version"] == "feedback-observation/1"
    assert obs["owner"] == "stockinfo-dl-simple"
    assert set(obs) <= set(fb.REQUIRED_FIELDS) | set(fb.OPTIONAL_FIELDS)


def test_disposition_is_a_closed_vocabulary():
    assert fb.make_observation(**_obs(disposition="expected"))["disposition"] == "expected"
    assert fb.make_observation(**_obs(disposition="deviation"))["disposition"] == "deviation"
    assert fb.make_observation(**_obs(disposition="unknown"))["disposition"] == "unknown"
    with pytest.raises(ValueError):
        fb.make_observation(**_obs(disposition="maybe"))


@pytest.mark.parametrize(
    "bad_ref",
    ["C:/secret/path", "/abs/path", "https://host/x", "a b", "cmd;rm -rf", "u:p@host", ".."],
)
def test_references_cannot_carry_paths_credentials_or_commands(bad_ref):
    with pytest.raises(ValueError):
        fb.make_observation(**_obs(evidence_ref=bad_ref))


def test_opaque_evidence_reference_is_accepted():
    ref = "cninfo-ann:1222881496"
    assert fb.make_observation(**_obs(evidence_ref=ref))["evidence_ref"] == ref


def test_verified_candidate_is_expected_even_with_a_native_security_id():
    candidate = {
        "security_id": "002594",
        "provider_document_id": "1222881496",
        "title": "比亚迪股份有限公司2024年年度报告",
    }
    verdict = fb.classify_candidate_identity(candidate, "002594")
    assert verdict["actual"] == "verified"
    assert verdict["disposition"] == "expected"
    assert "issue_key" not in verdict


def test_legacy_claim_without_native_evidence_is_a_named_deviation():
    # The legacy payload still *looks* matched: the correct stock code appears
    # in source_url and title.  Ownership must NOT be inferred from either.
    candidate = _fixture()["legacy_claim_verified"]
    assert "security_id" not in candidate
    assert "002594" in candidate["source_url"]
    verdict = fb.classify_candidate_identity(candidate, "002594")
    assert verdict["actual"] == "missing"
    assert verdict["disposition"] == "deviation"
    assert verdict["issue_key"] == fb.ISSUE_VERIFIED_ID_MISSING


def test_conflicting_native_security_id_is_a_separate_deviation():
    verdict = fb.classify_candidate_identity(
        {"security_id": "000001", "provider_document_id": "1222882996"}, "002594"
    )
    assert verdict["actual"] == "mismatched"
    assert verdict["disposition"] == "deviation"
    assert verdict["issue_key"] != fb.ISSUE_VERIFIED_ID_MISSING


@pytest.mark.parametrize(
    "sec_code, expected_actual",
    [
        ("002594", "verified"),
        ("", "skipped-missing-code"),
        ("000001", "skipped-different-stock"),
    ],
)
def test_unproven_rows_are_legitimate_rejects_not_defects(sec_code, expected_actual):
    verdict = fb.classify_raw_record(
        {"announcementId": "1", "secCode": sec_code}, "002594"
    )
    assert verdict["actual"] == expected_actual
    assert verdict["disposition"] == "expected"
    assert "issue_key" not in verdict


def _announcement(row):
    """Build the production CninfoAnnouncement from a fixture row."""
    import datetime as dt
    from urllib.parse import quote

    from src.cninfo_api import CninfoAnnouncement

    moment = dt.datetime.fromtimestamp(
        row["announcementTime"] / 1000.0, tz=dt.timezone(dt.timedelta(hours=8))
    )
    adj = row["adjunctUrl"]
    return CninfoAnnouncement(
        announcement_id=row["announcementId"],
        filing_date=moment.date().isoformat(),
        title=row["announcementTitle"],
        sec_code=row.get("secCode", ""),
        sec_name=row.get("secName", ""),
        org_id=row.get("orgId", ""),
        announcement_time_ms=row["announcementTime"],
        adjunct_type=row.get("adjunctType", "PDF"),
        adjunct_url=adj,
        transport_url=f"https://static.cninfo.com.cn/{adj}",
        detail_url=(
            "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=002594"
            f"&announcementId={quote(row['announcementId'], safe='')}"
        ),
    )


@pytest.mark.parametrize("mode", ["exact", "latest_as_of"])
def test_real_adapter_keeps_only_the_verified_row_and_does_not_accuse_rejects(mode):
    """The exact/latest discovery path filters unproven rows and observes them."""
    from src.company_wiki_adapter import AdapterDiscoveryRequest, StockInfoCompanyWikiAdapter

    rows = [_announcement(row) for row in _fixture()["announcements"]]

    class _Api:
        def discover_announcements(self, **kwargs):
            return list(rows), MagicMock()

    adapter = StockInfoCompanyWikiAdapter(None, cninfo_client=_Api())
    request_kwargs = dict(
        stock_code="002594",
        stock_name="比亚迪",
        org_id="gshk0001211",
        document_kind="annual_report",
        mode=mode,
        max_pages=1,
    )
    if mode == "exact":
        request_kwargs["fiscal_year"] = 2024
    else:
        request_kwargs["as_of_date"] = "2026-06-01"
    candidates = adapter.discover(AdapterDiscoveryRequest(**request_kwargs))

    assert [c.provider_document_id for c in candidates] == ["1222881496"]
    assert candidates[0].security_id == "002594"
    verdicts = [fb.classify_raw_record({"secCode": r.sec_code}, "002594") for r in rows]
    assert [v["actual"] for v in verdicts] == [
        "verified",
        "skipped-missing-code",
        "skipped-different-stock",
    ]
    assert all(v["disposition"] == "expected" for v in verdicts)


# ---------------------------------------------------------------------------
# Node 2 — sidecar JSONL, CLI wiring, no leakage, no business changes
# ---------------------------------------------------------------------------


def test_cli_discover_emits_sidecar_without_touching_business_streams(monkeypatch, tmp_path):
    payload = {
        "entity": "比亚迪",
        "security_id": "002594",
        "document_kind": "annual_report",
        "fiscal_year": 2024,
        "acquisition_budget": {
            "schema_version": "1.0",
            "max_response_bytes": 200,
            "timeout_seconds": 5.0,
            "max_cost_usd": "0",
        },
    }
    out = tmp_path / "observations.jsonl"
    code, stdout, stderr = _invoke(
        monkeypatch,
        payload,
        adapter=_DiscoverAdapter([], charge=17),
        env={fb.ENV_OUT: out, fb.ENV_RUN_ID: "run-1", fb.ENV_ATTEMPT_ID: "try-7"},
    )
    assert code == 0
    assert stderr == ""
    response = json.loads(stdout)  # exactly one JSON value, single line
    assert response["status"] == "ok"
    assert response["acquisition_usage"]["response_bytes"] == 17

    observations = _read_jsonl(out)
    assert observations, "feedback must be produced when a sidecar is injected"
    assert all(o["schema_version"] == "feedback-observation/1" for o in observations)
    assert all(o["owner"] == "stockinfo-dl-simple" for o in observations)
    assert all(o["run_id"] == "run-1" and o["attempt_id"] == "try-7" for o in observations)
    assert any(o["actual"] == "started" for o in observations)
    assert any(o["actual"] == "verified" for o in observations)
    assert any(o["check_id"] == fb.CHECK_ACQUISITION_BUDGET for o in observations)


def test_sidecar_carries_no_bytes_response_url_query_or_physical_path(monkeypatch, tmp_path):
    out = tmp_path / "observations.jsonl"
    payload = {
        "entity": "比亚迪",
        "security_id": "002594",
        "document_kind": "annual_report",
        "fiscal_year": 2024,
    }
    with patch("urllib.request.urlopen") as urlopen:
        urlopen.side_effect = AssertionError("feedback test must not reach the network")
        code, stdout, stderr = _invoke(
            monkeypatch,
            payload,
            adapter=_DiscoverAdapter([]),
            env={fb.ENV_OUT: out},
        )
    assert code == 0 and stderr == ""
    raw = out.read_text(encoding="utf-8")
    for forbidden in ("%PDF", "http", "announcementTime=", "C:\\", str(tmp_path), "/tmp/"):
        assert forbidden not in raw, forbidden
    assert all(len(line) < 600 for line in raw.splitlines())


def test_budget_rejection_keeps_stderr_last_line_and_records_terminal(monkeypatch, tmp_path):
    out = tmp_path / "obs.jsonl"
    payload = {
        "entity": "比亚迪",
        "security_id": "002594",
        "document_kind": "annual_report",
        "fiscal_year": 2024,
        "acquisition_budget": {
            "schema_version": "1.0",
            "max_response_bytes": 20,
            "timeout_seconds": 5.0,
            "max_cost_usd": "0",
        },
    }
    code, stdout, stderr = _invoke(
        monkeypatch,
        payload,
        adapter=_DiscoverAdapter(
            [], charge=9, raise_exc=AcquisitionBudgetExceeded("response too large")
        ),
        env={fb.ENV_OUT: out},
    )
    assert code == 1 and stdout == ""
    error = json.loads(stderr.splitlines()[-1])["error"]
    assert error["code"] == "budget_exceeded"
    assert error["acquisition_usage"]["response_bytes"] == 9

    observations = _read_jsonl(out)
    terminal = [o for o in observations if o["actual"] not in ("started",)]
    assert terminal
    assert terminal[-1]["actual"] == "budget_exceeded"
    assert terminal[-1]["disposition"] == "expected"  # a legitimate rejection
    assert terminal[-1]["check_id"] == fb.CHECK_ACQUISITION_BUDGET


def test_sidecar_write_failure_does_not_change_business_result(monkeypatch, tmp_path):
    payload = {
        "entity": "比亚迪",
        "security_id": "002594",
        "document_kind": "annual_report",
        "fiscal_year": 2024,
    }
    unwritable = tmp_path / "missing-parent" / "obs.jsonl"  # parent does not exist
    code, stdout, stderr = _invoke(
        monkeypatch,
        payload,
        adapter=_DiscoverAdapter([]),
        env={fb.ENV_OUT: unwritable},
    )
    assert code == 0
    assert json.loads(stdout)["status"] == "ok"
    assert "status" in json.loads(stderr.splitlines()[-1]) if stderr.strip() else True


def test_started_without_terminal_observation_stays_unknown(tmp_path):
    out = tmp_path / "obs.jsonl"
    sink = fb.FeedbackSink(out, run_id="run-x", attempt_id="try-1", version="fixture-v1")
    with pytest.raises(RuntimeError, match="interrupted"):
        with sink.action(
            step_id="fetch-1",
            check_id=fb.CHECK_STAGED_FETCH,
            expected="staged",
        ):
            raise RuntimeError("interrupted before receipt")
    rows = _read_jsonl(out)
    assert rows[0]["actual"] == "started"
    assert rows[-1]["actual"] == "unknown"
    assert rows[-1]["disposition"] == "unknown"


def test_cli_process_interrupt_before_receipt_leaves_unknown(monkeypatch, tmp_path):
    """A real CLI invocation interrupted (BaseException) never fabricates success."""
    out = tmp_path / "obs.jsonl"
    payload = {
        **_fixture()["legacy_claim_verified"],
        "adapter_payload_json": json.dumps(
            _fixture()["legacy_claim_verified"], ensure_ascii=False
        ),
    }

    class _InterruptedAdapter(_DiscoverAdapter):
        def fetch(self, candidate, staging_dir, *, acquisition_budget=None):
            raise KeyboardInterrupt("process killed before receipt")

    with pytest.raises(KeyboardInterrupt):
        _invoke(
            monkeypatch,
            payload,
            adapter=_InterruptedAdapter([]),
            argv=("fetch", "--staging-dir", str(tmp_path / "stage")),
            env={fb.ENV_OUT: out, fb.ENV_RUN_ID: "run-int", fb.ENV_ATTEMPT_ID: "try-1"},
        )
    rows = _read_jsonl(out)
    assert rows[0]["actual"] == "started"
    assert rows[-1]["actual"] == "unknown"
    assert rows[-1]["disposition"] == "unknown"
    assert rows[-1]["step_id"] == "fetch-1"
    assert list((tmp_path / "stage").glob("*.pdf")) == []


def test_details_are_whitelisted_and_referenced_opaquely(tmp_path):
    out = tmp_path / "obs.jsonl"
    sink = fb.FeedbackSink(out, run_id="run-x", attempt_id="try-1", version="fixture-v1")
    action = sink.action(
        step_id="discover-1", check_id=fb.CHECK_CANDIDATE_IDENTITY, expected="verified"
    )
    action.finish(
        actual="verified",
        disposition="expected",
        details={
            "action": "discover_exact",
            "security_id": "002594",
            "announcement_ids": ["1222881496"],
            "budget_usage": {"response_bytes": 17, "cost_usd": "0"},
            "retried": False,
            "reused": False,
            "raw_response": "MUST NOT BE WRITTEN",
            "exception_text": "MUST NOT BE WRITTEN",
        },
    )
    detail_ref = [o for o in _read_jsonl(out) if o["actual"] == "verified"][0]["details_ref"]
    assert fb.is_safe_ref(detail_ref)
    written = json.loads((tmp_path / (out.name + ".details.jsonl")).read_text(encoding="utf-8"))
    assert written["budget_usage"]["response_bytes"] == 17
    assert "raw_response" not in written
    assert "exception_text" not in written


# ---------------------------------------------------------------------------
# Node 3 — replay, dedup, issue cards and the no-refetch guard
# ---------------------------------------------------------------------------


def test_reimporting_the_same_observation_adds_nothing(tmp_path):
    dest = tmp_path / "obs.jsonl"
    obs = fb.make_observation(**_obs())
    first = fb.import_observations(dest, [obs])
    second = fb.import_observations(dest, [obs, obs])
    assert (first.added, first.duplicates) == (1, 0)
    assert (second.added, second.duplicates) == (0, 2)
    assert len(_read_jsonl(dest)) == 1


def test_replay_reuses_ids_while_a_new_attempt_is_distinct(tmp_path):
    dest = tmp_path / "obs.jsonl"
    fb.import_observations(dest, [fb.make_observation(**_obs())])
    fb.import_observations(
        dest,
        [
            fb.make_observation(**_obs()),  # replay: same IDs
            fb.make_observation(**_obs(attempt_id="try-2")),
        ],
    )
    rows = _read_jsonl(dest)
    assert len(rows) == 2
    assert {row["attempt_id"] for row in rows} == {"try-1", "try-2"}


def test_issue_ledger_folds_runs_but_keeps_distinct_roots(tmp_path):
    ledger = fb.IssueLedger(tmp_path / "issues")
    first = fb.make_observation(
        **_obs(
            actual="missing",
            disposition="deviation",
            issue_key=fb.ISSUE_VERIFIED_ID_MISSING,
            evidence_ref="case-byd-fy2024",
        )
    )
    assert ledger.record(first) is True
    assert ledger.record(first) is False  # duplicate import
    later = fb.make_observation(
        **_obs(
            run_id="run-b",
            attempt_id="try-2",
            actual="missing",
            disposition="deviation",
            issue_key=fb.ISSUE_VERIFIED_ID_MISSING,
            evidence_ref="case-other-listing",
        )
    )
    assert ledger.record(later) is True  # new run attaches to the same card
    other_root = fb.make_observation(
        **_obs(
            run_id="run-b",
            attempt_id="try-2",
            actual="skipped",
            disposition="deviation",
            issue_key=fb.ISSUE_BATCH_MISSED_SUCCESS,
            evidence_ref="case-other-listing",
        )
    )
    assert ledger.record(other_root) is True  # same error code, different cause
    cards = ledger.cards()
    by_key = {card["issue_key"]: card for card in cards}
    assert set(by_key) == {fb.ISSUE_VERIFIED_ID_MISSING, fb.ISSUE_BATCH_MISSED_SUCCESS}
    assert len(by_key[fb.ISSUE_VERIFIED_ID_MISSING]["runs"]) == 2
    assert by_key[fb.ISSUE_VERIFIED_ID_MISSING]["runs"][0]["evidence_ref"] == "case-byd-fy2024"


def test_terminal_report_guard_prevents_a_duplicate_fetch(tmp_path):
    started = fb.make_observation(
        **_obs(step_id="fetch-1", check_id=fb.CHECK_STAGED_FETCH, actual="started", disposition="unknown")
    )
    assert fb.needs_refetch([started], step_id="fetch-1") is True
    terminal = fb.make_observation(
        **_obs(step_id="fetch-1", check_id=fb.CHECK_STAGED_FETCH, actual="staged", disposition="expected")
    )
    assert fb.needs_refetch([started, terminal], step_id="fetch-1") is False
