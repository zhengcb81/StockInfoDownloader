"""F4-SID-FAILURES milestone C: item-by-item acceptance matrix.

Runs every injected entry event in fresh subprocesses and prints one JSON
verdict per case.  Denominator = the entry events actually injected here.

Run (from the repo root):

    C:/Miniconda/python.exe docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-node-c-check.py \
        > docs/plans/feedback-loop-2026-11-17/evidence/f4-sid-node-c-20261121.json
"""

import json
import shutil
import subprocess as sp
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tests" / "unit"))
import test_f4_ordinary_failures as T  # noqa: E402  (sanctioned doubles + helpers)

results = []


def record(case, injected, checks):
    ok = all(passed for passed, _ in checks.values())
    results.append({
        "case": case,
        "injected": injected,
        "verdict": "covered" if ok else "MISMATCH",
        "measured": {
            name: ("ok" if passed else repr(got))
            for name, (passed, got) in checks.items()
        },
    })


def obs(work, pattern="state/observations/feedback-*.jsonl"):
    return T._readback(str(work / pattern))


def details_of(work, pattern="state/observations/feedback-*.details.jsonl"):
    return T._readback(str(work / pattern))


tmp = Path(tempfile.mkdtemp(prefix="f4nodec-"))


def new_work(name):
    d = tmp / name
    d.mkdir()
    return T._work(d)


# ── ordinary CLI ──────────────────────────────────────────────────────────
work = new_work("c1"); config = T._config(work); state = T._state(work)
proc = T._run([*T.PYTHON, "-c", T.SINGLE_DRIVER, str(T.MAIN_PY), "900001", str(config)],
              T._env(work, state_root=state), work)
rows = obs(work)
terms = [r for r in rows if r.get("check_id") == "ordinary-download-task"]
settle = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
receipts = T._readback(str(state / "runs" / "*.json"))
det = [d for d in details_of(work) if "stage" in d]
record("ordinary-engine-permission", "main.py <code> with engine PermissionError", {
    "exit_nonzero": (T._receipt(proc)["exit_code"] == 1, T._receipt(proc)["exit_code"]),
    "no_all_tasks_completed": ("All tasks completed" not in T._stderr_text(proc), None),
    "task_failed_deviation": (terms and terms[0]["actual"] == "failed" and terms[0]["disposition"] == "deviation", terms[0]["actual"] if terms else None),
    "settlement_all_failed": (settle and settle[0]["actual"] == "all_failed", settle[0]["actual"] if settle else None),
    "receipt_all_failed": (receipts and receipts[0]["terminal"]["result"] == "all_failed", None),
    "cause_permissionerror": (bool(det) and "PermissionError" in det[0]["cause_chain"], det[0]["cause_chain"] if det else None),
})

work = new_work("c2"); config = T._config(work)
companies = T._companies(work, ["900001", "900002"])
proc = T._run([*T.PYTHON, "-c", T.MULTI_DRIVER, str(T.MAIN_PY), "900001", str(companies), str(config)],
              T._env(work, state_root=T._state(work)), work)
rows = obs(work)
terms = [r for r in rows if r.get("check_id") == "ordinary-download-task"]
settle = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
progress = json.loads((work / "logs" / "progress.json").read_text(encoding="utf-8"))
record("ordinary-two-tasks-partial", "--companies with one failing engine", {
    "exit_nonzero": (T._receipt(proc)["exit_code"] == 1, T._receipt(proc)["exit_code"]),
    "two_terminals": (len(terms) == 2, len(terms)),
    "actuals_split": ({r["actual"] for r in terms} == {"completed", "failed"}, sorted({r["actual"] for r in terms})),
    "settlement_partial": (settle and settle[0]["actual"] == "partial", settle[0]["actual"] if settle else None),
    "progress_marks_each": (progress["completed"] == ["900002"] and progress["failed"] == ["900001"], progress),
})

work = new_work("c3"); config = T._config(work)
proc = T._run([*T.PYTHON, "-c", T.SINGLE_OK_DRIVER, str(T.MAIN_PY), "900002", str(config)],
              T._env(work, state_root=T._state(work)), work)
