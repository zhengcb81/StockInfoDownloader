# Issue: verified-candidate-id-missing

- **issue_key**: `verified-candidate-id-missing`
- **owner**: `stockinfo-dl-simple`
- **status**: FIXED in `fb8c8ba` (`fix(sid): emit verified CNINFO listing identity`); regression-locked by this card.
- **machine ledger**: [verified-candidate-id-missing.json](verified-candidate-id-missing.json)
- **evidence**: [replay-samples.jsonl](../evidence/replay-samples.jsonl) · [real-cli-sample.jsonl](../evidence/real-cli-sample.jsonl) · [red-feedback-observation.log](../evidence/red-feedback-observation.log)

## Deviation (expected → actual)

`candidate-listing-identity`: expected `verified`, observed `missing`, `disposition=deviation`.
A discovery response returned a candidate that *looked* attributed but carried no native
`security_id`; the old parser filled a missing upstream `secCode` from the request stock
code, so ownership could be fabricated from the request alone. First evidence is pinned to
`case-byd-fy2024` (the local BYD FY2024 capture), and the ledger never overwrites it.

## Root cause / responsibility layer

Same-repo `src/cninfo_api.py` `_parse_announcement` + `src/company_wiki_adapter.py` `discover`:
a scoped CNINFO query was treated as proof that every returned row belongs to the requested
listing. The fix keeps only rows whose **native** `secCode` equals the request and emits
`DisclosureCandidate.security_id` from that native value.

## Legitimate same-kind control (NOT a defect)

A row with an empty `secCode` or a foreign `secCode` is a legitimate reject:
`classify_raw_record` yields `skipped-missing-code` / `skipped-different-stock` with
`disposition=expected`. These are proven by the fixture's three-row page and must not open
an issue. Ownership is never inferred from `source_url`, filename or request hint.

## Reproduce RED → GREEN (this repo, no network)

1. Minimal input: `tests/fixtures/feedback_observation/listing_identity_rows.json` (derived
   from `tests/fixtures/cninfo/byd_fy2024_announcement.json`).
2. RED fixture payload: `legacy_claim_verified` — a candidate with `security_id` removed.
   `classify_candidate_identity(...)` returns `actual=missing`, `disposition=deviation`,
   `issue_key=verified-candidate-id-missing`. The pre-fix wire omitted `security_id` entirely.
3. GREEN: native id present and matching → `actual=verified`, `disposition=expected`.
   Same mechanisms apply to the sibling listing/period by changing the request `security_id`
   and the row's native `secCode` together (the fixture's third row is exactly that control).
4. Locked by `tests/unit/test_feedback_observation.py` (28 tests) and the real CLI loopback
   sample above. Replay with the same version + same input + same deviation does not re-run
   the fetch: `needs_refetch()` is False once a terminal report exists.

## Consumer status

CWP ingestion/reuse acceptance is ROOT-owned (FF → ET → CWP chain). The SID candidate now
carries `security_id` in the 1.3.0 wire; downstream consumption is pending ROOT, not claimed here.
