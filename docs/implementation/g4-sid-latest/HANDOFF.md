# HANDOFF — G4-SID-LATEST

**Lane** `G4-SID-LATEST` · **branch** `codex/g4-sid-latest` ·
**base** `8ed5fdde5e88c13470c120665ff3074a7f44a052` ·
**worktree** `C:/Users/郑曾波/Projects/_g4/SID-LATEST/StockInfoDLSimple`

Scope delivered: CNINFO **metadata discovery** for
`mode=latest_as_of` (annual / semi-annual / quarterly), with exact mode
preserved.  No download pipeline work, no new provider, no company-wiki writes.

---

## 1. RED → GREEN

### RED (`docs/implementation/g4-sid-latest/red_run.txt`)

```
python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py
→ exit 1, 38 failed, 7 passed
```

The 7 green ones were the exact-mode guards that had to stay green throughout.
The 38 failures were the real gaps, e.g.:

| RED symptom | root cause removed |
|---|---|
| `AdapterDiscoveryRequest.__init__() got an unexpected keyword argument 'mode'` | request had no mode/as-of fields |
| `CninfoAnnouncementClient.discover_announcements() got an unexpected keyword argument 'as_of_date'` | window was hard-wired to `{fy}-01-01~{fy+1}-12-31` |
| `provider must not be built` (pytest.fail fired) | the CLI constructed `StockDownloader` **before** validating the request |
| `assert '1.2.0' == '1.3.0'` | version not bumped |
| post-cutoff / future / wrong-year announcements returned as candidates | no cutoff, no security, no title-only-year filtering in latest |
| only page 1 fetched although `totalpages=2` | pagination stopped on `not page_records and not hasMore` |
| partial page cap reported as a normal result | no `discovery_incomplete` / `bounded_discovery_empty` |

No RED assertion was written against a faked CLI result: every one drives the
real `AdapterDiscoveryRequest` / `CninfoAnnouncementClient` / CLI code.

### GREEN (`docs/implementation/g4-sid-latest/green_run.txt`)

```
python -B -m pytest -q -p no:cacheprovider \
  tests/unit/test_g4_latest_discovery.py \
  tests/unit/test_company_wiki_adapter.py \
  tests/unit/test_company_wiki_adapter_cli.py \
  tests/unit/test_company_wiki_adapter_cli_budget.py \
  tests/unit/test_cninfo_api.py \
  tests/unit/test_cninfo_api_fixture_contract.py \
  tests/unit/test_cninfo_api_budget.py \
  tests/e2e/test_g4_latest_cli_offline.py
→ exit 0, 120 passed, 0 failed, 0 skipped
```

Full unit directory (`unit_run.txt`): **216 passed**, exit 0.

---

## 2. Exact mock layer (what is *not* real)

Two seams only, both at the bottom:

1. **`urllib.request.urlopen`**, replaced by
   `docs/implementation/g4-sid-latest/g4_bootstrap/sitecustomize.py` in the
   child process.  CPython imports it automatically because the directory is
   first on that child's `PYTHONPATH`.  It rewrites only
   `www.cninfo.com.cn` / `static.cninfo.com.cn` onto a `ThreadingHTTPServer`
   bound to `127.0.0.1:0`, then calls the **original** `urlopen`, so a genuine
   HTTP request/response happens over loopback.  With no `G4_LOOPBACK` set the
   rewrite refuses instead of reaching the public network.
2. **company-wiki source**, exported read-only with
   `git -C <cwp> archive --format=tar 5930a644… src/company_wiki` into the
   card's temp root, so the *committed* `JsonCommandAdapter` (not MAIN's
   uncommitted `ensure` code) is what consumes the response.

Everything above those seams is production code: the literal
`python -m src.company_wiki_adapter_cli discover --config <tmp config>`
entry point, `CninfoAnnouncementClient`, `StockInfoCompanyWikiAdapter`,
request validation, JSON serialization, budget accounting.
`FakeAdapter` is never used by the E2E.

