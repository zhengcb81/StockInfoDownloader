"""Deterministic clock for provider-budget unit tests on every platform."""
from dataclasses import dataclass

import pytest


@dataclass
class AcquisitionTestClock:
    seconds: float = 100.0

    def monotonic(self) -> float:
        return self.seconds

    def advance(self, seconds: float) -> None:
        self.seconds += seconds


@pytest.fixture
def acquisition_clock(monkeypatch):
    clock = AcquisitionTestClock()
    monkeypatch.setattr("src.acquisition_budget.time", clock)
    return clock
