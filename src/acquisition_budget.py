"""Small provider-local budget contract for company-wiki subprocess calls.

This module intentionally has no dependency on company-wiki. The parent sends
remaining limits for one command invocation; the provider charges HTTP response
body bytes while reading them and reports the measured usage in its JSON reply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import math
import time
from typing import Any


class AcquisitionBudgetExceeded(RuntimeError):
    """The provider reached a response-byte or wall-clock limit."""


def _cost(value: Any) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("max_cost_usd must be decimal text")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("max_cost_usd must be finite and non-negative") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("max_cost_usd must be finite and non-negative")
    return amount


@dataclass(slots=True)
class ProviderAcquisitionBudget:
    max_response_bytes: int
    timeout_seconds: float
    max_cost_usd: str
    response_bytes_used: int = 0
    _deadline: float = field(init=False, repr=False)
    _max_cost: Decimal = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_response_bytes, bool)
            or not isinstance(self.max_response_bytes, int)
            or self.max_response_bytes <= 0
        ):
            raise ValueError("max_response_bytes must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be finite and positive")
        if (
            isinstance(self.response_bytes_used, bool)
            or not isinstance(self.response_bytes_used, int)
            or not 0 <= self.response_bytes_used <= self.max_response_bytes
        ):
            raise ValueError("response_bytes_used is outside the byte limit")
        self._max_cost = _cost(self.max_cost_usd)
        self._deadline = time.monotonic() + float(self.timeout_seconds)

    @classmethod
    def from_payload(cls, payload: Any) -> ProviderAcquisitionBudget:
        if not isinstance(payload, dict) or set(payload) != {
            "schema_version",
            "max_response_bytes",
            "timeout_seconds",
            "max_cost_usd",
        }:
            raise ValueError("acquisition_budget must have the exact 1.0 fields")
        if payload.get("schema_version") != "1.0":
            raise ValueError("acquisition_budget schema_version must be 1.0")
        return cls(
            max_response_bytes=payload["max_response_bytes"],
            timeout_seconds=payload["timeout_seconds"],
            max_cost_usd=payload["max_cost_usd"],
        )

    @property
    def remaining_response_bytes(self) -> int:
        return self.max_response_bytes - self.response_bytes_used

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    def ensure_open(self) -> None:
        if self.remaining_seconds <= 0:
            raise AcquisitionBudgetExceeded("acquisition deadline exceeded")

    def consume_response_bytes(self, count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("response byte count must be a non-negative integer")
        if count > self.remaining_response_bytes:
            raise AcquisitionBudgetExceeded("acquisition response-byte budget exceeded")
        self.response_bytes_used += count
        # Record bytes already returned by the socket even if the absolute
        # deadline elapsed during this read, then fail the operation.
        self.ensure_open()

    def usage(self) -> dict[str, str | int]:
        return {
            "schema_version": "1.0",
            "response_bytes": self.response_bytes_used,
            # CNINFO is a free public disclosure endpoint; no paid request is made.
            "cost_usd": "0",
        }


__all__ = ["AcquisitionBudgetExceeded", "ProviderAcquisitionBudget"]
