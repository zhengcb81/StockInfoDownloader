# Issue: batch-missed-success

- **issue_key**: `batch-missed-success`
- **owner**: `stockinfo-dl-simple`
- **status**: RECORD-ONLY / ROOT-owned combination (`downloader.py` verification); SID provider is not the responsible layer.
- **machine ledger**: [batch-missed-success.json](batch-missed-success.json)
- **evidence**: [replay-samples.jsonl](../evidence/replay-samples.jsonl) · [review.md B3](../../mb11-sid-2026-11-11/review.md)

## Deviation (expected → actual)

`staged-fetch-receipt`: expected `staged`, observed `missed-success`, `disposition=deviation`.
The historical validator's `_verify_downloads` read only the success path: with two candidates
and one failed download, the batch still reported `success=True` / `verification.ok=True` even
though `logs/failed_downloads.json` recorded the failure. First evidence pinned to
`case-review-b3`.

## Root cause / responsibility layer

Neighbour concern in the legacy `src/downloader.py` batch verification, already fixed in
`fb8c8ba` ancestry by the MB-SID card (typed `VerificationIssue` folded into `success`).
For the **provider** (`company_wiki_adapter_cli`) the honest rule is different and is what
this card locks: the CLI surfaces only what **this invocation** can prove — one candidate
and one receipt — with a stable terminal result. A zero-candidate or failed result is never
silently promoted to success.

## Legitimate same-kind control (NOT a defect)

A batch that completes with one legal candidate and a matching staged receipt is `verified` /
`staged`, `disposition=expected`. A row skipped because it is a summary (`摘要`) or belongs
to another listing is a legitimate filter, not a missed success. Absence of a receipt after a
killed process is `unknown`, not a fabricated success — see `test_started_without_terminal_observation_stays_unknown`.

## Reproduce RED → GREEN (this repo, no network)

1. Inject a two-item batch in which one item fails; the old verifier reported success (RED,
   documented in `review.md` B3). The provider CLI now emits a single terminal observation
   for the one action it actually performed.
2. GREEN: `feedback.finish("staged", ...)` only after the adapter returns a real
   `StagedDownloadReceipt` with measured `byte_size` and `content_sha256`; otherwise the
   action terminates as a typed error or `unknown`. Locked by
   `tests/unit/test_feedback_observation.py` (`test_started_without_terminal_observation_stays_unknown`,
   budget-failure terminal).
3. A sibling period/listing reproducing the same "partial failure reported as overall
   success" must bind to this same card (same `issue_key`), not open a second one.

## Consumer status

Full cross-repo batch semantics (FF → ET → CWP) belong to ROOT. This repo contributes the
provider's honest single-action terminal observation and the desensitized samples; it does
not claim the downstream chain is verified.