The E2E additionally supplies an optional `org_id` in the stdin payload for the
direct CLI runs (a provider-local field company-wiki does not send), and seeds
`stock_orgid_mapping.json` for the company-wiki-driven run, so no org-id lookup
leaves the machine.

## 3. Page-completeness judgement

Raw, pre-filter facts only (`_PageMeta` = `total`, `raw_count`, `totalpages`,
`hasMore`), never "the filtered list came back empty".

Latest loop for one page:

1. `page_num >= totalpages` → covered;
2. else `covered_raw >= totalRecordNum` → covered;
3. else `raw_count == 0 and not hasMore` → upstream says no more pages;
4. otherwise fetch the next page, up to **5 pages × 30**.

After the loop, coverage is re-checked as `covered_raw >= totalRecordNum`.
Any unproven coverage ⇒ `discovery_incomplete`.  A `totalRecordNum` that
disagrees between pages is also `discovery_incomplete` (coverage is no longer
trustworthy), and a page whose structure cannot be parsed becomes
`discovery_incomplete` in latest mode.

Exact mode now advances on raw totals too (that is a bug fix for "page 1
filters to zero, `hasMore` absent"), while keeping its `totalpages` and
empty-page stops; the existing budget test that relies on exact continuing
after `totalRecordNum=0, hasMore=true` still passes unchanged.

## 4. Terminal errors

| code | raised by | retryable | when |
|---|---|---|---|
| `discovery_incomplete` | `CninfoApiError` → `AdapterError.code` | `false` | latest window coverage cannot be proven within the 5-page cap |
| `bounded_discovery_empty` | `AdapterError` | `false` | latest window fully covered, zero valid candidates (message carries `window_start..as_of`) |
| `schema_drift` | `CninfoApiError` / `AdapterError` | `false` | corrupt upstream page, **or** two payloads for one announcement ID that disagree |
| `budget_exceeded` | `AcquisitionBudgetExceeded` | `false` | shared response-byte / deadline ceiling |
| `upstream_unavailable` / `upstream_timeout` / `rate_limited` / `client_error` | `CninfoApiError` | `true`/`false` as before | genuine HTTP/DNS failures |

`AdapterError` now carries `.code` / `.retryable`; `_emit_failure` prefers them
over message text, so `AdapterProcessError.error_code` / `.retryable` on the
company-wiki side become exact.

`discovery_incomplete` and `bounded_discovery_empty` are **latest-only**.

## 5. Old exact compatibility

* positional construction
  `AdapterDiscoveryRequest(code, name, kind, fiscal_year, …)` unchanged;
* missing/null `mode` ⇒ `exact`;
* exact still demands a real integer `fiscal_year` (a `bool` is rejected), and
  still uses `{fy}-01-01~{fy+1}-12-31` bit-for-bit
  (`test_build_request_body_matches_capture_params_bit_for_bit` still green);
* exact still filters `year != fiscal_year`, still excludes `摘要`, still
  returns `candidates: []` with exit 0 for an empty result;
* `fiscal_period` / `form_type` are honoured in both modes **only** when the
  caller supplies them — legacy payloads do not, so nothing narrows;
* fetch keeps SHA-256 / byte-size / `%PDF-` magic validation and the existing
  exact + budget regressions.

## 6. Adapter version

| | |
|---|---|
| wire `schema_version` | `1.0` (unchanged) |
| `ADAPTER_NAME` | `stockinfo-cninfo` (unchanged) |
| `old_adapter_version` | `1.2.0` |
| `new_adapter_version` | **`1.3.0`** |

`config/source_acquisition.yaml` and any install copy must be bumped by MAIN —
`JsonCommandAdapter` validates name **and** version on every response.  This
lane does not touch production config or install copies.
See `main_wiring.md`.

## 7. Live status — what was NOT run

* **Optional anonymous official metadata probe: NOT RUN.**  No live cninfo
  request was made by this package, so no live-success claim is made.
* **External network requests of the final test suite: 0.**
* One incident during development, disclosed rather than hidden: the first run
  of the company-wiki consumption test reached
  `StockDownloader.mapping`, which resolves the org id through
  `OrgIdCrawler._query_api` and wrote `src/stock_orgid_mapping.json`
  (`600000 → gssh0600000`, `source=auto`, `confidence=0.7`).  The test now
  seeds a local `stock_orgid_mapping.json` inside its own temp root, so
  `get_org_id` returns from cache and never issues that lookup.  The stray file
  was deleted; the run is now loopback-only.
* Loopback HTTP per full suite run: **19** requests (one `127.0.0.1`
  `ThreadingHTTPServer`, assertions per test: 1/1/1/2/5/1/1/1/0/0/2/2/2).
* No paid API, no FMP, no LLM, no live PDF download, no browser-driven page
  scraping.

## 8. Protected state & cleanup

* Original repo `StockInfoDLSimple/v2-clean-rewrite` was never written to.
  Its `git status --short` is byte-identical to the session-start capture
  (11 tracked owner modifications + `a_share_companies.txt`, `companies.txt`,
  `scripts/`), with SHA-256s recorded in `owner_protection.txt`.
* No `reset` / `clean` / `stash` was run anywhere; no owner file was copied into
  the new baseline; no owner script was used as an entry point.
* Scratch removed: the card's `si4l-*` temp roots (subprocess cwd, config,
  logs, staging, CWP export, browser download dir), `$TEMP/g4basemypy-*`,
  `$TEMP/g4-cwp-export`, `_tmp/g4_adapter_process_export.py`, plus worktree
  caches created by this run (`logs/`, `src/__pycache__/`,
  `g4_bootstrap/__pycache__/`, `.mypy_cache/`, `.ruff_cache/`).  Deletion was
  guarded on the `si4l-` path component and every removed worktree path was
  created during this session.
