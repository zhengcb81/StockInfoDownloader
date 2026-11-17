---
name: repair-stockinfo-dl-simple-issue
description: Repair a stockinfo-dl-simple (CNINFO candidate / staged fetch) deviation from an in-repo issue or run reference. Reproduce the first contract break from the public CLI with local fixtures, separate business error / test fixture / deployment / external conditions, write RED against the legitimate same-kind control, fix the shared responsibility layer, confirm targeted GREEN, then replay the original scenario. Use when a feedback-observation/1 deviation with owner=stockinfo-dl-simple needs a root-cause fix in this repo, or when ROOT hands back a cross-repo deviation.
---

# Repair `stockinfo-dl-simple` issue

This skill only consumes **this repo's** controlled replay entries and **non-executable**
evidence references. It never reaches the public CNINFO network, never reads a physical
staging path into feedback, and never treats a reported status as a reason to re-fetch.

## Start inputs (choose one)

- an issue card under `docs/plans/feedback-loop-2026-11-17/issues/` (e.g.
  `verified-candidate-id-missing.md` + its `.json` ledger), or
- a `feedback-observation/1` run reference: `run_id`, `attempt_id`, `step_id`, `check_id`,
  `issue_key`, `evidence_ref`.

Resolve the evidence ref to an in-repo file only: `docs/plans/feedback-loop-2026-11-17/evidence/`
or `tests/fixtures/feedback_observation/`. A ref containing a path, credential, URL or
command is invalid by construction (`feedback_observation.is_safe_ref`).

## Procedure

1. **Verify the claim, not the narrative.** Read `expected`, `actual`, `disposition`,
   `version` from the observation; confirm the tested code version with
   `git rev-parse HEAD` and the real input source from the fixture's `__provenance__`.
   Do not accept a deviation whose `disposition=expected` or whose `issue_key` is absent.

2. **Reproduce the first break from the public entry.** Run the real CLI with the local
   loopback/fixture bootstrap. Only `urllib.request.urlopen` and the temp roots are replaced;
   request validation, `CninfoAnnouncementClient`, `StockInfoCompanyWikiAdapter`, JSON and
   budget accounting stay on the production path.

   ~~~powershell
   & 'C:/Miniconda/python.exe' -B -m pytest -q tests/unit/test_feedback_observation.py
   # real CLI + loopback sample already recorded in:
   #   docs/plans/feedback-loop-2026-11-17/evidence/real-cli-sample.jsonl
   ~~~

   Pin the observed run with injected env (a fresh attempt gets a **new** `attempt_id`):
   `RESEARCH_FEEDBACK_OUT=<exclusive-sidecar>`, `RESEARCH_FEEDBACK_RUN_ID=<run>`,
   `RESEARCH_FEEDBACK_ATTEMPT_ID=<attempt>`. Replaying the same written event keeps its
   original IDs (`import_observations` reports zero new). Give each child worker its own OUT.

3. **Attribute separately.** Decide which of four buckets owns the deviation:
   - business error — a typed `AdapterError`/`CninfoApiError` code on the real wire;
   - test fixture — the fixture encodes an impossible state; fix the fixture, not the provider;
   - deployment environment — wrong version pin / config (e.g. a CWP route that predates
     `security_id` is an environment mismatch, not a SID code bug);
   - external condition — CNINFO schema drift, timeout, budget exhaustion; record a recovery
     condition instead of a code change.
   Only a same-repo responsibility layer is fixed here. A neighbour-repo deviation is handed
   to ROOT with public input/output and evidence; do not edit other repos.

4. **Find the legitimate same-kind control.** For every deviation, name the near case that is
   *expected*: a row with a missing/foreign `secCode` is `skipped-missing-code` /
   `skipped-different-stock` (`expected`), a summary is filtered, a killed process is
   `unknown`. Do not "fix" these into verified candidates. Ownership is read from the native
   `security_id`, never from the request code, URL query or filename.

5. **Write RED first.** Add/extend a test in `tests/unit/test_feedback_observation.py` (or the
   owning unit file) that fails on the current code with the exact `actual` word and keeps the
   control passing. The canonical examples:
   - field drop → `verified-candidate-id-missing`: legacy payload with no native `security_id`
     must be `actual=missing`, `disposition=deviation`.
   - batch missed success → `batch-missed-success`: a batch with a hidden failed item must not
     be reported as `verified`/`staged`; a started action with no receipt is `unknown`.
   Extend to a sibling listing or period by changing the request `security_id` and the native
   row `secCode` together in the same fixture mechanism — the fix must be shared, not per-ticker.

6. **Fix the common layer, then targeted GREEN.** Repair
   `src/cninfo_api.py` / `src/company_wiki_adapter.py` / `src/company_wiki_adapter_cli.py` /
   `src/feedback_observation.py` at the shared decision point. Re-run the single test, then the
   directed command:

   ~~~powershell
   & 'C:/Miniconda/python.exe' -B -m pytest -q tests/unit/test_feedback_observation.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/e2e/test_g4_latest_cli_offline.py
   ~~~

   Check single-line stdout wire, last stderr line + exit code, filtered source IDs, real byte
   counts and `unknown` behaviour. Note: the e2e file's default external CWP pin may be stale.
   The `security_id` assertion on the CWP side requires a CWP revision whose `DownloadCandidate`
   exposes that field; the historical pins recorded in
   `docs/plans/mb11-sid-2026-11-11/task_plan.md` predate it and fail that assertion. Confirm the
   revision actually carries the field before treating such a failure as a code regression, and
   report a pin mismatch as an environment finding to ROOT — do not edit another repo.

7. **Replay the original scenario and record.** Re-run the same `run_id`/input; with the same
   code version, input and deviation already reported, `needs_refetch()` is False — do not
   re-download. Attach any new run/evidence to the **same** issue card via `IssueLedger.record`
   (idempotent; first evidence preserved). Do not split or merge issue keys without
   distinguishing evidence.

8. **Report.** Record the fix commit, regression test IDs, and consumer status
   (`pending` / `verified` by ROOT). Keep raw responses, response bytes, download URL queries,
   unmasked exception text and physical paths out of the feedback sidecar and the handoff.

## Guard rails

- One JSON object per line, one writer per sidecar file, UTF-8. Never print observations to
  stdout/stderr.
- A write failure is counted by `FeedbackSink.write_failures`; it never changes the business
  exit code, charged budget, originals, or retry behaviour.
- `disposition` is only `expected` / `deviation` / `unknown`. Legitimate rejects are
  `expected`; a killed action is `unknown`; only proven contract breaks are `deviation`.
- Verification of ingestion/reuse across CWP/FF is ROOT's job. This skill closes the loop
  inside `stockinfo-dl-simple` only.
