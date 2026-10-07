# G4-SID-LATEST — progress

**MAIN latest status:** accepted and published on v2-clean-rewrite; code eb8495ceb76892ff6f4a95889b6a19f0a78d769c. Final 127 responsibility/real CLI offline cases pass (27.02s), including three completeness regressions and four real committed CWP route cases. CWP route df7d7ba is published. Full unified ensure/FF/ET/CWP ingest/reuse remains MAIN G2-12; overall goal remains paused. See [MAIN_ACCEPTANCE](MAIN_ACCEPTANCE.md). The earlier worker status below is historical.

## 2026-10-07 — Session 1: worktree, pin, baseline read

- Verified original repo `C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`:
  branch `v2-clean-rewrite` @ `8ed5fdd`, 11 tracked owner modifications + 3 untracked entries.
  No reset/clean/stash performed.
- Verified branch `codex/g4-sid-latest` and path `Projects/_g4/SID-LATEST/StockInfoDLSimple`
  were free; created the worktree from `8ed5fdde5e88c13470c120665ff3074a7f44a052`.
- Pinned planning-with-files: `PLAN_ID=g4-sid-latest`,
  `PWF_PLAN_ROOT=<worktree>/docs/implementation` → resolver returns
  `<worktree>/docs/implementation/.planning/g4-sid-latest`. Deliverables additionally live at
  `<worktree>/docs/implementation/g4-sid-latest/` per card §7.
- Read the three production sources, the budget/transport modules and all six responsibility tests.
- Read-only export of CWP commit `5930a644…` (`adapter_process.py`, `resolver.py`,
  `download_budget.py`, `acquisition.py`) into `$TEMP/g4-cwp-export` — deleted after use.
- No repo AGENTS.md exists in the original repo or its parents → no extra in-repo rules apply.

Status: Phase 0 complete, Phase 1 complete, Phase 2 in progress.


## 2026-10-07 — Session 2: RED → GREEN

- RED: `tests/unit/test_g4_latest_discovery.py` written first, 38 failed / 7 passed
  against unmodified `src/` (`red_run.txt`). The 7 green cases were the exact-mode
  guards that had to stay green.
- GREEN: trailing optional `mode`/`as_of_date`/`fiscal_period`/`form_type` on
  `AdapterDiscoveryRequest`; latest dispatch + `_PageMeta` raw-page facts +
  `_discover_latest` coverage proof in `cninfo_api`; typed `AdapterError.code/
  retryable`; request validation moved ahead of `_build_adapter`;
  `ADAPTER_VERSION` 1.2.0 → 1.3.0.
- Responsibility command: **120 passed, exit 0** (`green_run.txt`).
  Full `tests/unit`: **216 passed** (`unit_run.txt`).
- Offline CLI E2E (`tests/e2e/test_g4_latest_cli_offline.py`, 13 cases) drives the
  real `-m` entry through `g4_bootstrap/sitecustomize.py` + a `127.0.0.1`
  `ThreadingHTTPServer`, and consumes the 1.3.0 response with company-wiki's
  committed `5930a644…` `JsonCommandAdapter.discover_bounded`.
- Ruff clean (`ruff_run.txt`); mypy 12 errors, byte-identical to the `8ed5fdd`
  baseline (`mypy_run.txt`).
- Disclosed incident: the first CWP-consumption run performed one live cninfo
  org-id lookup via `StockDownloader.mapping`. Fixed by seeding a local
  `stock_orgid_mapping.json` inside the card temp root; the final suite is
  loopback-only (19 localhost requests/run, 0 external).
- Scratch cleaned: `si4l-*` temp roots, `$TEMP/g4basemypy-*`,
  `$TEMP/g4-cwp-export`, `_tmp/g4_adapter_process_export.py`, `logs/`,
  `src/__pycache__`, `.mypy_cache`, `.ruff_cache`, bootstrap `__pycache__`.
- Original repo untouched: status byte-identical to the session-start capture,
  SHAs in `owner_protection.txt`.
- Implementation commit `d958a0f` on `codex/g4-sid-latest`.

Status: Phases 0-5 complete, Phase 6 in progress (handoff commit + push).


## 2026-10-07 — Session 3: acceptance and delivery

- Final responsibility run after all commits: exit 0, **120 passed**, 14.61 s
  (committed receipt `green_run.txt` records the identical command at 14.51 s).
- Original repo `v2-clean-rewrite` status re-checked: byte-identical to the
  session-start capture, 11 tracked owner modifications + 3 untracked entries.
- Worktree clean apart from the intentional, uncommitted
  `docs/implementation/.planning/` resolver mirror; no `si4l-*` temp root
  remains, no `logs/`, `src/__pycache__`, `src/stock_orgid_mapping.json`,
  `.mypy_cache` or `.ruff_cache`.
- Delivered commits on `codex/g4-sid-latest`, pushed to `origin`:
  `d958a0f` (implementation), `2d8919a` (contract/wiring/handoff docs),
  `0c29a93` (machine `handoff.json`), plus this plan close-out.
- Phase 6 complete; the lane is handed to MAIN.