* `docs/implementation/.planning/g4-sid-latest/` is an uncommitted local mirror
  of `task_plan.md` / `findings.md` / `progress.md` so the pinned
  `PLAN_ID=g4-sid-latest` + `PWF_PLAN_ROOT=<worktree>/docs/implementation`
  resolver resolves; the delivered copies live in
  `docs/implementation/g4-sid-latest/`.

## 9. Verification commands

```powershell
python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_cninfo_api.py tests/unit/test_cninfo_api_fixture_contract.py tests/unit/test_cninfo_api_budget.py tests/e2e/test_g4_latest_cli_offline.py
ruff check src/company_wiki_adapter.py src/company_wiki_adapter_cli.py src/cninfo_api.py tests/unit/test_g4_latest_discovery.py tests/e2e/test_g4_latest_cli_offline.py
ruff format --check <same five files>
mypy src/company_wiki_adapter.py src/company_wiki_adapter_cli.py src/cninfo_api.py
```

`ruff` exits 0 (`ruff_run.txt`).  `mypy` exits 1 with **12** errors, the
same 12 the base commit `8ed5fdd` produces — four in `browser.py`, four in
`orgid.py`, one in `mapping.py` (files this lane never opened for editing) and
three in untouched statements whose line numbers moved.  No new type error was
introduced (`mypy_run.txt`).

## 10. Still open for MAIN

1. Bump the company-wiki route version to `1.3.0` and re-run the real
   `ensure`/acquisition wiring against this branch (see `main_wiring.md`).
2. Handle `discovery_incomplete` / `bounded_discovery_empty` as honest GAPs —
   never let an older local file be presented as "latest".
3. Complete the FF → ET → CWP → latest-download chain; this lane only proves
   metadata discovery plus one controlled loopback fetch.
4. Optional live cninfo metadata probe (≤ 2 requests, 3 MiB, 60 s, $0) was
   **not** run — run it from MAIN if a live receipt is required.
5. `mode=latest_as_of` is only wired for annual / semi-annual / quarterly.
6. Confirm Playwright + Chromium exist on the runtime that drives the provider
   through company-wiki, because `StockDownloader.mapping` constructs the
   browser eagerly (pre-existing behaviour, unchanged by this lane).
