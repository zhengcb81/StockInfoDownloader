# G4 SID MAIN acceptance — 2026-10-07

Delivery 201a8f0 (implementation d958a0f) is accepted with a narrow MAIN pagination correction. The target remains the existing v2-clean-rewrite execution branch in the StockInfoDownloader-named remote; the legacy StockInfoDownloader main is outside scope.

## Defect and TDD

All three added completeness counterexamples first failed: a final page with fewer records than totalRecordNum, hasMore after zero records, and hasMore after the declared final page. latest_as_of now requires terminal count/page/hasMore facts to agree, otherwise discovery_incomplete is non-retryable. Exact-year semantics remain unchanged.

The committed CWP route test first failed all four cases with the old route's missing bounded capability. MAIN then committed CWP route identity 1.3.0 and capability=true at df7d7ba58955e224c1799355f479ad5378ef38a7, keeping the canonical provider execution root. The same real JsonCommandAdapter/child CLI/loopback HTTP tests now pass: previous-year latest, five-page limit, covered-but-empty and contradictory final page. Failure usage is charged to the shared budget and no candidate/fetch is produced. Fresh exported modules are removed after each test so a previous checkout cannot conceal a version mismatch.

## Concentrated final verification

127 passed, 27.02 seconds; includes the delivery's 120 responsibility cases, three new regression cases and four committed-route integration cases. Ruff check and format check passed for the changed provider/CLI/test scope. The earlier 13 setup errors were MAIN's missing pytest basetemp parent, not provider failures; creating that owned parent resolved them. No new mypy gate is imposed: the delivery/base both have the same 12 pre-existing errors. This repo has no CI workflow; no remote CI success is claimed.

```powershell
$env:G4_CWP_REPO='C:/Users/郑曾波/Projects/company-wiki'
$env:G4_CWP_COMMIT='df7d7ba58955e224c1799355f479ad5378ef38a7'
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
# Create the parent of --basetemp first; use an owned short test root.
python -B -m pytest -q -p no:cacheprovider tests/unit/test_g4_latest_discovery.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_cninfo_api.py tests/unit/test_cninfo_api_fixture_contract.py tests/unit/test_cninfo_api_budget.py tests/e2e/test_g4_latest_cli_offline.py
```

No live cninfo requests, paid API/LLM calls or production data writes. Original user changes are preserved. Synthetic inputs and exports live only in the card-owned test roots and are cleaned after use. Worker history and receipts remain available.

## Remaining MAIN work

Full single-intent latest ensure and FF/ET/CWP download-to-ingest/reuse wiring is still unfinished G2-12, not part of this acceptance. This package establishes CN annual/semiannual/quarterly discovery and the committed CWP provider contract; it does not claim a complete latest acquisition chain or US/HK capability. Overall goal remains paused.
