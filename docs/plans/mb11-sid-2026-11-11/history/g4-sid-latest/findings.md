# G4-SID-LATEST — findings

## Frozen input / output contract (read from real sources)

### CLI (`src/company_wiki_adapter_cli.py`)
- entry: `python -m src.company_wiki_adapter_cli {discover,fetch} [--config PATH] [--staging-dir PATH]`
- stdin: one JSON object. Success writes exactly one JSON value to stdout (no trailing newline),
  `schema_version="1.0"`, `status="ok"`, `adapter.{name,version}`, plus `candidates`/`receipt`
  and optional `acquisition_usage`.
- failure: one JSON value on **stderr**, `status="failed"`, `error.{code,type,message,retryable}`
  and `error.acquisition_usage` when a budget was parsed; exit code 1.
- today: budget is parsed **before** `_build_adapter`, but request validation (`security_id`,
  `fiscal_year`) happens **after** → bad request input still constructs the provider (RED).
- today `mode` / `as_of_date` / `fiscal_period` / `form_type` are ignored entirely.

### Request dataclass (`src/company_wiki_adapter.py`)
- `AdapterDiscoveryRequest` is frozen; positional order
  `stock_code, stock_name, document_kind, fiscal_year, org_id, suffix, allowed_keywords,
  excluded_keywords, max_pages`. `fiscal_year` must be `int` (bool rejected), 1990..2200.
- `ADAPTER_VERSION = "1.2.0"`, `ADAPTER_NAME = "stockinfo-cninfo"`.
- `discover()` builds `candidates` in a **dict keyed by candidate_id → silent overwrite**,
  then `tuple(sorted(candidates))`.
- default excluded token `("摘要",)`; `_report_metadata(title)` yields
  `(kind, year, form_type, period, amended)` with period ∈ {FY, H1, Q1, Q3, UNKNOWN}.
  Year comes **only** from the `20\d{2}年` match on the title — never from the request or today.

### API client (`src/cninfo_api.py`)
- `_build_request_body` window is fixed to `{fiscal_year}-01-01~{fiscal_year+1}-12-31`.
- `discover_announcements` loops `max_pages` × 30 and stops on
  `page_num >= totalpages` **or** `not page_records and not hasMore` — i.e. a page that filters to
  0 records while `hasMore` is absent stops pagination even when `totalpages` says otherwise.
- `_filter_announcements_from_response` re-filters on `year != fiscal_year or kind != document_kind`
  → the API layer can never return a different year, which is exactly the CWP gap.
- `CninfoApiError` already carries `error_code` + `retryable` (+ `http_status`); codes in use:
  `upstream_unavailable`, `upstream_timeout`, `rate_limited`, `client_error`, `schema_drift`,
  `content_too_small`, `pdf_magic_invalid`, `transport_url_host_not_allowed`.
- bounded reads: `_copy_bounded_response` charges `budget.consume_response_bytes` per chunk,
  refuses declared-oversize before reading, and raises `AcquisitionBudgetExceeded` (never converted
  to an empty result). Shared across pages because one budget object is threaded through.

### Budget (`src/acquisition_budget.py`)
- exactly four payload fields `schema_version/max_response_bytes/timeout_seconds/max_cost_usd`,
  `max_cost_usd` is decimal text; `usage()` = `{schema_version, response_bytes, cost_usd:"0"}`.
- one deadline per invocation (`time.monotonic() + timeout_seconds`) → bytes **and** deadline are
  shared by every page of one discover call.

### LoadState (`src/transport_states.py`) — OUTSIDE write set
- strictly four members, docstring forbids adding a fifth without updating the enum and its tests.
  ⇒ `discovery_incomplete` / `bounded_discovery_empty` must be **typed errors**, not a new state.

## CWP side (read-only export of committed `5930a644453ed46494c2c83c5ecfb97767fa9492`)
- `SourceRequest.to_dict()` always carries `entity, document_kind, as_of_date, market, security_id,
  form_type, fiscal_year, fiscal_period, language, provider, provider_document_id, mode,
  allow_download, schema_version`. `mode ∈ {None, "exact", "latest_as_of"}`; `None` = legacy exact.
  `fiscal_year` may be `null`. `as_of_date` is a canonical `YYYY-MM-DD`.
- `JsonCommandAdapter.discover_bounded(request, budget)`:
  - injects `acquisition_budget = {schema_version, max_response_bytes: remaining,
    timeout_seconds: min(...), max_cost_usd: str(remaining)}` — the **remaining** allowance,
  - requires `response.acquisition_usage` with exactly `{schema_version, response_bytes, cost_usd}`
    and charges it back,
  - on non-zero exit parses the **last stderr line** as the structured 1.0 failure and takes
    `error.code` / `error.retryable` / `error.acquisition_usage` and `adapter.version`,
  - requires `adapter.name == self.name` and `adapter.version == self.version` → **route version
    must be bumped to 1.3.0 by MAIN** or `discover_bounded` raises identity mismatch.