rows = obs(work)
settle = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
record("ordinary-success", "main.py <code> with engine success", {
    "exit_zero": (T._receipt(proc)["exit_code"] == 0, T._receipt(proc)["exit_code"]),
    "all_tasks_completed": ("All tasks completed" in T._stderr_text(proc), None),
    "settlement_all_completed": (settle and settle[0]["actual"] == "all_completed" and settle[0]["disposition"] == "expected", settle[0]["actual"] if settle else None),
})

work = new_work("c4"); (work / "bad.json").write_text("{", encoding="ascii")
proc = T._run([*T.PYTHON, str(T.MAIN_PY), "900001", "--config", "bad.json"],
              T._env(work, state_root=T._state(work)), work)
rows = obs(work)
settle = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
det = details_of(work)
record("ordinary-broken-config", "main.py --config broken JSON", {
    "exit_nonzero": (proc.returncode == 1, proc.returncode),
    "no_side_effects": (not (work / "downloads").exists(), None),
    "settlement_not_started": (settle and settle[0]["actual"] == "not_started", settle[0]["actual"] if settle else None),
    "stage_config": (bool(det) and det[0].get("stage") == "config", det[0].get("stage") if det else None),
})

work = new_work("c5"); (work / "empty.json").write_text("{}", encoding="ascii")
proc = T._run([*T.PYTHON, str(T.MAIN_PY), "--config", "empty.json"],
              T._env(work, state_root=T._state(work)), work)
rows = obs(work)
settle = [r for r in rows if r.get("check_id") == "ordinary-run-settlement"]
record("ordinary-empty-config-vacuous", "main.py with an empty config (defaults inject test_cases: [])", {
    "exit_zero_vacuous_success": (proc.returncode == 0, proc.returncode),
    "zero_tasks_recorded": (settle and settle[0]["actual"] == "all_completed", settle[0]["actual"] if settle else None),
    "pre_existing_semantics_note": (True, "usage refusal is unreachable via the public entry because the config loader always injects empty test_cases/companies; only the broken-config refusal is injectable"),
})

work = new_work("c6")
proc = T._run([*T.PYTHON, "-B", "-m", "src.company_wiki_adapter_cli", "--bad-action"],
              T._env(work, state_root=T._state(work)), work)
bad_action = details_of(work)
record("adapter-bad-action", "adapter CLI --bad-action", {
    "exit_two": (proc.returncode == 2, proc.returncode),
    "local_refusal_not_sent": (
        any(detail.get("stage") == "arguments" and detail.get("sent") == "not_sent" for detail in bad_action),
        bad_action,
    ),
    "no_business_result": (not list(work.glob("**/*.pdf")), None),
})

fixture = json.loads(T.FIXTURE.read_text(encoding="utf-8"))
discover_payload = {**fixture["request"], "org_id": fixture["announcements"][0]["orgId"]}

work = new_work("ad-timeout")
(work / "valid.json").write_text("{}", encoding="ascii")
out = work / "out.jsonl"
proc = T._run([*T.PYTHON, "-c", T.ADAPTER_DISCOVER_DRIVER, "provider-timeout", str(T.FIXTURE), "valid.json"],
              T._env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="nodec", RESEARCH_FEEDBACK_ATTEMPT_ID="a1"),
              work, payload=json.dumps(discover_payload).encode("utf-8"))
det = T._readback(str(out) + ".details.jsonl")
trow = next((d for d in det if d.get("stage") == "transport"), None)
record("adapter-discover-transport-timeout", "discover with TimeoutError at the transport boundary", {
    "exit_nonzero": (proc.returncode == 1, proc.returncode),
    "outer_code_upstream": (json.loads(T._stderr_text(proc).splitlines()[-1])["error"]["code"] == "upstream_unavailable", None),
    "stage_transport": (trow is not None, None),
    "sent_unknown_timeout": (trow is not None and trow["sent"] == "unknown" and "TimeoutError" in trow["cause_types"], trow["cause_types"] if trow else None),
})

