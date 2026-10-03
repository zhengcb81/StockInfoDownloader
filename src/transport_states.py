"""Typed transport load state shared between downloader, adapter, and CLI.

LoadState is the single source of truth distinguishing positive outcomes
(READY / CONFIRMED_EMPTY) from infrastructural or timing failures
(INFRASTRUCTURE_FAIL / TIMEOUT). It replaces the historical boolean
``success`` path for the three-state zero-link case where ``success=True / 0
files`` silently masked DNS/SPA resource failures.
"""

from __future__ import annotations

from enum import Enum


class LoadState(str, Enum):
    """Closure over the discovery/transport outcome.

    Members intentionally form a strict enum (exactly four) so that adapters,
    downloader and CLI have a single machine-readable contract; no caller may
    invent a fifth state without updating this enum and its tests.
    """

    READY = "ready"
    CONFIRMED_EMPTY = "confirmed_empty"
    INFRASTRUCTURE_FAIL = "infrastructure_fail"
    TIMEOUT = "timeout"


__all__ = ["LoadState"]
