"""SID feedback-observation/1 diagnostic sidecar.

This module is the *only* producer of cross-run issue evidence for the
``stockinfo-dl-simple`` owner.  It is deliberately separated from the provider
domain so that observations are diagnostics, never business results:

* one UTF-8 JSON object per line, written to the caller-owned
  ``RESEARCH_FEEDBACK_OUT`` path; no observation ever reaches the JSON CLI's
  stdout/stderr channel;
* references are opaque in-repo identifiers -- no credentials, paths,
  executable commands, raw responses, response bytes, download URL queries or
  physical staging paths are ever serialized;
* a diagnostic write failure is counted here and never changes the provider's
  exit code, return value, already-charged budget, originals or retry policy;
* an action has a ``started`` observation and a terminal observation; a started
  action without a terminal state stays ``unknown``.

The module has no dependency on ``cninfo_api`` / ``company_wiki_adapter``; the
public CLI wires it in at the native discover/fetch entry points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .logger import log

SCHEMA_VERSION = "feedback-observation/1"
OWNER = "stockinfo-dl-simple"

ENV_OUT = "RESEARCH_FEEDBACK_OUT"
ENV_RUN_ID = "RESEARCH_FEEDBACK_RUN_ID"
ENV_ATTEMPT_ID = "RESEARCH_FEEDBACK_ATTEMPT_ID"

DISPOSITIONS = ("expected", "deviation", "unknown")

REQUIRED_FIELDS = (
    "schema_version",
    "owner",
    "run_id",
    "attempt_id",
    "step_id",
    "check_id",
    "expected",
    "actual",
)
OPTIONAL_FIELDS = (
    "issue_key",
    "evidence_ref",
    "version",
    "parent_step_id",
    "details_ref",
    "disposition",
    "origin_owner",
)

# Stable check identifiers.  ``expected``/``actual`` are stable words for the
# corresponding check, not free-form messages.
CHECK_CANDIDATE_IDENTITY = "candidate-listing-identity"
CHECK_RAW_CANDIDATE_FILTER = "raw-candidate-filter"
CHECK_ACQUISITION_BUDGET = "acquisition-budget"
CHECK_STAGED_FETCH = "staged-fetch-receipt"

# Root-cause signatures.  One judged root cause maps to one in-repo issue card.
ISSUE_VERIFIED_ID_MISSING = "verified-candidate-id-missing"
ISSUE_VERIFIED_ID_MISMATCH = "verified-candidate-id-mismatch"
ISSUE_BATCH_MISSED_SUCCESS = "batch-missed-success"

# Details are an explicit whitelist; everything else is dropped before write.
DETAILS_ALLOWED_KEYS = (
    "action",
    # Wall-clock time of the native step (FB-SID 33: "记录公开操作、时间").
    "observed_at",
    "mode",
    "security_id",
    "announcement_ids",
    "provider_document_id",
    "budget_usage",
    "source_result",
    "error_code",
    "retryable",
    # Stable cause chain (FB-SID 33: "错误的稳定类型和原因链"), never raw
    # exception text: an ordered tuple of stable reason tokens.
    "cause_chain",
    "retried",
    "reused",
)


def utc_now() -> str:
    """UTC ISO-8601 timestamp for an observation detail (no secret/path data)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,119}$")
_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9]+")


def is_safe_ref(value: Any) -> bool:
    """True when ``value`` is an opaque, credential/path/command-free token."""
    if not isinstance(value, str) or not _REF_PATTERN.fullmatch(value):
        return False
    if ".." in value or "://" in value:
        return False
    return True


