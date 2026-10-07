# G4-SID-LATEST — as-of latest A-share periodic report discovery

**Lane card:** `company-wiki/docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/g4_sid_latest_discovery.md`
**Worktree:** `C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple`
**Branch:** `codex/g4-sid-latest`  **Base:** `8ed5fdde5e88c13470c120665ff3074a7f44a052`
**PWF pin:** `PLAN_ID=g4-sid-latest`, `PWF_PLAN_ROOT=<worktree>/docs/implementation`

## Goal

Make CNINFO **metadata discovery** complete for `mode=latest_as_of`:

- keep `exact` semantics byte-for-byte (mandatory integer `fiscal_year`, existing year window/filter),
- latest resolves a real as-of window from real announcement metadata, returns the full bounded
  candidate set, or fails with an explicit non-retryable `discovery_incomplete` /
  `bounded_discovery_empty`,
- one shared `ProviderAcquisitionBudget` (bytes + deadline) across all pages of one invocation,
- `ADAPTER_VERSION` 1.2.0 → 1.3.0, wire schema stays `1.0`.

Non-goals: no new providers, no download/translate/summarize/model calls, no company-wiki
directories/DB writes in SID, no owner-file changes.

## Phases

### Phase 0: Baseline + owner protection — Status: complete
**Goal**: worktree created from base commit, owner state recorded, PWF pinned.
**Success Criteria**: `git status --short` of original repo matches the 11 tracked owner edits +
untracked company lists/scripts; worktree exists at the card path on `codex/g4-sid-latest`.
**Tests**: n/a (inspection)
**Status**: complete

### Phase 1: Read real sources + freeze interfaces — Status: complete
**Goal**: read `company_wiki_adapter.py`, `company_wiki_adapter_cli.py`, `cninfo_api.py`,
`acquisition_budget.py`, `transport_states.py` and the six responsibility tests; record the
frozen request/response/budget contract in `latest_request_contract.md`.
**Success Criteria**: findings written; no interface guessed.
**Tests**: n/a
**Status**: complete

### Phase 2: RED — new latest-discovery tests fail on current code — Status: complete
**Goal**: write `tests/unit/test_g4_latest_discovery.py` + `tests/fixtures/g4_latest/*.json`
covering: `fiscal_year=null` latest on current CLI fails; year-start annual falls back to the old
year instead of a guessed year; post-cutoff announcements excluded; summary-only first page with
full text on a later page; page-budget exhaustion not reported as complete; bad request input
must not construct a provider.
**Success Criteria**: the new tests fail against unmodified `src/` for the documented reasons.
**Tests**: `python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py`
**Status**: complete

### Phase 3: GREEN — request interpretation, window, filters, bounded completeness — Status: complete
**Goal**: implement trailing optional `mode` / `as_of_date` / `fiscal_period` / `form_type` on
`AdapterDiscoveryRequest`; latest date window + raw-total-driven pagination + metadata filtering +
typed `discovery_incomplete`; typed `AdapterError.code/retryable`; CLI validates request before
provider construction; `ADAPTER_VERSION=1.3.0`.
**Success Criteria**: phase-2 tests green; exact tests unchanged and green.
**Tests**: phase-2 command + six responsibility test files.
**Status**: complete

### Phase 4: Real offline CLI E2E + CWP 1.3.0 consumption — Status: complete
**Goal**: `tests/e2e/test_g4_latest_cli_offline.py` drives the real `-m src.company_wiki_adapter_cli`
entry through a loopback-only HTTP transport (driver under this directory), plus a read-only export
of the committed CWP `5930a644...` `JsonCommandAdapter.discover_bounded` consuming the 1.3.0
response; controlled loopback fetch regression keeps SHA/size/magic.
**Success Criteria**: one JSON value on stdout per success; failure usage real; exit codes right.
**Tests**: `python -B -m pytest -q -p no:cacheprovider tests/e2e/test_g4_latest_cli_offline.py`
**Status**: complete

