"""Owner-side durable delivery of feedback observations (F4-SID-FAILURES).

Save-before-ack delivery for the ordinary CLI and any owner command that must
publish ``feedback-observation/1`` diagnostics without an injected sidecar:

* an explicit ``RESEARCH_FEEDBACK_OUT`` keeps the caller-owned single-use
  sidecar with its existing ``FeedbackSink`` semantics (no owner bookkeeping);
* without OUT the owner owns delivery: ``RESEARCH_FEEDBACK_DIR`` selects an
  isolated public inbox directory, otherwise the owner state root's
  ``observations`` directory is the formal public inbox;
* every observation is saved to a per-occurrence pending file *before* it is
  delivered, and the pending record is acknowledged only after the delivery
  triple (data JSONL, sanitized details, ready marker) is durably on disk.

A kill between save and delivery, between the data file and the ready marker,
or between ready and ack leaves the pending record behind.  ``republish``
redelivers with the recorded delivery identity (a delivery ledger per
occurrence), so re-sending the same occurrence from any number of processes
produces exactly one publication.  A run receipt written before the first
side effect marks the run; when no terminal can be written the interval stays
unconfirmed instead of being silently reported as a success.

Nothing here ever raises into the business flow: delivery failures are
counted, never fatal.  The module depends only on the observation module --
no provider, browser or transport code.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Mapping
import uuid

from .feedback_candidate_capture import IDENTITY, digest
from .feedback_files import atomic_text, exclusive_file, native_path
from .feedback_observation import (
    ENV_ATTEMPT_ID,
    ENV_OUT,
    ENV_RUN_ID,
    OWNER,
    FeedbackSink,
    filter_details,
    is_safe_ref,
    make_observation,
)
from .logger import log
from .runtime_steps import implementation_version

ENV_DIR = "RESEARCH_FEEDBACK_DIR"
ENV_STATE_ROOT = "RESEARCH_FEEDBACK_STATE_ROOT"

PENDING_SCHEMA = "sid-pending-delivery/1"
READY_SCHEMA = "sid-ready/1"
RECEIPT_SCHEMA = "sid-run-receipt/1"
LEDGER_SCHEMA = "sid-delivery-ledger/1"

DELIVERED = "delivered"
DEFERRED = "deferred"

ORDINARY_VERSION = "ordinary-cli-1.0"


# ── layout ────────────────────────────────────────────────────────────────


def state_root(root: Path | None = None) -> Path:
    """Owner-owned persistent state root for this machine."""
    if root is not None:
        return root
    raw = os.environ.get(ENV_STATE_ROOT, "").strip()
    if raw:
        return Path(raw)
    try:
        base = Path.home()
    except RuntimeError:
        # A noninteractive host can supply an explicit observation channel
        # without loading a user profile. Keep its owner state beside it.
        output = os.environ.get(ENV_OUT, "").strip()
        inbox = os.environ.get(ENV_DIR, "").strip()
        if output:
            base = Path(output).parent
        elif inbox:
            base = Path(inbox)
        else:
            base = Path(gettempdir())
    return base / ".stockinfo-dl-simple"


def observations_dir(root: Path | None = None) -> Path:
    return state_root(root) / "observations"


def pending_dir(root: Path | None = None) -> Path:
    return state_root(root) / "pending"


def runs_dir(root: Path | None = None) -> Path:
    return state_root(root) / "runs"


def deliveries_dir(root: Path | None = None) -> Path:
    return state_root(root) / "deliveries"


def resolve_target(root: Path | None = None) -> tuple[str, Path]:
    """Publication target in priority order: OUT, then DIR, then state root."""
    raw = os.environ.get(ENV_OUT, "").strip()
    if raw:
        return ("out", Path(raw))
    raw = os.environ.get(ENV_DIR, "").strip()
    if raw:
        return ("dir", Path(raw))
    return ("dir", observations_dir(root))


def occurrence_id(observation: Mapping[str, Any]) -> str:
    """Canonical occurrence key: one original occurrence, one delivery."""
    row = {"owner": OWNER, "origin_owner": OWNER, **observation}
    for key in IDENTITY:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"occurrence identity missing {key}")
    return digest([row[key] for key in IDENTITY])


# ── atomic file primitives ────────────────────────────────────────────────


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    with atomic_text(path) as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def _atomic_lines(path: Path, lines: list[str]) -> None:
    with atomic_text(path) as stream:
        for line in lines:
            stream.write(line.rstrip("\n") + "\n")


# ── pending queue, delivery ledger, run receipts ──────────────────────────


def save_pending(
    root: Path | None,
    observation: Mapping[str, Any],
    delivery: Mapping[str, Any],
    details: Mapping[str, Any] | None,
) -> bool:
    """Persist the pending record for ``observation`` before any delivery."""
    try:
        occ = occurrence_id(observation)
        path = native_path(pending_dir(root) / f"{occ}.json")
        safe_details = filter_details(details or {})
        if safe_details:
            safe_details.setdefault("observed_at", utc_now_pub())
        payload = {
            "schema_version": PENDING_SCHEMA,
            "occurrence_id": occ,
            "observation": dict(observation),
            "delivery": dict(delivery),
            "details": safe_details or None,
        }
        if path.exists():
            # Same occurrence: keep the first pending content; a re-send must
            # never replace the original evidence with a changed payload.
            saved = json.loads(path.read_text(encoding="utf-8"))
            return saved.get("observation") == dict(observation)
        _atomic_json(path, payload)
        return True
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        log.debug("feedback pending save refused: %s", type(exc).__name__)
        return False


def ack_pending(root: Path | None, occurrence: str) -> bool:
    """Acknowledge (drop) the pending record after durable delivery."""
    try:
        native_path(pending_dir(root) / f"{occurrence}.json").unlink(missing_ok=True)
        return True
    except OSError as exc:
        log.debug("feedback pending ack refused: %s", type(exc).__name__)
        return False


def _delivery_record(
    root: Path | None, occurrence: str, observation_digest: str
) -> tuple[Path, dict]:
    """Read or create the original delivery under the owner publication lock."""
    path = native_path(deliveries_dir(root) / f"{occurrence}.json")
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        saved = {
            "schema_version": LEDGER_SCHEMA,
            "occurrence_id": occurrence,
            "delivery": {"kind": "dir", "filename": f"feedback-{occurrence[:32]}"},
            "observation_digest": observation_digest,
        }
        _atomic_json(path, saved)
    if (
        saved.get("observation_digest") not in (None, observation_digest)
        or not is_safe_ref((saved.get("delivery") or {}).get("filename"))
    ):
        raise ValueError("conflicting delivery identity")
    return path, saved


def write_startup_receipt(
    run_id: str, attempt_id: str, *, root: Path | None = None,
    entry: str | None = None, version: str | None = None,
) -> bool:
    """Mark the run as started; called before any side effect."""
    if not (is_safe_ref(run_id) and is_safe_ref(attempt_id)):
        return False
    try:
        path = native_path(runs_dir(root) / f"{run_id}__{attempt_id}.json")
        with exclusive_file(state_root(root) / "run-receipts"):
            if path.exists():
                return True  # a started receipt is never rewritten
            payload = {
                "schema_version": RECEIPT_SCHEMA,
                "owner": OWNER,
                "run_id": run_id,
                "attempt_id": attempt_id,
                "started_at": utc_now_pub(),
                "terminal": None,
            }
            if entry is not None:
                payload["entry"] = entry
            if version is not None:
                payload["version"] = version
                try:
                    payload["implementation"] = implementation_version()
                except OSError:
                    payload["implementation"] = "unknown"
            _atomic_json(path, payload)
            return True
    except OSError as exc:
        log.debug("startup receipt unavailable: %s", type(exc).__name__)
        return False


def finish_receipt(
    run_id: str,
    attempt_id: str,
    terminal: Mapping[str, Any],
    *,
    root: Path | None = None,
) -> bool:
    """Record the terminal state; the first terminal wins, never overwritten."""
    if not (is_safe_ref(run_id) and is_safe_ref(attempt_id)):
        return False
    try:
        path = native_path(runs_dir(root) / f"{run_id}__{attempt_id}.json")
        with exclusive_file(state_root(root) / "run-receipts"):
            if path.exists():
                saved = json.loads(path.read_text(encoding="utf-8"))
                if saved.get("terminal") is not None:
                    return True
                payload = {**saved, "terminal": dict(terminal), "finished_at": utc_now_pub()}
            else:
                payload = {
                    "schema_version": RECEIPT_SCHEMA,
                    "owner": OWNER,
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "started_at": utc_now_pub(),
                    "terminal": dict(terminal),
                }
            _atomic_json(path, payload)
            return True
    except (OSError, ValueError) as exc:
        log.debug("run receipt unavailable: %s", type(exc).__name__)
        return False


def read_receipts(root: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(native_path(runs_dir(root)).glob("*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            events = _read_checkpoints(path.with_suffix(".jsonl"))
            if events:
                receipt["checkpoints"] = events
            rows.append(receipt)
        except (OSError, ValueError):
            continue
    return rows


def write_checkpoint(
    run_id: str, attempt_id: str, step_id: str, details: Mapping[str, Any],
    *, root: Path | None = None,
) -> bool:
    """Record one already-known step before optional observation delivery."""
    if not all(is_safe_ref(item) for item in (run_id, attempt_id, step_id)):
        return False
    path = native_path(runs_dir(root) / f"{run_id}__{attempt_id}.jsonl")
    payload = {**filter_details(details), "step_id": step_id, "observed_at": utc_now_pub()}
    try:
        with exclusive_file(path), path.open("a+b") as stream:
            separator = b""
            if stream.seek(0, os.SEEK_END):
                stream.seek(-1, os.SEEK_END)
                separator = b"" if stream.read(1) == b"\n" else b"\n"
            stream.write(separator + (json.dumps(payload, ensure_ascii=True) + "\n").encode("ascii"))
            stream.flush()
            os.fsync(stream.fileno())
        return True
    except (OSError, ValueError, TypeError):
        return False


def _read_checkpoints(path: Path) -> list[dict[str, Any]]:
    events = []
    try:
        with path.open("rb") as stream:
            for line in stream:
                if not line.endswith(b"\n"):
                    break
                try:
                    record = json.loads(line)
                    if isinstance(record, dict) and is_safe_ref(record.get("step_id")):
                        events.append({**filter_details(record), "step_id": record["step_id"]})
                except (UnicodeError, ValueError, RecursionError):
                    continue
    except OSError:
        pass
    return events


def read_pending(root: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(native_path(pending_dir(root)).glob("*.json")):
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return rows


def utc_now_pub() -> str:
    """UTC timestamp for owner-private state (kept out of public payloads)."""
    from .feedback_observation import utc_now

    return utc_now()


# ── publisher ─────────────────────────────────────────────────────────────


def _ready_payload(observation: Mapping[str, Any], occurrence: str) -> dict[str, str]:
    """The ready marker: binds one publication to its original occurrence."""
    return {
        "schema_version": READY_SCHEMA,
        "owner": str(observation.get("owner") or OWNER),
        "origin_owner": str(observation.get("origin_owner") or OWNER),
        "run_id": str(observation["run_id"]),
        "attempt_id": str(observation["attempt_id"]),
        "step_id": str(observation["step_id"]),
        "check_id": str(observation["check_id"]),
        "occurrence_id": occurrence,
    }


def _publish_to_inbox(
    inbox: Path,
    filename: str,
    observation: Mapping[str, Any],
    details: Mapping[str, Any] | None,
    occurrence: str,
    ready_writer: Any = None,
) -> None:
    """Deliver one observation triple; details and data before the marker."""
    from .feedback_observation import filter_details, utc_now

    write_ready = ready_writer if ready_writer is not None else _atomic_json
    base = inbox / filename
    details_ref = None
    if details:
        safe = filter_details(details)
        if safe:
            # FB-SID 33: every native step records its observation time, on
            # the DIR path exactly as the explicit-OUT path does.
            safe.setdefault("observed_at", utc_now())
            row = {"details_ref": f"details:{observation['step_id']}", **safe}
            _atomic_lines(
                Path(f"{base}.details.jsonl"),
                [json.dumps(row, ensure_ascii=False, sort_keys=True)],
            )
            details_ref = row["details_ref"]
    final = {**observation, **({"details_ref": details_ref} if details_ref else {})}
    _atomic_lines(
        Path(f"{base}.jsonl"),
        [json.dumps(final, ensure_ascii=False, sort_keys=True)],
    )
    write_ready(Path(f"{base}.ready"), _ready_payload(final, occurrence))


class Publisher:
    """Save-before-ack publication of one observation at a time.

    ``publish`` never raises: every failure path returns ``DEFERRED`` and is
    counted, so diagnostics can never change a business result.  ``_write_ready``
    and ``_ack`` are isolated hooks so a harness can interrupt exactly between
    the transactional steps.
    """

    def __init__(
        self,
        *,
        run_id: str,
        attempt_id: str,
        version: str,
        target: tuple[str, Path] | None = None,
        state_root: Path | None = None,
    ) -> None:
        self.run_id = run_id
        self.attempt_id = attempt_id
        self.version = version
        self.root = state_root
        if target is None:
            target = resolve_target(state_root)
        self.target_kind, self.target_path = target
        self.write_failures = 0
        self.last_write_error: str | None = None
        self._sink_instance: Any = None

    def publish(
        self,
        *,
        step_id: str,
        check_id: str,
        expected: str,
        actual: str,
        disposition: str | None = None,
        issue_key: str | None = None,
        evidence_ref: str | None = None,
        parent_step_id: str | None = None,
        terminal_check_id: str | None = None,
        refusal_code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> str:
        try:
            observation = make_observation(
                run_id=self.run_id,
                attempt_id=self.attempt_id,
                step_id=step_id,
                check_id=check_id,
                expected=expected,
                actual=actual,
                version=self.version,
                disposition=disposition,
                issue_key=issue_key,
                evidence_ref=evidence_ref,
                parent_step_id=parent_step_id,
                terminal_check_id=terminal_check_id,
                refusal_code=refusal_code,
            )
        except (ValueError, TypeError) as exc:
            self.write_failures += 1
            self.last_write_error = type(exc).__name__
            log.warning("feedback_observation_refused run_id=%s exception_type=%s",
                        self.run_id, self.last_write_error)
            return DEFERRED
        return self.emit(observation, details)

    def emit(self, observation: dict[str, str], details: Mapping[str, Any] | None = None) -> str:
        try:
            if self.target_kind == "out":
                return self._deliver_out(observation["step_id"], observation, details)
            return self._deliver_dir(observation, details)
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            self.write_failures += 1
            self.last_write_error = type(exc).__name__
            log.warning("feedback_delivery_deferred run_id=%s exception_type=%s",
                        self.run_id, self.last_write_error)
            return DEFERRED

    def _deliver_out(
        self,
        step_id: str,
        observation: dict[str, str],
        details: Mapping[str, Any] | None,
    ) -> str:
        """Explicit OUT: the caller-owned single-use file, existing format."""
        sink = self._out_sink()
        details_ref = sink.write_details(step_id, details) if details else None
        if details_ref:
            observation = {**observation, "details_ref": details_ref}
        return DELIVERED if sink.emit(observation) else DEFERRED

    def _out_sink(self) -> Any:
        if self._sink_instance is None:
            from .feedback_observation import FeedbackSink

            self._sink_instance = FeedbackSink(
                self.target_path,
                run_id=self.run_id,
                attempt_id=self.attempt_id,
                version=self.version,
            )
        return self._sink_instance

    def _deliver_dir(self, observation: dict[str, str], details: Mapping[str, Any] | None) -> str:
        occurrence = occurrence_id(observation)
        with exclusive_file(state_root(self.root) / "delivery"):
            path, recorded = _delivery_record(self.root, occurrence, digest(observation))
            if recorded.get("published"):
                self._ack(occurrence)
                return DELIVERED
            filename = recorded["delivery"]["filename"]
            wanted = {
                "kind": "dir",
                "filename": filename,
                "inbox": str(self.target_path),
            }
            if not save_pending(self.root, observation, wanted, details):
                return DEFERRED
            saved = json.loads(native_path(pending_dir(self.root) / f"{occurrence}.json").read_bytes())
            inbox = Path(saved["delivery"]["inbox"])
            self._deliver_triple(inbox, filename, observation, saved.get("details"), occurrence)
            _atomic_json(path, {**recorded, "published": True})
            self._ack(occurrence)
            return DELIVERED

    def _deliver_triple(
        self,
        inbox: Path,
        filename: str,
        observation: Mapping[str, Any],
        details: Mapping[str, Any] | None,
        occurrence: str,
    ) -> None:
        _publish_to_inbox(
            inbox,
            filename,
            observation,
            details,
            occurrence,
            ready_writer=self._write_ready,
        )

    def _write_ready(self, ready_path: Path, payload: Mapping[str, Any]) -> None:
        _atomic_json(ready_path, payload)

    def _ack(self, occurrence: str) -> bool:
        return ack_pending(self.root, occurrence)


class NativeFeedbackSink(FeedbackSink):
    """Use the same ActionObservation protocol with durable native delivery."""

    def __init__(self, publisher: Publisher) -> None:
        # Existing candidate evidence uses the enclosing folder as its anchor.
        super().__init__(
            publisher.target_path / "native-sidecar",
            run_id=publisher.run_id,
            attempt_id=publisher.attempt_id,
            version=publisher.version,
        )
        self._publisher = publisher
        self._details: dict[str, dict[str, Any]] = {}

    def write_details(self, step_id: str, details: Mapping[str, Any]) -> str | None:
        safe = filter_details(details)
        if safe:
            self._details[step_id] = safe
            return f"details:{step_id}"
        return None

    def emit(self, observation: Mapping[str, str]) -> bool:
        details = self._details.pop(observation["step_id"], None)
        delivered = self._publisher.emit(dict(observation), details) == DELIVERED
        if not delivered:
            self.write_failures += 1
            self.last_write_error = self._publisher.last_write_error
        return delivered


def command_sink(version: str, *, identity: tuple[str, str] | None = None) -> FeedbackSink:
    target = resolve_target()
    if target[0] == "out":
        if identity is not None:
            return FeedbackSink(target[1], run_id=identity[0], attempt_id=identity[1], version=version)
        return FeedbackSink.from_env(version=version)
    run_id, attempt_id = identity if identity is not None else establish_identity()
    return NativeFeedbackSink(Publisher(
        run_id=run_id, attempt_id=attempt_id, version=version, target=target,
    ))


# ── recovery ──────────────────────────────────────────────────────────────


def _redeliver(root: Path | None, saved: Mapping[str, Any]) -> bool:
    observation = saved.get("observation")
    delivery = saved.get("delivery")
    occurrence = saved.get("occurrence_id")
    if (
        not isinstance(observation, dict)
        or not isinstance(delivery, dict)
        or not isinstance(occurrence, str)
    ):
        return False
    filename = delivery.get("filename")
    if delivery.get("kind") != "dir" or not (
        isinstance(filename, str) and is_safe_ref(filename)
    ):
        return False
    inbox = Path(delivery.get("inbox") or observations_dir(root))
    try:
        with exclusive_file(state_root(root) / "delivery"):
            if not native_path(pending_dir(root) / f"{occurrence}.json").is_file():
                return False  # another reader already confirmed this record
            path, recorded = _delivery_record(root, occurrence, digest(observation))
            if not recorded.get("published"):
                _publish_to_inbox(inbox, filename, observation, saved.get("details"), occurrence)
                _atomic_json(path, {**recorded, "published": True})
            return ack_pending(root, occurrence)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        log.debug("republish deferred: %s", type(exc).__name__)
        return False


def republish(root: Path | None = None) -> dict[str, int]:
    """Redeliver every pending occurrence with its recorded delivery identity."""
    result = {"delivered": 0, "deferred": 0, "unreadable": 0}
    for saved in read_pending(root):
        if not isinstance(saved, dict):
            result["unreadable"] += 1
            continue
        if _redeliver(root, saved):
            result["delivered"] += 1
        else:
            result["deferred"] += 1
    return result


# ── ordinary CLI run feedback ─────────────────────────────────────────────


def establish_identity() -> tuple[str, str]:
    """Run/attempt identity for one ordinary launch.

    Parent-injected ids are associated as-is; anything missing (or unsafe)
    becomes a generated id that other processes can recover from the run
    receipts and pending records under the state root.
    """
    run_id = os.environ.get(ENV_RUN_ID, "").strip()
    attempt_id = os.environ.get(ENV_ATTEMPT_ID, "").strip()
    if not is_safe_ref(run_id):
        run_id = f"sid-run-{uuid.uuid4().hex}"
    if not is_safe_ref(attempt_id):
        attempt_id = f"try-{uuid.uuid4().hex}"
    return run_id, attempt_id


def task_step_id(task_key: Mapping[str, Any]) -> str:
    """Stable per-task step id derived from the business request intent."""
    from .feedback_observation import request_step_id

    return request_step_id("download", dict(task_key))


class RunReceipt:
    """One owner run ledger, independent of any observation destination."""

    def __init__(self, *, entry: str, version: str):
        self.identity = establish_identity()
        self.root = state_root()
        self.available = write_startup_receipt(*self.identity, root=self.root, entry=entry, version=version)

    def checkpoint(self, step_id: str, details: Mapping[str, Any]) -> bool:
        written = write_checkpoint(*self.identity, step_id, details, root=self.root)
        self.available = self.available and written
        return written

    def finish(self, terminal: Mapping[str, Any]) -> bool:
        written = finish_receipt(*self.identity, terminal, root=self.root)
        self.available = self.available and written
        return written


class OrdinaryRunFeedback:
    """Identity, startup receipt and settlement publication for one run.

    The instance is created *before* argument parsing and any side effect.
    All publication is best-effort and counted on ``write_failures``; the
    business result stays untouched even when every writable medium refuses.
    """

    def __init__(self, *, version: str = ORDINARY_VERSION) -> None:
        self.receipt = RunReceipt(entry="ordinary", version=version)
        self.run_id, self.attempt_id = self.receipt.identity
        self.version = version
        self.root = self.receipt.root
        target = resolve_target(self.root)
        self.target_kind, self.target_path = target
        self.publisher = Publisher(
            run_id=self.run_id,
            attempt_id=self.attempt_id,
            version=version,
            target=target,
            state_root=self.root,
        )
        self.write_failures = 0
        if not self.receipt.available:
            self.write_failures += 1

    def checkpoint(self, step_id: str, details: Mapping[str, Any]) -> None:
        if not self.receipt.checkpoint(step_id, details):
            self.write_failures += 1
            log.warning("ordinary_checkpoint_unavailable run_id=%s attempt_id=%s step_id=%s",
                        self.run_id, self.attempt_id, step_id)

    # ── per-task observations ─────────────────────────────────────────

    def task_started(self, *, stock_code: str, task_key: Mapping[str, Any]) -> str:
        step_id = task_step_id(task_key)
        self._publish(
            step_id=step_id,
            check_id="action-started",
            expected="started",
            actual="started",
            disposition="expected",
            terminal_check_id="ordinary-download-task",
            details={
                "action": "ordinary-download",
                "code_site": "main.py:download",
                "stock_code": stock_code,
            },
        )
        return step_id

    def task_finished(
        self,
        *,
        step_id: str,
        stock_code: str,
        success: bool,
        stage: str,
        error_code: str | None = None,
        cause_chain: list[str] | None = None,
        cause_types: list[str] | None = None,
        executed_state: str = "attempted",
    ) -> None:
        self._publish(
            step_id=step_id,
            check_id="ordinary-download-task",
            expected="completed",
            actual="completed" if success else "failed",
            disposition="expected" if success else "deviation",
            issue_key=None if success else "ordinary-task-failed",
            details={
                "action": "ordinary-download",
                "code_site": "main.py:download",
                "stock_code": stock_code,
                "stage": stage,
                "executed_state": executed_state,
                "error_code": error_code,
                "cause_chain": cause_chain,
                "cause_types": cause_types,
                "retried": False,
                "reused": False,
            },
        )

    def file_log_unavailable(self, *, cause_types: list[str]) -> None:
        """Record a file logging failure alongside the original business result."""
        self._publish(
            step_id="logging-setup",
            check_id="ordinary-file-log",
            expected="configured",
            actual="unavailable",
            disposition="deviation",
            details={
                "action": "ordinary-run",
                "code_site": "main.py:setup_logger",
                "stage": "logging",
                "source_result": "console_logging",
                "cause_types": cause_types,
            },
        )

    # ── run settlement ────────────────────────────────────────────────

    def settlement_step_id(self) -> str:
        return "settlement-" + digest([self.run_id, self.attempt_id])[:24]

    def run_refused(
        self,
        *,
        stage: str,
        exit_code: int,
        error_code: str | None = None,
        cause_chain: list[str] | None = None,
        cause_types: list[str] | None = None,
    ) -> None:
        """The run was refused before any task started (e.g. broken config,
        an unreadable companies list).

        The original run id, the stage and the native exception type chain
        stay on record; ``not_sent`` is a known fact because nothing was
        dispatched.  ``exit_code`` keeps the business status the entry returned.
        """
        self._publish(
            step_id=self.settlement_step_id(),
            check_id="ordinary-run-settlement",
            expected="all_completed",
            actual="not_started",
            disposition="expected",
            refusal_code="invalid_arguments" if stage == "arguments" else None,
            details={
                "action": "ordinary-run",
                "code_site": "main.py:main",
                "stage": stage,
                "executed_state": "not_started",
                "sent": "not_sent",
                "attempted": 0,
                "exit_code": exit_code,
                "error_code": error_code,
                "cause_chain": cause_chain,
                "cause_types": cause_types,
            },
        )
        self._finish_receipt({"result": "not_started", "exit_code": exit_code})

    def run_finished(self, *, exit_code: int, settlement: Mapping[str, int]) -> str:
        """Publish the business settlement of the launch.

        ``settlement`` is the runner's own tally: ``attempted`` counts the
        sub-items that really started.  A launch in which nothing started and
        nothing was skipped is an explicit empty work list (``no_tasks``) --
        legitimate and expected, never "all tasks completed"; a launch whose
        companies were all already completed keeps ``all_completed`` with
        ``attempted: 0`` and the skip count.
        """
        attempted = int(settlement.get("attempted", 0) or 0)
        succeeded = int(settlement.get("succeeded", 0) or 0)
        failed = int(settlement.get("failed", 0) or 0)
        skipped = int(settlement.get("skipped", 0) or 0)
        if attempted == 0 and skipped == 0:
            actual = "no_tasks"
        elif failed == 0:
            actual = "all_completed"
        elif succeeded > 0:
            actual = "partial"
        else:
            actual = "all_failed"
        details: dict[str, Any] = {
            "action": "ordinary-run",
            "code_site": "main.py:main",
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "exit_code": exit_code,
        }
        if attempted == 0:
            # Nothing started, so nothing could have been sent.
            details["executed_state"] = "not_started"
            details["sent"] = "not_sent"
        self._publish(
            step_id=self.settlement_step_id(),
            check_id="ordinary-run-settlement",
            expected="all_completed",
            actual=actual,
            disposition="expected" if failed == 0 else "deviation",
            details=details,
        )
        self._finish_receipt({"result": actual, "exit_code": exit_code})
        return actual

    # ── internals ─────────────────────────────────────────────────────

    def _publish(self, **kwargs: Any) -> str:
        try:
            status = self.publisher.publish(**kwargs)
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            self.write_failures += 1
            log.warning("ordinary_feedback_publish_failed run_id=%s exception_type=%s",
                        self.run_id, type(exc).__name__)
            return DEFERRED
        if status != DELIVERED:
            self.write_failures += 1
        return status

    def _finish_receipt(self, terminal: Mapping[str, Any]) -> None:
        if not self.receipt.finish(terminal):
            self.write_failures += 1


# ── CLI ───────────────────────────────────────────────────────────────────


def _reconcile_report(root: Path | None) -> dict[str, Any]:
    """Cold-read reconcile summary.  Owner-private state, public-safe output:
    delivery inbox paths and raw detail payloads never leave the report."""
    from .feedback_observation import filter_details

    pending = []
    for saved in read_pending(root):
        if not isinstance(saved, dict):
            pending.append({"schema_version": "unreadable"})
            continue
        delivery = saved.get("delivery")
        pending.append({
            "schema_version": saved.get("schema_version"),
            "occurrence_id": saved.get("occurrence_id"),
            "observation": saved.get("observation"),
            "delivery": {
                key: value
                for key, value in (delivery or {}).items()
                if key != "inbox"
            }
            if isinstance(delivery, dict)
            else delivery,
            "details": filter_details(saved.get("details") or {}),
        })
    return {"receipts": read_receipts(root), "pending": pending}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SID owner feedback delivery")
    parser.add_argument("command", choices=("republish", "reconcile"))
    parser.add_argument("--state-root", type=Path, default=None)
    parser.add_argument(
        "--json", action="store_true",
        help="accepted for callers; the summary is always one JSON document",
    )
    args = parser.parse_args(argv)
    if args.command == "republish":
        result: dict[str, Any] = republish(args.state_root)
    else:
        result = _reconcile_report(args.state_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ENV_DIR",
    "ENV_STATE_ROOT",
    "PENDING_SCHEMA",
    "READY_SCHEMA",
    "RECEIPT_SCHEMA",
    "LEDGER_SCHEMA",
    "DELIVERED",
    "DEFERRED",
    "ORDINARY_VERSION",
    "OrdinaryRunFeedback",
    "Publisher",
    "ack_pending",
    "establish_identity",
    "finish_receipt",
    "main",
    "occurrence_id",
    "pending_dir",
    "observations_dir",
    "read_pending",
    "read_receipts",
    "republish",
    "resolve_target",
    "runs_dir",
    "save_pending",
    "state_root",
    "task_step_id",
    "write_startup_receipt",
]