work = new_work("ad-valid")
(work / "valid.json").write_text("{}", encoding="ascii")
out = work / "out.jsonl"
proc = T._run([*T.PYTHON, "-c", T.ADAPTER_DISCOVER_DRIVER, "valid-candidate", str(T.FIXTURE), "valid.json"],
              T._env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="nodec", RESEARCH_FEEDBACK_ATTEMPT_ID="a1"),
              work, payload=json.dumps(discover_payload).encode("utf-8"))
rows = T._readback(str(out))
terms = [r for r in rows if r.get("check_id") == "candidate-listing-identity"]
record("adapter-valid-candidates", "discover with fixture announcements", {
    "exit_zero": (proc.returncode == 0, proc.returncode),
    "candidates_present": (json.loads(T._stdout_text(proc))["candidates"], None),
    "verified_expected": (terms and terms[0]["actual"] == "verified" and terms[0]["disposition"] == "expected", terms[0]["actual"] if terms else None),
})

work = new_work("ad-missing")
(work / "valid.json").write_text("{}", encoding="ascii")
out = work / "out.jsonl"
proc = T._run([*T.PYTHON, "-c", T.ADAPTER_DISCOVER_DRIVER, "missing-candidate-id", str(T.FIXTURE), "valid.json"],
              T._env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="nodec", RESEARCH_FEEDBACK_ATTEMPT_ID="a1"),
              work, payload=json.dumps(discover_payload).encode("utf-8"))
rows = T._readback(str(out))
terms = [r for r in rows if r.get("check_id") == "candidate-listing-identity"]
record("adapter-missing-identity", "discover with serialization missing security_id", {
    "exit_zero": (proc.returncode == 0, proc.returncode),
    "deviation_named": (terms and terms[0]["issue_key"] == "verified-candidate-id-missing", terms[0]["issue_key"] if terms else None),
})

work = new_work("ad-fetch")
(work / "valid.json").write_text("{}", encoding="ascii")
stage_file = work / "already-a-file"
stage_file.touch()
fetch_payload = json.dumps({"adapter_payload_json": json.dumps(fixture["legacy_claim_verified"])})
proc = T._run([*T.PYTHON, "-c", T.ADAPTER_FETCH_DRIVER, "valid.json", str(stage_file)],
              T._env(work, RESEARCH_FEEDBACK_OUT=str(work / "out.jsonl"), RESEARCH_FEEDBACK_RUN_ID="nodec", RESEARCH_FEEDBACK_ATTEMPT_ID="a1"),
              work, payload=fetch_payload.encode("utf-8"))
det = T._readback(str(work / "out.jsonl.details.jsonl"))
staging_row = next((d for d in det if d.get("stage") == "staging"), None)
record("adapter-fetch-staging-file", "fetch --staging-dir pointing at an ordinary file", {
    "exit_one": (proc.returncode == 1, proc.returncode),
    "outer_code_upstream": (json.loads(T._stderr_text(proc).splitlines()[-1])["error"]["code"] == "upstream_unavailable", None),
    "staging_unknown_sent_fileexists": (staging_row is not None and staging_row["sent"] == "unknown" and "FileExistsError" in staging_row["cause_types"], staging_row["cause_types"] if staging_row else None),
})

work = new_work("ad-budget")
(work / "valid.json").write_text("{}", encoding="ascii")
out = work / "out.jsonl"
budget_payload = json.dumps({**discover_payload, "acquisition_budget": {
    "schema_version": "1.0", "max_response_bytes": 100, "timeout_seconds": 5, "max_cost_usd": "1"}})
proc = T._run([*T.PYTHON, "-c", T.ADAPTER_BUDGET_DRIVER, "valid.json"],
              T._env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="nodec", RESEARCH_FEEDBACK_ATTEMPT_ID="a1"),
              work, payload=budget_payload.encode("utf-8"))
