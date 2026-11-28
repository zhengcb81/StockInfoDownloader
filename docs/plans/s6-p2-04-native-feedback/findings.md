# Findings

Baseline 33377928b928cfcb92457c2e49a57eacd8391201. P2 uses the existing SID-owned receipt, checkpoints, native feedback publisher and cold reconciliation.

| Runtime root | Public operations | Existing contract preserved |
| --- | --- | --- |
| main.py | Batch by explicit security, list, config or test-case plan; serial and parallel modes | Human stderr, first terminal settlement and no-work result |
| -m src.company_wiki_adapter_cli | CNINFO exact/latest discover and staged fetch | Success JSON on stdout and final failure JSON on stderr; same budget usage and original file validation |
| -m src.feedback_owner | triage, repair, replay, report, reconcile, get-action, get-publication | Existing F4 envelope, idempotent first results, read-only reconcile |
| -m src.feedback_publish | republish and reconcile, optional --json same renderer | One existing stdout JSON document; original receipts stay immutable |
| Browser-free runtime artifact | Same published adapter module, in the defined restricted packaging | No Playwright or batch entry; no new runtime file or cross-owner dependency |

There is no SID-owned HTTP listener, worker service or scheduled entry in this release. Browser fallback and mapping are in-process calls under the batch scope. Diagnostics never decide if a business operation may proceed.

The native RED run failed seven cases. A separate 200 response with a deliberately shortened body reproduced a second integrity issue: the HTTP connection had already delivered headers but the adapter receipt still reported sent=unknown. The transport itself now supplies this fact. F4 cost status remains unknown when no original terminal settlement establishes a cost, including after a mid-body stop.
