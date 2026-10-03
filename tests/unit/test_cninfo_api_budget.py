"""Budgeted CNINFO HTTP reads must stop at the shared response-byte cap."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


class _ChunkedResponse:
    def __init__(self, body: bytes, *, content_length: bool = True) -> None:
        self.body = body
        self.offset = 0
        self.status = 200
        self.headers = {"Content-Type": "application/json"}
        if content_length:
            self.headers["Content-Length"] = str(len(body))
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        assert size >= 0, "bounded provider must never call unbounded read()"
        self.read_sizes.append(size)
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def __enter__(self) -> _ChunkedResponse:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _budget(*, byte_limit: int, seconds: float = 10.0):
    from src.acquisition_budget import ProviderAcquisitionBudget

    return ProviderAcquisitionBudget(
        max_response_bytes=byte_limit,
        timeout_seconds=seconds,
        max_cost_usd="0",
    )


def test_bounded_discovery_streams_json_and_charges_exact_response_bytes(monkeypatch):
    from src.cninfo_api import CninfoAnnouncementClient

    body = (
        b'{"totalRecordNum":0,"announcements":[],"padding":"'
        + b"x" * 200_000
        + b'"}'
    )
    response = _ChunkedResponse(body)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    budget = _budget(byte_limit=len(body))

    payload = CninfoAnnouncementClient()._post_json(b"page=1", budget=budget)

    assert payload["totalRecordNum"] == 0
    assert len(response.read_sizes) > 1
    assert all(size > 0 for size in response.read_sizes)
    assert budget.response_bytes_used == len(body)
    assert budget.usage() == {
        "schema_version": "1.0",
        "response_bytes": len(body),
        "cost_usd": "0",
    }


def test_bounded_discovery_refuses_declared_oversize_before_read(monkeypatch):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.cninfo_api import CninfoAnnouncementClient

    body = b'{"totalRecordNum":0,"announcements":[]}'
    response = _ChunkedResponse(body)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    budget = _budget(byte_limit=len(body) - 1)

    with pytest.raises(AcquisitionBudgetExceeded):
        CninfoAnnouncementClient()._post_json(b"page=1", budget=budget)

    assert response.read_sizes == []
    assert budget.response_bytes_used == 0


def test_bounded_discovery_shares_bytes_across_pages_and_stops_before_next_request(
    monkeypatch,
):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.cninfo_api import CninfoAnnouncementClient

    body = (
        b'{"totalRecordNum":0,"announcements":[],"totalpages":2,'
        b'"hasMore":true}'
    )
    opened: list[_ChunkedResponse] = []

    def open_response(*_args, **_kwargs):
        response = _ChunkedResponse(body)
        opened.append(response)
        return response

    monkeypatch.setattr("urllib.request.urlopen", open_response)
    budget = _budget(byte_limit=len(body))

    with pytest.raises(AcquisitionBudgetExceeded):
        CninfoAnnouncementClient().discover_announcements(
            stock_code="002594",
            org_id="gshk0001211",
            document_kind="annual_report",
            fiscal_year=2024,
            max_pages=2,
            budget=budget,
        )

    assert len(opened) == 1
    assert budget.response_bytes_used == len(body)


def test_deadline_elapsed_during_read_still_charges_returned_bytes(monkeypatch):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.cninfo_api import CninfoAnnouncementClient
    import time

    response = _ChunkedResponse(b"{}")
    response.read = lambda size=-1: (time.sleep(0.02), b"{}")[1]  # type: ignore[method-assign]
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    budget = _budget(byte_limit=10, seconds=0.005)

    with pytest.raises(AcquisitionBudgetExceeded):
        CninfoAnnouncementClient()._post_json(b"page=1", budget=budget)

    assert budget.response_bytes_used == 2


def test_bounded_pdf_stream_over_limit_removes_partial_file(monkeypatch, tmp_path: Path):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.cninfo_api import CninfoAnnouncementClient

    body = b"%PDF-" + b"x" * 200
    response = _ChunkedResponse(body, content_length=False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    budget = _budget(byte_limit=100)
    staging = tmp_path / "staging"

    with pytest.raises(AcquisitionBudgetExceeded):
        CninfoAnnouncementClient().fetch_pdf(
            "https://static.cninfo.com.cn/report.PDF",
            staging,
            expected_filename="report.pdf",
            budget=budget,
        )

    assert not (staging / "report.pdf.part").exists()
    assert not (staging / "report.pdf").exists()
    assert budget.response_bytes_used == 100
    assert all(0 < size <= 100 for size in response.read_sizes)


def test_bounded_pdf_success_writes_and_accounts_incrementally(monkeypatch, tmp_path: Path):
    from src.cninfo_api import CninfoAnnouncementClient

    from src import constants as C

    body = b"%PDF-" + b"x" * (C.MIN_FILE_SIZE + 100)
    response = _ChunkedResponse(body, content_length=False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    budget = _budget(byte_limit=len(body) + 10)
    staging = tmp_path / "staging"

    final_path = CninfoAnnouncementClient().fetch_pdf(
        "https://static.cninfo.com.cn/report.PDF",
        staging,
        expected_filename="report.pdf",
        budget=budget,
    )

    assert final_path.read_bytes() == body
    assert budget.response_bytes_used == len(body)
    assert not (staging / "report.pdf.part").exists()
    assert all(0 < size <= len(body) + 10 for size in response.read_sizes)


def test_expired_budget_fails_before_opening_request(monkeypatch):
    from src.acquisition_budget import AcquisitionBudgetExceeded
    from src.cninfo_api import CninfoAnnouncementClient

    opener = MagicMock()
    monkeypatch.setattr("urllib.request.urlopen", opener)
    budget = _budget(byte_limit=100, seconds=0.001)
    import time

    time.sleep(0.01)

    with pytest.raises(AcquisitionBudgetExceeded):
        CninfoAnnouncementClient()._post_json(b"page=1", budget=budget)
    opener.assert_not_called()