- `JsonCommandAdapter._candidate` reads `fiscal_year` (required), `fiscal_period`, `form_type`,
  `filing_date`, `amended` from the candidate dict → `DisclosureCandidate.to_dict()` shape is the
  wire contract and must not change.

## Owner protection (original repo `v2-clean-rewrite`, base `8ed5fdd`)
```
 M README.md, config_template.json, main.py, src/browser.py, src/downloader.py,
   src/logger.py, src/mapping.py, src/models.py, tests/e2e/official_e2e_test.py,
   tests/unit/test_downloader.py, tests/unit/test_official_e2e_contract.py
?? a_share_companies.txt, companies.txt, scripts/
```
11 tracked owner edits + 3 untracked entries — must be byte-identical after this card.

## Write set actually used
- `src/company_wiki_adapter.py`, `src/company_wiki_adapter_cli.py`, `src/cninfo_api.py`
- `tests/unit/test_company_wiki_adapter.py`, `test_company_wiki_adapter_cli.py`,
  `test_company_wiki_adapter_cli_budget.py`, `test_cninfo_api.py`,
  `test_cninfo_api_fixture_contract.py`, `test_cninfo_api_budget.py`
- new `tests/unit/test_g4_latest_discovery.py`, new `tests/e2e/test_g4_latest_cli_offline.py`,
  new fixtures only under `tests/fixtures/g4_latest/`
- `docs/implementation/g4-sid-latest/**` (+ PWF resolver mirror `docs/implementation/.planning/g4-sid-latest/`)

## Facts that shape the design
1. `LoadState` cannot grow → incompleteness must be an exception.
2. `test_cli_budgeted_real_discovery_path_reports_http_body_bytes` requires exact mode with
   `totalRecordNum=0` to stay exit 0 with `candidates == []` → `bounded_discovery_empty`
   is **latest-only**.
3. `test_build_request_body_matches_capture_params_bit_for_bit` pins the exact-mode body
   bit-for-bit → `seDate` must stay `{fy}-01-01~{fy+1}-12-31` for exact.
4. `test_fetch_writes_only_allocated_staging_and_returns_hash_receipt` asserts
   `receipt.adapter_version == "1.2.0"` → responsibility test must move to 1.3.0 with the constant.
5. `.gitignore` ignores `*.json` except `tests/**/*.json` → `handoff.json` under
   `docs/implementation/` needs `git add -f`; **`.gitignore` is not in the write set, so it is not
   edited.**
6. `StockDownloader.__init__` lazily creates a browser but eagerly runs
   `FailedDownloadLogger()` → `logs/` relative to cwd; E2E therefore runs with cwd inside its own
   `si4l-*` temp root and `PYTHONPATH` pointing at the worktree.
7. `src.logger` attaches a stdout `StreamHandler` at import; the CLI already re-points it to
   stderr, which is why the offline E2E can assert stdout parses as one JSON value.


## Verified during GREEN (addendum)

1. `JsonCommandAdapter` from commit `5930a644…` imports cleanly from a
   `git archive` export of `src/company_wiki`; the minimal importable closure is
   the published `company_wiki` package (210 files, ~2.7 MB), not a hand-picked
   subset — `adapter_process` pulls `acquisition` → `resolver` → `service`/`store`.
2. `SourceRequest.to_dict()` carries **no** `org_id`, so a company-wiki-driven
   discovery always falls through to `StockDownloader.mapping`, which eagerly
   constructs `PlaywrightBrowser`. The CLI therefore accepts an optional
   provider-local `org_id`, and the E2E seeds a local mapping cache instead.
3. `date.fromisoformat` accepts the compact `YYYYMMDD` form on Python 3.11+, so
   `as_of_date` is round-tripped through `parsed.isoformat()` to reject it.
4. Exact-mode pagination had a latent bug: `not page_records and not hasMore`
   stopped the loop when the *filtered* page was empty even though
   `totalpages` promised more — the same failure mode the latest path had to
   avoid, so the raw-total rule was applied to both modes.
5. `.gitignore`'s `*.json` rule means `handoff.json` under `docs/` needs
   `git add -f`; `.gitignore` itself stays untouched.
6. `StockDownloader.mapping` reaches `browser_strategy=self.browser` before
   `MappingManager` is even constructed, so any org-id resolution starts
   Chromium regardless of whether the mapping cache hits.
