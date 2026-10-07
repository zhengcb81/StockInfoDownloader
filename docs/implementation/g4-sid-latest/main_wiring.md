# main_wiring.md — what MAIN still has to do

This lane stops at the provider boundary.  It changes **only** StockInfoDLSimple
(`codex/g4-sid-latest`) and never touches company-wiki's production config,
install copies, or the shared plan.

## 1. Route version (required, blocking)

`JsonCommandAdapter._run` compares `response["adapter"]["version"]` with the
version it was constructed with and raises
`AdapterProcessError("… response identity/version mismatch")` on any difference.

| | value |
|---|---|
| SID `ADAPTER_NAME` | `stockinfo-cninfo` (unchanged) |
| SID `ADAPTER_VERSION` | `1.2.0` → **`1.3.0`** |
| wire `schema_version` | `1.0` (unchanged) |
| `config/source_acquisition.yaml` route version | **must be updated to `1.3.0`** before this branch is reachable |

Verified offline by `test_cwp_discover_bounded_consumes_the_1_3_0_response`,
which constructs a real `JsonCommandAdapter` at `1.3.0` (consumes the response)
and a second one at `1.2.0` (must raise `identity/version mismatch`).

MAIN must perform the same bump in `config/source_acquisition.yaml` and in any
install copy.  This lane does not edit those files.

## 2. Request fields company-wiki can now send

`SourceRequest` already carries everything the new path needs:

* `mode = "latest_as_of"` + `as_of_date` → latest discovery;
* `fiscal_year = null` is now legal (was a hard provider error);
* `fiscal_period` / `form_type`, when set, are honoured as equality filters;
* `mode = null`/absent keeps the historical exact behaviour.

Nothing on the company-wiki side has to change for `latest_as_of` to work
**once the route version is bumped**.  `allow_download`, `acquisition_budget`
and `acquisition_usage` shapes are untouched.

## 3. Errors MAIN must route (all non-retryable)

| `error.code` | meaning | recommended CWP handling |
|---|---|---|
| `discovery_incomplete` | page cap exhausted with raw records still uncovered | honest GAP — do **not** substitute an older local file as "latest" |
| `bounded_discovery_empty` | window fully covered, zero valid candidates | honest GAP with the window diagnostics in `error.message` |
| `budget_exceeded` | shared response-byte or deadline ceiling | report usage, retry only under a fresh budget |
| `schema_drift` | corrupt upstream page **or** conflicting duplicate announcement id | non-retryable upstream integrity failure |
| `upstream_unavailable` / `upstream_timeout` / `rate_limited` | genuine network/HTTP failures | existing retry logic |

`AdapterError` now carries `.code` and `.retryable`; the CLI prefers those
attributes over message parsing, so MAIN's
`AdapterProcessError.{error_code,retryable}` population becomes exact rather
than inferred.

## 4. Two pre-existing behaviours worth knowing

1. **org-id resolution launches a browser.**  `StockDownloader.mapping` builds
   `MappingManager(browser_strategy=self.browser, …)`, and `self.browser`
   eagerly starts Playwright.  company-wiki's `SourceRequest` carries no
   `org_id`, so every real CWP discovery goes down this path.  That is
   unchanged by this lane (exact mode already behaved this way), but MAIN
   should confirm the runtime has Playwright + Chromium available — otherwise a
   `latest_as_of` call fails at org-id resolution before any HTTP happens.
   The CLI accepts an optional provider-local `org_id` field that skips this
   path entirely; CWP may adopt it later without a provider change.
2. **Never fabricate a period.**  The provider only reports `FY`, `H1`, `Q1`,
   `Q3`.  A half-year report is never relabelled `Q2`, an annual report is
   never relabelled `Q4`, and an announcement whose title has no `20\d{2}年`
   is dropped rather than given a guessed year.

## 5. What this lane does *not* prove

* no live cninfo request was made by this lane (see `HANDOFF.md` § live status);
* no production CN download, no FF→ET→CWP latest wiring, no Dayu support;
* `mode=latest_as_of` beyond annual / semi-annual / quarterly is untested
  because it is explicitly out of scope.