### Phase 5:集中责任 + 集中验收 — Status: complete
**Goal**: run the card's single responsibility command; Ruff/type-check only modified files;
verify original-repo owner status + owner file SHAs unchanged; clean owned scratch only.
**Success Criteria**: exit code recorded with real counts; owner protection proven.
**Tests**: responsibility command in §6 of the card.
**Status**: complete

### Phase 6: Handoff — Status: complete
**Goal**: deliver `HANDOFF.md`, `handoff.json`, `main_wiring.md`, `latest_request_contract.md`,
golden request/response JSON; commit on `codex/g4-sid-latest`.
**Success Criteria**: `handoff.json` matches `g4-handoff/1` with real values, no placeholders.
**Tests**: n/a
**Status**: complete

## Decisions Made

| # | Decision | Why |
|---|---|---|
| D1 | `discovery_incomplete` / `bounded_discovery_empty` are raised as typed `CninfoApiError`/`AdapterError`, never a new `LoadState` member | `src/transport_states.py` is outside the card write set and its docstring forbids a fifth state |
| D2 | exact-mode pagination also advances on raw totals instead of `hasMore` alone | card §4.2 makes raw-total-driven pagination a general rule; year semantics stay untouched |
| D3 | latest window is a single `seDate` of `as_of.year-2-01-01 ~ as_of` | card §4.2 forbids per-year re-requests and reading local today |
| D4 | `fiscal_period` / `form_type` are strict type+trim validated and used as equality filters, not an enum whitelist | card says "尊重显式period/form_type" and "不能假填"; whitelisting could reject legitimate caller input |
| D5 | unsupported `document_kind` in latest mode fails before provider construction | card §4.1.4 scopes this card to annual/semi/quarterly only |
| D6 | duplicate announcement IDs with differing content raise `schema_drift` (non-retryable) with a diagnosing message | card forbids silent dict overwrite; `schema_drift` is the existing upstream-integrity code CWP already understands |
| D7 | PWF resolver mirror lives at `docs/implementation/.planning/g4-sid-latest/` while delivered artifacts live at `docs/implementation/g4-sid-latest/` | the pin in card §2 resolves `<PWF_PLAN_ROOT>/.planning/<PLAN_ID>` while card §7 names the delivery path; both must exist |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| `AdapterDiscoveryRequest.__init__() got an unexpected keyword argument 'mode'` (RED) | 1 | added trailing optional `mode`/`as_of_date`/`fiscal_period`/`form_type` |
| `TypeError: discover_announcements() got an unexpected keyword argument 'as_of_date'` (RED) | 1 | latest dispatch inside `CninfoAnnouncementClient.discover_announcements` |
| CLI built the provider before validating the request (RED) | 1 | `_discovery_request(value)` moved ahead of `_build_adapter` |
| duplicated `candidates = adapter.discover(...)` block left by an edit | 1 | removed the duplicate; discovered by two budget tests reporting exactly double usage |
| duplicated `test_latest_drops_*` definitions left by an edit | 1 | removed the stale second definitions; discovered by pytest taking the later one |
| `assert {c["document_kind"]} == {"semi_annual_report"]` bracket typo | 1 | fixed during the first E2E run |
| mypy reported 1 new error (`fiscal_year: int \| None`) | 1 | hoisted `if year is None: continue` above the constructor call — behaviourally identical for exact |
| first CWP consumption run reached the live cninfo org-id lookup and wrote `src/stock_orgid_mapping.json` | 1 | seed `stock_orgid_mapping.json` inside the card temp root so `get_org_id` hits the local cache; deleted the stray file; disclosed in HANDOFF §7 |
| `src/__pycache__` reappeared | 2 | added `PYTHONDONTWRITEBYTECODE=1` to both child envs (the remaining occurrence was an ad-hoc `python -c`, removed afterwards) |

## Next Step

None — lane handed off.  MAIN owns the `1.3.0` route bump, the GAP handling for
`discovery_incomplete` / `bounded_discovery_empty`, and the remaining
FF → ET → CWP wiring (see `main_wiring.md`).
