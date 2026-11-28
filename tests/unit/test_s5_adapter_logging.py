"""Offline probes of config-driven logging at the CWP subprocess port."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys

import pytest

from tests.native_process_fixture import native_run
from src.logger import setup_logger


ROOT = Path(__file__).resolve().parents[2]


def test_reconfiguration_closes_replaced_file_and_disables_its_console(tmp_path, capsys):
    first, second = (tmp_path / name for name in ("first.log", "second.log"))
    logger = setup_logger(name="sid-s5-reconfigure", console=True, log_file=str(first))
    try:
        logger.warning("only first")
        previous, = [handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]
        previous_stream = previous.stream
        assert previous_stream is None  # The rotation sink closes its handle after every record.
        capsys.readouterr()
        assert setup_logger(name=logger.name, console=False, log_file=str(second)) is logger
        logger.warning("only second")
        assert previous not in logger.handlers and previous.stream is None
        assert "only second" not in capsys.readouterr().err
        assert first.read_text(encoding="utf-8").count("only first") == 1
        assert "only second" not in first.read_text(encoding="utf-8")
        assert "only second" in second.read_text(encoding="utf-8")
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()


def test_explicit_quiet_logger_does_not_fall_through_to_root_console(capsys):
    root = logging.getLogger()
    ambient = logging.StreamHandler(sys.stderr)
    root.addHandler(ambient)
    logger = setup_logger(name="sid-s5-explicit-quiet", console=False)
    try:
        logger.warning("unexpected ambient console")
        assert capsys.readouterr().err == ""
    finally:
        root.removeHandler(ambient)
        ambient.close()
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()


def invoke_adapter(tmp_path: Path, *, log_path: Path, block_feedback: bool = False):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"logging": {"log_file": str(log_path)}}), encoding="utf-8")
    guard = tmp_path / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import sys\n"
        "def no_network(event, args):\n"
        "    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):\n"
        "        raise AssertionError('no network in the adapter diagnostics fixture')\n"
        "sys.addaudithook(no_network)\n",
        encoding="utf-8",
    )
    sidecar = tmp_path / "observations.jsonl"
    if block_feedback:
        sidecar.mkdir()
    env = {
        name: os.environ[name]
        for name in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC")
        if name in os.environ
    }
    env.update(
        PYTHONPATH=os.pathsep.join((str(guard), str(ROOT))),
        PYTHONUTF8="1",
        RESEARCH_FEEDBACK_OUT=str(sidecar),
        RESEARCH_FEEDBACK_STATE_ROOT=str(tmp_path / "state"),
        RESEARCH_FEEDBACK_RUN_ID="sid-s5-port",
        RESEARCH_FEEDBACK_ATTEMPT_ID="one",
        HOME=str(tmp_path),
        USERPROFILE=str(tmp_path),
    )
    return native_run(
        [sys.executable, "-B", "-m", "src.company_wiki_adapter_cli", "discover", "--config", str(config)],
        cwd=tmp_path, env=env, input=b'{"entity":"Fake"}', capture_output=True,
        timeout=15, check=False,
    )


@pytest.mark.parametrize("block_feedback", [False, True])
def test_cwp_port_writes_configured_structural_log_with_unchanged_protocol(tmp_path, block_feedback):
    target = tmp_path / "logs" / "adapter.log"
    completed = invoke_adapter(tmp_path, log_path=target, block_feedback=block_feedback)
    assert completed.returncode == 1
    assert completed.stdout == b""
    assert len(completed.stderr.splitlines()) == 1
    payload = json.loads(completed.stderr)
    assert payload["error"]["message"] == "security_id is required for CN discovery"
    content = target.read_text(encoding="utf-8")
    assert "ValueError" in content and "sid-s5-port" in content and "request" in content
    assert str(tmp_path) not in content
    if block_feedback:
        assert "feedback" in content and ("PermissionError" in content or "IsADirectoryError" in content)


def test_unavailable_configured_log_uses_owner_fallback_without_changing_wire(tmp_path):
    target = tmp_path / "not-a-file"
    target.mkdir()
    completed = invoke_adapter(tmp_path, log_path=target)
    assert completed.returncode == 1 and completed.stdout == b""
    assert len(completed.stderr.splitlines()) == 1
    assert json.loads(completed.stderr)["error"]["type"] == "ValueError"
    assert target.is_dir()
    output = (tmp_path / "state" / "logs" / "adapter.log").read_text(encoding="utf-8")
    assert "adapter_log_setup_failed" in output and "adapter_failure" in output
    assert str(tmp_path) not in output


def test_configured_rotating_log_keeps_bounded_backups(tmp_path):
    target = tmp_path / "adapter.log"
    logger = setup_logger(
        name="sid-s5-rotation", console=False, log_file=str(target),
        max_bytes=128, backup_count=2,
    )
    try:
        for index in range(10):
            logger.warning("rotation record %s with enough content to roll", index)
        assert sorted(path.name for path in tmp_path.iterdir()) == [
            "adapter.log", "adapter.log.1", "adapter.log.2", "adapter.log.lock",
        ]
        assert "rotation record 9" in target.read_text(encoding="utf-8")
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()


def test_configured_log_redacts_wire_values_and_never_logs_exception_body(tmp_path):
    target = tmp_path / "s5.log"
    logger = setup_logger(name="sid-s5-redaction", console=False, log_file=str(target))
    try:
        try:
            raise ValueError("SYNTHETIC_UNSTRUCTURED_EXCEPTION_BODY")
        except ValueError:
            logger.exception(
                "adapter probe request?apikey=FAKE_QUERY_758 authorization='Bearer FAKE_HEADER_758'",
            )
        logger.warning("FMP_API_KEY=FAKE_ENV_758 Authorization: Bearer\n'FAKE_WRAP_758'")
        logger.warning("Set-Cookie: session=FAKE_COOKIE_758; refresh=FAKE_REFRESH_758")
        logger.warning("Basic FAKE_STANDALONE_FIRST_758\r\n\tFAKE_STANDALONE_FOLD_758\nnext independent diagnostic")
        content = target.read_text(encoding="utf-8")
        assert "next independent diagnostic" in content
        assert "ValueError" in content and "adapter probe" in content
        assert "FAKE_" not in content
        assert "SYNTHETIC_UNSTRUCTURED_EXCEPTION_BODY" not in content
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