rows = T._readback(str(out))
budget_rows = [r for r in rows if r.get("check_id") == "acquisition-budget"]
record("adapter-budget-refusal", "discover with a 100-byte response budget against a 1MB body", {
    "exit_one_budget_envelope": (proc.returncode == 1 and json.loads(T._stderr_text(proc).splitlines()[-1])["error"]["code"] == "budget_exceeded", proc.returncode),
    "budget_observation": (bool(budget_rows) and budget_rows[0]["actual"] != "within_budget", budget_rows[0]["actual"] if budget_rows else None),
})

# ── failure log ───────────────────────────────────────────────────────────
work = new_work("log"); log_file = work / "failed_downloads.json"
proc = T._run([*T.PYTHON, "-c", T.LOG_WRITER, str(log_file)], T._env(work), work)
rows = T._readback(str(log_file))
record("failure-log-refused-write", "two records, refused persistence, mid-flush arrival, recovery", {
    "queue_kept_after_refusal": (json.loads(T._stdout_text(proc).splitlines()[-1])["after_refused"] == 2, None),
    "four_distinct_persisted": (len(rows) == 4 and len({(r["stock_code"], r["file_name"]) for r in rows}) == 4, len(rows)),
})

work = new_work("log2"); log_file = work / "failed_downloads.json"
log_file.write_text(json.dumps([{"timestamp": "2020", "stock_code": "600000", "stock_name": "legacy",
                                 "file_name": "old", "url": "u", "error": "old"}]), encoding="utf-8")
proc = T._run([*T.PYTHON, "-c", T.MIGRATION_WRITER, str(log_file)], T._env(work), work)
rows = T._readback(str(log_file))
record("failure-log-legacy-migration", "legacy failure file plus refused then recovered flush", {
    "legacy_first_intact": (rows and rows[0]["stock_code"] == "600000", None),
    "new_record_appended": (len(rows) == 2, len(rows)),
})

# ── kill window and cold reconcile ────────────────────────────────────────
work = new_work("kill"); config = T._config(work); marker = work / "engine-marker"
T._run([*T.PYTHON, "-c", T.KILL_DRIVER, str(T.MAIN_PY), "900001", str(marker), str(config)],
       T._env(work, state_root=T._state(work)), work)
T._run([*T.PYTHON, "-c", T.SINGLE_OK_DRIVER, str(T.MAIN_PY), "900002", str(config)],
       T._env(work, state_root=T._state(work), RESEARCH_FEEDBACK_RUN_ID="sid-later",
              RESEARCH_FEEDBACK_ATTEMPT_ID="try-later"), work)
receipts = T._readback(str(work / "state" / "runs" / "*.json"))
by_run = {r["run_id"]: r for r in receipts}
record("kill-mid-task-unknown", "engine os._exit mid task, then a successful sibling attempt", {
    "engine_reached": (marker.exists(), None),
    "killed_receipt_unconfirmed": (any(r["terminal"] is None for r in receipts), None),
    "sibling_independent": (bool(by_run.get("sid-later", {}).get("terminal", {})) and by_run["sid-later"]["terminal"]["result"] == "all_completed", None),
})

recon = T._run([*T.PYTHON, "-B", "-m", "src.feedback_publish", "reconcile", "--json"],
               T._env(work, state_root=T._state(work)), work)
report = json.loads(recon.stdout)
record("reconcile-cold-read", "new process, read-only reconcile of the kill state", {
    "receipts_visible": (len(report["receipts"]) == 2, len(report["receipts"])),
    "unconfirmed_listed": (any(r["terminal"] is None for r in report["receipts"]), None),
})