def _require_word(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty trimmed text")
    if not is_safe_ref(value):
        raise ValueError(f"{name} must be an opaque token without paths or credentials")
    return value


def make_observation(
    *,
    run_id: str,
    attempt_id: str,
    step_id: str,
    check_id: str,
    expected: str,
    actual: str,
    version: str | None = None,
    disposition: str | None = None,
    issue_key: str | None = None,
    evidence_ref: str | None = None,
    parent_step_id: str | None = None,
    details_ref: str | None = None,
    origin_owner: str | None = None,
) -> dict[str, str]:
    """Build and validate one ``feedback-observation/1`` wire object."""
    value: dict[str, str] = {
        "schema_version": SCHEMA_VERSION,
        "owner": OWNER,
        "run_id": _require_word("run_id", run_id),
        "attempt_id": _require_word("attempt_id", attempt_id),
        "step_id": _require_word("step_id", step_id),
        "check_id": _require_word("check_id", check_id),
        "expected": _require_word("expected", expected),
        "actual": _require_word("actual", actual),
    }
    if disposition is not None:
        if disposition not in DISPOSITIONS:
            raise ValueError(f"disposition must be one of {DISPOSITIONS}: {disposition!r}")
        value["disposition"] = disposition
    for name, candidate in (
        ("version", version),
        ("issue_key", issue_key),
        ("evidence_ref", evidence_ref),
        ("parent_step_id", parent_step_id),
        ("details_ref", details_ref),
        ("origin_owner", origin_owner),
    ):
        if candidate is not None:
            value[name] = _require_word(name, candidate)
    return value


def classify_candidate_identity(
    candidate: Mapping[str, Any], security_id: str
) -> dict[str, str]:
    """Judge a candidate from its *native* evidence, never from a filename/URL.

    A candidate that claims to be verified without a native ``security_id`` is
    the M3 field-drop signature; a native id for another listing is a distinct
    root cause.  Neither stock codes embedded in ``source_url``/title nor any
    request-side hint may turn a missing id into a verified verdict.
    """
    native = candidate.get("security_id")
    if not isinstance(native, str) or not native.strip():
        return {
            "actual": "missing",
            "disposition": "deviation",
            "issue_key": ISSUE_VERIFIED_ID_MISSING,
        }
    if native != security_id:
        return {
            "actual": "mismatched",
            "disposition": "deviation",
            "issue_key": ISSUE_VERIFIED_ID_MISMATCH,
        }
    if not candidate.get("provider_document_id"):
        return {
            "actual": "missing",
            "disposition": "deviation",
            "issue_key": ISSUE_VERIFIED_ID_MISSING,
        }
    return {"actual": "verified", "disposition": "expected"}


def classify_raw_record(record: Mapping[str, Any], security_id: str) -> dict[str, str]:
    """Judge one CNINFO-shaped row before the adapter filters it.

    An empty secCode and a foreign secCode are legitimate rejects: they are
    recorded with stable words and ``expected`` disposition, never accused of
    being a provider defect.
    """
    sec = record.get("secCode", record.get("sec_code", ""))
    sec = sec.strip() if isinstance(sec, str) else ""
    if not sec:
        actual = "skipped-missing-code"
    elif sec != security_id:
        actual = "skipped-different-stock"
    else:
        actual = "verified"
    return {"actual": actual, "disposition": "expected"}


def observation_identity(observation: Mapping[str, str]) -> str:
    """Canonical key for replay de-duplication (same event => same key)."""
    return json.dumps(observation, ensure_ascii=False, sort_keys=True)


def load_observations(path: Path) -> list[dict[str, str]]:
    """Read a JSONL sidecar; malformed lines are refused, not silently skipped."""
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or any(
            field not in value for field in REQUIRED_FIELDS
        ):
            raise ValueError(f"invalid feedback observation at line {lineno}")
        rows.append(value)
    return rows


@dataclass(frozen=True)
class ImportResult:
    added: int = 0
    duplicates: int = 0


def import_observations(
    dest: Path, observations: Iterable[Mapping[str, str]]
) -> ImportResult:
    """Append observations to ``dest`` once; replays add nothing.

    The caller owns ``dest`` and guarantees a single writer per file.
    """
    existing = {observation_identity(row) for row in load_observations(dest)}
    added = duplicates = 0
    lines: list[str] = []
    for observation in observations:
        key = observation_identity(observation)
        if key in existing:
            duplicates += 1
            continue
        existing.add(key)
        lines.append(json.dumps(observation, ensure_ascii=False, sort_keys=True))
        added += 1
    if lines:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("a", encoding="utf-8") as stream:
            for line in lines:
                stream.write(line + "\n")
    return ImportResult(added=added, duplicates=duplicates)


def needs_refetch(observations: Iterable[Mapping[str, str]], *, step_id: str) -> bool:
    """A terminal report for ``step_id`` forbids a second fetch of the same action."""
    for observation in observations:
        if observation.get("step_id") != step_id:
            continue
        actual = observation.get("actual")
        if actual not in (None, "started", "unknown"):
            return False
    return True


class ActionObservation:
    """One action's ``started``/terminal observation pair.

    ``finish`` is idempotent, so a caller that reports a stable failure followed
    by generic cleanup cannot emit a second terminal event.  When an action
    leaves the scope without a terminal state, ``__exit__`` records ``unknown``
    and never swallows the exception.
    """

    def __init__(
        self,
        sink: "FeedbackSink",
        *,
        step_id: str,
        check_id: str,
        expected: str,
        parent_step_id: str | None = None,
    ) -> None:
        self._sink = sink
        self.step_id = step_id
        self.check_id = check_id
        self.expected = expected
        self.parent_step_id = parent_step_id
        self.finished = False
        self.actual = "started"

    @property
    def _base(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "run_id": self._sink.run_id,
            "attempt_id": self._sink.attempt_id,
            "step_id": self.step_id,
            "check_id": self.check_id,
            "expected": self.expected,
            "version": self._sink.version,
        }
        if self.parent_step_id is not None:
            base["parent_step_id"] = self.parent_step_id
        return base

    def begin(self) -> None:
        self._sink.emit(
            make_observation(**self._base, actual="started", disposition="unknown")
        )

    def __enter__(self) -> "ActionObservation":
        self.begin()
        return self

    def finish(
        self,
        actual: str,
        *,
        disposition: str,
        issue_key: str | None = None,
        evidence_ref: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if self.finished:
            return
        details_ref = self._sink.write_details(self.step_id, details) if details else None
        self._sink.emit(
            make_observation(
                **self._base,
                actual=actual,
                disposition=disposition,
                issue_key=issue_key,
                evidence_ref=evidence_ref,
                details_ref=details_ref,
            )
        )
        self.actual = actual
        self.finished = True

    def __exit__(self, exc_type, exc, tb) -> bool:
        if not self.finished:
            self.finish("unknown", disposition="unknown")
        return False


class FeedbackSink:
    """Single-writer UTF-8 JSONL emitter for one injected sidecar path."""

    def __init__(
        self,
        path: Path | None,
        *,
        run_id: str = "run-local",
        attempt_id: str = "try-1",
        version: str = "unknown",
    ) -> None:
        self.path = path
        self.run_id = run_id
        self.attempt_id = attempt_id
        self.version = version
        self.write_failures = 0
        self.last_write_error: str | None = None

    @classmethod
    def from_env(cls, *, version: str = "unknown") -> "FeedbackSink":
        raw = os.environ.get(ENV_OUT, "").strip()
        return cls(
            Path(raw) if raw else None,
            run_id=os.environ.get(ENV_RUN_ID, "run-local") or "run-local",
            attempt_id=os.environ.get(ENV_ATTEMPT_ID, "try-1") or "try-1",
            version=version,
        )

    @property
    def enabled(self) -> bool:
        return self.path is not None

    def emit(self, observation: Mapping[str, str]) -> bool:
        """Append one line; write errors are counted and never propagated."""
        if self.path is None:
            return False
        line = json.dumps(observation, ensure_ascii=False, sort_keys=True)
        try:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
            return True
        except OSError as exc:  # diagnostics must not change the business result
            self.write_failures += 1
            self.last_write_error = type(exc).__name__
            log.debug("feedback sidecar write failed: %s", type(exc).__name__)
            return False

    def write_details(self, step_id: str, details: Mapping[str, Any]) -> str | None:
        """Write whitelisted diagnostics to ``<sidecar>.details.jsonl``.

        Returns the opaque ``details_ref`` recorded on the observation, or
        ``None`` when no detail survived the whitelist or the write failed.
        """
        if self.path is None:
            return None
        safe = {
            key: details[key]
            for key in DETAILS_ALLOWED_KEYS
            if key in details and details[key] is not None
        }
        # FB-SID 33: every native step records its observation time.  A caller
        # may override with its own UTC timestamp; otherwise stamp it here.
        safe.setdefault("observed_at", utc_now())
        ref = f"details:{step_id}"
        if not is_safe_ref(ref):
            return None
        document = {"details_ref": ref, **safe}
        target = Path(str(self.path) + ".details.jsonl")
        try:
            with target.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")
            return ref
        except OSError as exc:
            self.write_failures += 1
            self.last_write_error = type(exc).__name__
            return None

    def action(
        self,
        *,
        step_id: str,
        check_id: str,
        expected: str,
        parent_step_id: str | None = None,
    ) -> ActionObservation:
        return ActionObservation(
            self,
            step_id=step_id,
            check_id=check_id,
            expected=expected,
            parent_step_id=parent_step_id,
        )


class IssueLedger:
    """One judged root cause = one in-repo issue card, idempotent on replay."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _card_path(self, issue_key: str) -> Path:
        slug = _SLUG_PATTERN.sub("-", issue_key).strip("-") or "unclassified"
        return self.directory / f"{slug}.json"

    def record(
        self,
        observation: Mapping[str, str],
        *,
        recovery_condition: str | None = None,
    ) -> bool:
        """Attach a run to the card for its ``issue_key``; True if anything changed.

        ``recovery_condition`` is for temporary external conditions (FB-SID 37:
        "临时外部条件写恢复条件").  It is a stable, opaque token -- never raw
        exception text, a path or a command -- and is stored once on the card;
        a later run without one never clears it.
        """
        if observation.get("disposition") != "deviation":
            return False
        issue_key = observation.get("issue_key")
        if not issue_key or not is_safe_ref(issue_key):
            return False
        if recovery_condition is not None and not is_safe_ref(recovery_condition):
            raise ValueError("recovery_condition must be a safe opaque token")
        path = self._card_path(issue_key)
        card: dict[str, Any]
        if path.exists():
            card = json.loads(path.read_text(encoding="utf-8"))
        else:
            card = {"issue_key": issue_key, "runs": []}
        if recovery_condition is not None and not card.get("recovery_condition"):
            card["recovery_condition"] = recovery_condition
        entry = {
            "run_id": observation.get("run_id"),
            "attempt_id": observation.get("attempt_id"),
            "step_id": observation.get("step_id"),
            "check_id": observation.get("check_id"),
            "actual": observation.get("actual"),
            "evidence_ref": observation.get("evidence_ref"),
            "version": observation.get("version"),
            "details_ref": observation.get("details_ref"),
        }
        if entry in card["runs"]:
            return False
        card["runs"].append(entry)  # first evidence is never overwritten
        self.directory.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return True

    def cards(self) -> list[dict[str, Any]]:
        if not self.directory.exists():
            return []
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.directory.glob("*.json"))
        ]


__all__ = [
    "SCHEMA_VERSION",
    "OWNER",
    "ENV_OUT",
    "ENV_RUN_ID",
    "ENV_ATTEMPT_ID",
    "DISPOSITIONS",
    "REQUIRED_FIELDS",
    "OPTIONAL_FIELDS",
    "CHECK_CANDIDATE_IDENTITY",
    "CHECK_RAW_CANDIDATE_FILTER",
    "CHECK_ACQUISITION_BUDGET",
    "CHECK_STAGED_FETCH",
    "ISSUE_VERIFIED_ID_MISSING",
    "ISSUE_VERIFIED_ID_MISMATCH",
    "ISSUE_BATCH_MISSED_SUCCESS",
    "ActionObservation",
    "FeedbackSink",
    "ImportResult",
    "IssueLedger",
    "classify_candidate_identity",
    "classify_raw_record",
    "import_observations",
    "is_safe_ref",
    "load_observations",
    "make_observation",
    "needs_refetch",
    "observation_identity",
    "utc_now",
]
