from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys
import threading
import urllib.request

import pytest

from src.acquisition_budget import ProviderAcquisitionBudget
from src.cninfo_api import CninfoAnnouncementClient, CninfoApiError
from src import feedback_files


_PDF = b"%PDF-" + b"x" * 495


@contextmanager
def _pdf_server(body: bytes, declared: int | None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            if declared is not None:
                self.send_header("Content-Length", str(declared))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_WR)
            self.close_connection = True

        def log_message(self, _format, *_args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/report.pdf"
        finally:
            server.shutdown()
            thread.join()


@pytest.fixture(autouse=True)
def loopback_transport(monkeypatch):
    monkeypatch.setattr("src.cninfo_api.TRANSPORT_HOSTS", {"127.0.0.1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    monkeypatch.setattr(urllib.request, "urlopen", opener.open)


@pytest.mark.parametrize("budgeted", [False, True])
def test_truncated_length_preserves_existing_pdf(tmp_path, budgeted):
    budget = ProviderAcquisitionBudget(10_000, 5, "0") if budgeted else None
    existing = tmp_path / "report.pdf"
    existing.write_bytes(_PDF + b"old")
    with _pdf_server(_PDF, 10_000) as url:
        with pytest.raises(CninfoApiError) as exc_info:
            CninfoAnnouncementClient().fetch_pdf(url, tmp_path, budget=budget)

    assert exc_info.value.error_code == "upstream_unavailable"
    assert exc_info.value.retryable
    assert existing.read_bytes() == _PDF + b"old"
    assert list(tmp_path.iterdir()) == [existing]
    if budget is not None:
        assert budget.response_bytes_used == len(_PDF)


@pytest.mark.parametrize("budgeted", [False, True])
@pytest.mark.parametrize("declared", [None, len(_PDF)])
def test_complete_pdf_replaces_existing_file(tmp_path, budgeted, declared):
    initial = tmp_path / "report.pdf"
    initial.write_bytes(_PDF + b"old")
    budget = ProviderAcquisitionBudget(len(_PDF) + (declared is None), 5, "0") if budgeted else None

    with _pdf_server(_PDF, declared) as url:
        output = CninfoAnnouncementClient().fetch_pdf(url, tmp_path, budget=budget)

    assert output == initial
    assert output.read_bytes() == _PDF
    assert list(tmp_path.iterdir()) == [output]
    if budget is not None:
        assert budget.response_bytes_used == len(_PDF)


def test_replace_failure_preserves_existing_pdf(tmp_path, monkeypatch):
    existing = tmp_path / "report.pdf"
    existing.write_bytes(_PDF + b"old")

    def fail(_source, destination):
        assert Path(destination).read_bytes() == _PDF + b"old"
        raise PermissionError("permanent failure")

    monkeypatch.setattr(feedback_files.os, "replace", fail)
    with _pdf_server(_PDF, len(_PDF)) as url:
        with pytest.raises(PermissionError, match="permanent failure"):
            CninfoAnnouncementClient().fetch_pdf(url, tmp_path)
    assert list(tmp_path.iterdir()) == [existing]
    assert existing.read_bytes() == _PDF + b"old"


@pytest.mark.parametrize("winerror", [5, 32])
@pytest.mark.parametrize("recover", [True, False])
def test_feedback_publish_retries_windows_sharing_errors(tmp_path, monkeypatch, winerror, recover):
    target = tmp_path / "status.json"
    target.write_text("old", encoding="utf-8")
    real_replace = feedback_files.os.replace
    attempts = 0

    def replace(source, destination):
        nonlocal attempts
        attempts += 1
        assert Path(destination).read_text(encoding="utf-8") == "old"
        if attempts == 1 or not recover:
            error = PermissionError("temporary sharing violation")
            error.winerror = winerror
            raise error
        real_replace(source, destination)

    def publish():
        with feedback_files.atomic_text(target) as stream:
            stream.write("new")

    monkeypatch.setattr(feedback_files.os, "replace", replace)
    if recover:
        publish()
        assert attempts == 2
        assert target.read_text(encoding="utf-8") == "new"
    else:
        with pytest.raises(PermissionError, match="temporary sharing violation"):
            publish()
        assert 2 <= attempts <= 5
        assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows share mode")
def test_feedback_publish_retries_a_real_open_windows_file(tmp_path, monkeypatch):
    target = tmp_path / "status.json"
    target.write_text("old", encoding="utf-8")
    retry_delays = []

    with target.open("rb") as reader:
        def release_reader(delay):
            retry_delays.append(delay)
            assert reader.read() == b"old"
            reader.close()

        monkeypatch.setattr(feedback_files, "sleep", release_reader)
        with feedback_files.atomic_text(target) as stream:
            stream.write("new")

    assert len(retry_delays) == 1
    assert target.read_text(encoding="utf-8") == "new"
    assert list(tmp_path.iterdir()) == [target]