# ── delivery windows ──────────────────────────────────────────────────────
work = new_work("win1"); inbox = work / "inbox"; state = T._state(work)
T._run([*T.PYTHON, "-c", T.PUBLISH_KILL_BEFORE_READY, str(inbox), str(state)], T._env(work), work)
before = sorted(p.name for p in inbox.glob("feedback-*.jsonl") if not p.name.endswith(".details.jsonl"))
T._run([*T.PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"], T._env(work, state_root=state), work)
after_data = sorted(p.name for p in inbox.glob("feedback-*.jsonl") if not p.name.endswith(".details.jsonl"))
after_ready = list(inbox.glob("feedback-*.ready"))
record("window-data-without-ready", "kill between data file and ready marker, then republish", {
    "same_delivery_identity": (after_data == before and len(after_data) == 1, after_data),
    "ready_written_once": (len(after_ready) == 1, len(after_ready)),
    "pending_acked": (T._readback(str(state / "pending" / "*.json")) == [], None),
})

work = new_work("win2"); inbox = work / "inbox"; state = T._state(work)
T._run([*T.PYTHON, "-c", T.PUBLISH_KILL_BEFORE_ACK, str(inbox), str(state)], T._env(work), work)
before = sorted(p.name for p in inbox.glob("feedback-*.jsonl") if not p.name.endswith(".details.jsonl"))
T._run([*T.PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"], T._env(work, state_root=state), work)
after_data = sorted(p.name for p in inbox.glob("feedback-*.jsonl") if not p.name.endswith(".details.jsonl"))
record("window-ready-without-ack", "kill after delivery before ack, then republish", {
    "no_new_files": (after_data == before, after_data),
    "pending_acked": (T._readback(str(state / "pending" / "*.json")) == [], None),
})

work = new_work("win3"); inbox = work / "inbox"; state = T._state(work)
T._run([*T.PYTHON, "-c", T.PUBLISH_KILL_BEFORE_ACK, str(inbox), str(state)], T._env(work), work)
c1 = sp.Popen([*T.PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"], cwd=work,
              env=T._env(work, state_root=state), stdout=sp.PIPE, stderr=sp.PIPE)
c2 = sp.Popen([*T.PYTHON, "-B", "-m", "src.feedback_publish", "republish", "--json"], cwd=work,
              env=T._env(work, state_root=state), stdout=sp.PIPE, stderr=sp.PIPE)
for child in (c1, c2):
    child.communicate(timeout=120)
after_data = sorted(p.name for p in inbox.glob("feedback-*.jsonl") if not p.name.endswith(".details.jsonl"))
record("window-parallel-republishers", "two republish processes on the same pending occurrence", {
    "both_exit_zero": (c1.returncode == 0 and c2.returncode == 0, (c1.returncode, c2.returncode)),
    "one_publication": (len(after_data) == 1, after_data),
    "pending_acked": (T._readback(str(state / "pending" / "*.json")) == [], None),
})

# ── publication modes ─────────────────────────────────────────────────────
work = new_work("pub"); config = T._config(work)
out = work / "out.jsonl"
T._run([*T.PYTHON, "-c", T.SINGLE_OK_DRIVER, str(T.MAIN_PY), "900002", str(config)],
       T._env(work, RESEARCH_FEEDBACK_OUT=str(out), RESEARCH_FEEDBACK_RUN_ID="host-run",
              RESEARCH_FEEDBACK_ATTEMPT_ID="host-1",
              RESEARCH_FEEDBACK_STATE_ROOT=str(work / "state")), work)
dir_inbox = work / "dirinbox"
T._run([*T.PYTHON, "-c", T.SINGLE_OK_DRIVER, str(T.MAIN_PY), "900002", str(config)],
       T._env(work, RESEARCH_FEEDBACK_DIR=str(dir_inbox),
              RESEARCH_FEEDBACK_STATE_ROOT=str(work / "state")), work)
defroot = work / "stateroot"
T._run([*T.PYTHON, "-c", T.SINGLE_OK_DRIVER, str(T.MAIN_PY), "900002", str(config)],
       T._env(work, RESEARCH_FEEDBACK_STATE_ROOT=str(defroot)), work)
record("publication-modes", "explicit OUT, DIR-only, and default state root", {
    "out_file_written": (out.exists() and Path(str(out) + ".details.jsonl").exists(), None),
    "dir_ready_bound": (list(dir_inbox.glob("feedback-*.ready")) != [], None),
    "state_root_observations": (list(defroot.glob("observations/feedback-*.jsonl")) != [], None),
})

print(json.dumps({
    "denominator": len(results),
    "covered": sum(1 for r in results if r["verdict"] == "covered"),
    "results": results,
}, ensure_ascii=False, indent=1))
shutil.rmtree(tmp, ignore_errors=True)
