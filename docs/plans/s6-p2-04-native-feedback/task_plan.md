# S6 P2-04 StockInfoDLSimple native observability

The original candidate was stopped at independent review. Both findings are repaired and passed native Windows focused tests. The two prior corrections passed independent review. The next review found a folded authentication continuation leak in native argument refusals. The common presentation fix is now implemented. Baseline 33377928b928cfcb92457c2e49a57eacd8391201 in the isolated SID worktree.

1. Freeze entrypoint inventory and owned state semantics. Add RED native B-04 fixtures.
2. Build one CLI logging scope and process-safe diagnostic log writer. Route failures through original stages and causal exception types.
3. Verify native no-window Windows and POSIX offline tests, owner cold recovery and zero duplicate dispatch. Hand off the exact commit for independent review.

## Next Step

Verify the corrected candidate in the guarded native entrypoint suite and send this exact source to independent recheck. The first candidate full-matrix receipts remain historical. Publish only after ROOT accepts the recheck and normal owner release tests.
