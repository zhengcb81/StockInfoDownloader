# G4-SID-LATEST request / response contract (adapter 1.3.0)

Wire schema stays **`1.0`**.  Only the adapter behaviour version moves, from
`1.2.0` → `1.3.0`.

## 1. stdin request

The CLI still reads one JSON object on stdin.  Fields that company-wiki already
sends are unchanged; the four fields marked **new** are optional and tolerated.

| field | type | required | notes |
|---|---|---|---|
| `entity` | string | yes | trimmed, non-empty |
| `market` | string | no | ignored by this provider (always `CN`) |
| `security_id` | string | yes | trimmed, non-empty — 6-digit A-share code |
| `document_kind` | string | yes | `annual_report` \| `semi_annual_report` \| `quarterly_report` |
| `mode` | string \| null | **new** | `null`/absent ⇒ `exact`; `exact` \| `latest_as_of`; any other value is a hard error (never silently downgraded) |
| `fiscal_year` | int \| null | cond. | required and must be a real `int` (not `bool`) when `mode` is `exact`; may be `null` under `latest_as_of`, where it is only a *hint* and is never used as a filter |
| `as_of_date` | string | **new** | `YYYY-MM-DD`; required for `latest_as_of`; compact `YYYYMMDD` and slashed forms are rejected |
| `fiscal_period` | string | **new** | explicit hint, upper-cased; `FY`/`H1`/`Q1`/`Q3`; filters candidates by equality |
| `form_type` | string | **new** | explicit hint, lower-cased; `annual_report`/`interim_report`/`quarterly_report`; filters candidates by equality |
| `org_id` | string | no | provider-local; company-wiki never sends it. When present the adapter skips `StockDownloader.mapping` (so no org-id lookup and no browser construction) |
| `acquisition_budget` | object | cond. | the four existing fields only: `schema_version="1.0"`, `max_response_bytes`, `timeout_seconds`, `max_cost_usd` (decimal **string**). Absent ⇒ unbudgeted legacy call |

Validation runs **before** `_build_adapter(...)`, so a malformed request never
constructs the provider, its browser, or a socket.

Minimal `latest_as_of` request (synthetic sample; no live grant):

```json
{"entity":"示例公司","market":"CN","security_id":"600000","document_kind":"quarterly_report","mode":"latest_as_of","fiscal_year":null,"fiscal_period":null,"form_type":null,"as_of_date":"2026-06-01","org_id":"gshk0001211","acquisition_budget":{"schema_version":"1.0","max_response_bytes":1048576,"timeout_seconds":20,"max_cost_usd":"0"}}
```

## 2. Discovery windows

| mode | `seDate` sent to cninfo | year filter |
|---|---|---|
| `exact` | `{fy}-01-01~{fy+1}-12-31` (unchanged, byte-for-byte params) | candidate year **must equal** `fiscal_year` |
| `latest_as_of` | `{as_of.year-2}-01-01~{as_of}` — one window, one budget | no year filter; the year is taken **only** from the announcement title (`20\d{2}年`) |

Latest never reads the machine's local clock, never walks history year by year,
and never requests a fresh budget per page: one `ProviderAcquisitionBudget`
covers every page of one invocation (response bytes **and** the wall-clock
deadline).

## 3. Latest candidate filtering (all must hold)

* `document_kind` matches the request's kind;
* the title states a year — a record with no `20\d{2}年` is dropped, never
  back-filled from `as_of_date` or from the caller's year hint;
* `sec_code` equals `security_id`;
* `filing_date <= as_of_date`, where `filing_date` is the **UTC** calendar date
  of the announcement epoch-millisecond timestamp (midnight UTC is the boundary);
* the title is non-empty and `adjunctUrl` yields a real `transport_url`;
* `摘要` companions stay excluded by the adapter's default safety tokens;
* explicit `fiscal_period` / `form_type` hints match when supplied.

The provider returns the **whole** bounded candidate set, sorted by
`candidate_id`, with distinct announcement IDs.  Two payloads for the same
announcement ID that disagree on content raise a non-retryable failure instead
of silently overwriting.  Two different IDs for the same period are both
returned — target selection stays company-wiki's job.

## 4. Terminal outcomes

| situation | exit | `error.code` | `error.retryable` |
|---|---|---|---|
| page cap reached while raw records remain uncovered | 1 | `discovery_incomplete` | `false` |
| window fully covered, zero valid candidates | 1 | `bounded_discovery_empty` | `false` |
| duplicate announcement id with conflicting payloads | 1 | `schema_drift` | `false` |
| response-byte or deadline ceiling hit | 1 | `budget_exceeded` | `false` |
| malformed request / unknown mode / bad date | 1 | `upstream_unavailable` | `false` |
| upstream DNS/timeout/429/5xx | 1 | `upstream_unavailable` / `upstream_timeout` / `rate_limited` | `true` |

`schema_drift` still covers structurally corrupt upstream pages (missing
`totalRecordNum`, non-list `announcements`, …).  In `latest_as_of` a page whose
*structure* cannot be interpreted is reported as `discovery_incomplete`, because
that is exactly a window whose coverage can no longer be proven.

`discovery_incomplete` and `bounded_discovery_empty` are **latest-only**; an
exact request with nothing to return still exits `0` with `candidates: []`, as
before.

## 5. Success response (unchanged shape)

```json
{"schema_version":"1.0","status":"ok","adapter":{"name":"stockinfo-cninfo","version":"1.3.0"},"candidates":[ …DisclosureCandidate.to_dict()… ],"acquisition_usage":{"schema_version":"1.0","response_bytes":1234,"cost_usd":"0"}}
```

* exactly one JSON value on stdout, nothing else;
* `candidates[]` keys are unchanged (`candidate_id`, `provider`,
  `provider_document_id`, `identity_method`, `market`, `entity`, `title`,
  `source_url`, `document_kind`, `form_type`, `filing_date`, `fiscal_year`,
  `fiscal_period`, `language`, `amended`, `transport_url`);
* `acquisition_usage` is present whenever a budget was supplied, on success
  **and** on failure, and reports the bytes actually read.

Failures emit one JSON value on **stderr** with the same
`schema_version`/`status`/`adapter` envelope plus `error.{code,type,message,
retryable,acquisition_usage}`.

## 6. fetch

Unchanged: `fetch --staging-dir <dir>` takes the selected candidate plus
`adapter_payload_json`, stages exactly one PDF, and returns a
`StagedDownloadReceipt` with real `content_sha256`, `byte_size` and
`%PDF-` magic validation.  Discovery never downloads a PDF and never writes
into company-wiki paths.
