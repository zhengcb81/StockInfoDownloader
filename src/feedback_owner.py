"""Public F4 owner commands for SID candidate projection and old job lookup."""

from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Iterable

from .feedback_candidate_capture import (
    CAPTURE,
    CAPTURE_DIR,
    CAPTURE_REF,
    IDENTITY,
    canonical_bytes,
    digest,
    repaired_candidate,
)
from .feedback_observation import (
    CHECK_ACTION_STARTED,
    CHECK_CANDIDATE_IDENTITY,
    CHECK_STAGED_FETCH,
    ISSUE_VERIFIED_ID_MISSING,
    OWNER,
    SCHEMA_VERSION,
)

ACTIONS = ("triage", "repair", "replay", "report")
PUBLICATION = "sid-candidate-publication/1"
KEY = re.compile(r"[0-9a-f]{64}")
TERMINALS = {CHECK_CANDIDATE_IDENTITY, CHECK_STAGED_FETCH}
SUCCEEDED = {"verified", "no_candidates", "staged", "missing", "mismatched"}


def _key(value: object) -> bool:
    return isinstance(value, str) and KEY.fullmatch(value) is not None


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _occurrence(row: object) -> str | None:
    if not isinstance(row, dict) or not all(
        isinstance(row.get(key), str) and row[key] for key in (*IDENTITY, "version")
    ):
        return None
    if (
        row["owner"] != OWNER
        or row["origin_owner"] != OWNER
        or row.get("schema_version") != SCHEMA_VERSION
    ):
        return None
    return digest([row[key] for key in IDENTITY])


def _request(action: str, value: dict) -> tuple[str, dict]:
    key, body = value.get("action_id"), value.get("payload")
    method = "lookup" if action == "reconcile" else "submit"
    if (
        value.get("schema_version") != "feedback-action/1"
        or value.get("owner") != OWNER
        or value.get("kind") != action
        or value.get("method") != method
        or not _key(key)
        or not isinstance(body, dict)
        or value.get("request_digest") != digest([OWNER, action, key, body])
    ):
        raise ValueError("invalid action envelope")
    if action in {"triage", "reconcile"}:
        scope = [body.get("occurrence_id")]
    elif action == "repair":
        scope = [body.get("issue_ref"), body.get("generation")]
    else:
        scope = [
            body.get("occurrence_id"),
            OWNER,
            body.get("issue_ref"),
            body.get("fixed_version"),
        ]
        if action == "report":
            scope.append(body.get("verdict"))
    if digest([action, OWNER, *scope]) != key:
        raise ValueError("invalid action scope")
    return key, body


def _rows(paths: Iterable[Path]) -> Iterable[tuple[Path, dict]]:
    for path in paths:
        try:
            with path.open("rb") as source:
                for line in source:
                    try:
                        row = json.loads(line, object_pairs_hook=_unique)
                    except (ValueError, RecursionError):
                        continue
                    if isinstance(row, dict):
                        yield path, {"origin_owner": row.get("owner"), **row}
        except OSError:
            continue


def _version(publication: dict) -> str:
    return f"{PUBLICATION}/{digest(publication)}"


def _cached(connection: sqlite3.Connection, key: str) -> dict | None:
    saved = connection.execute(
        "SELECT receipt FROM actions WHERE action_id = ?", (key,)
    ).fetchone()
    return json.loads(saved[0], object_pairs_hook=_unique) if saved else None


class OwnerRuntime:
    def __init__(
        self,
        db: Path,
        sidecars: list[Path],
        sidecar_dir: Path | None,
        capture_dir: Path | None,
    ):
        self.db = db
        self.sidecars = sidecars
        self.sidecar_dir = sidecar_dir
        self.capture_dir = capture_dir

    def _scope(self, row: dict) -> tuple[Path | None, list[dict]]:
        paths = set(self.sidecars)
        if self.sidecar_dir is not None:
            paths.update(
                path
                for path in self.sidecar_dir.glob("*.jsonl")
                if not path.name.endswith(".details.jsonl")
            )
        identity = tuple(row[name] for name in (*IDENTITY[:-1], "version"))
        original = None
        siblings = []
        for path, item in _rows(sorted(paths)):
            if (
                tuple(item.get(name) for name in (*IDENTITY[:-1], "version"))
                != identity
            ):
                continue
            if item.get("schema_version") != SCHEMA_VERSION:
                continue
            if item.get("check_id") == row["check_id"]:
                if item != row:
                    return None, []
                original = path
            siblings.append(item)
        return original, siblings

    def _projection(
        self, occurrence: str, row: dict, path: Path
    ) -> tuple[dict | None, str | None]:
        ref = row.get("evidence_ref")
        proof = (
            ref.removeprefix(CAPTURE_REF)
            if isinstance(ref, str) and ref.startswith(CAPTURE_REF)
            else None
        )
        if not _key(proof):
            return None, None
        capture_dir = (
            self.capture_dir
            if self.capture_dir is not None
            else path.parent / CAPTURE_DIR
        )
        try:
            capture = json.loads(
                (capture_dir / f"{proof}.json").read_bytes(), object_pairs_hook=_unique
            )
            if (
                not isinstance(capture, dict)
                or capture.get("schema_version") != CAPTURE
                or capture.get("occurrence_id") != occurrence
                or capture.get("version") != row.get("version")
                or digest(capture) != proof
            ):
                return None, None
            candidate = repaired_candidate(capture)
        except (OSError, ValueError, RecursionError):
            return None, None
        if candidate is None:
            return None, None
        return {
            "schema_version": PUBLICATION,
            "occurrence_id": occurrence,
            "candidate": candidate,
            "original_capture_sha256": proof,
            "original_source_version": row["version"],
        }, proof

    def _triage(self, body: dict) -> dict:
        row = body.get("observation")
        occurrence = _occurrence(row)
        if occurrence is None or occurrence != body.get("occurrence_id"):
            return {"decision": "needs_evidence"}
        original, _ = self._scope(row)
        if original is None:
            return {"decision": "needs_evidence"}
        if row.get("disposition") == "expected":
            return {"decision": "expected"}
        if (
            row.get("check_id") != CHECK_CANDIDATE_IDENTITY
            or row.get("actual") != "missing"
            or row.get("disposition") != "deviation"
            or row.get("issue_key") != ISSUE_VERIFIED_ID_MISSING
        ):
            return {"decision": "needs_evidence"}
        publication, proof = self._projection(occurrence, row, original)
        if publication is None:
            return {"decision": "needs_evidence"}
        return {
            "decision": "repair",
            "issue_ref": f"{PUBLICATION}/{occurrence}",
            "generation": proof,
        }

    def _repair(
        self, connection: sqlite3.Connection, key: str, body: dict
    ) -> tuple[dict | None, dict | None]:
        issue = body.get("issue_ref")
        prefix = PUBLICATION + "/"
        occurrence = (
            issue.removeprefix(prefix)
            if isinstance(issue, str) and issue.startswith(prefix)
            else None
        )
        if not _key(occurrence):
            return None, None
        triage = _cached(connection, digest(["triage", OWNER, occurrence]))
        if (
            not triage
            or triage["result"].get("issue_ref") != issue
            or triage["result"].get("generation") != body.get("generation")
        ):
            return None, None
        original = triage["request"]["payload"]["observation"]
        path, _ = self._scope(original)
        publication, proof = (
            self._projection(occurrence, original, path) if path else (None, None)
        )
        if publication is None or proof != body["generation"]:
            return None, None
        return {
            "fixed_version": _version(publication),
            "evidence_ref": f"{PUBLICATION}/{key}",
        }, publication

    def _replay(self, connection: sqlite3.Connection, body: dict) -> dict | None:
        row = body.get("observation")
        occurrence = _occurrence(row)
        issue, version = body.get("issue_ref"), body.get("fixed_version")
        if (
            occurrence is None
            or occurrence != body.get("occurrence_id")
            or issue != f"{PUBLICATION}/{occurrence}"
            or body.get("issue_owner") != OWNER
            or body.get("acquisition") != "reuse_only"
            or body.get("original_occurrence_id")
            != row.get("original_occurrence_id", occurrence)
        ):
            return None
        triage = _cached(connection, digest(["triage", OWNER, occurrence]))
        if not triage or triage["request"]["payload"].get("observation") != row:
            return None
        repair = _cached(
            connection,
            digest(["repair", OWNER, issue, triage["result"].get("generation")]),
        )
        if not repair or repair["result"].get("fixed_version") != version:
            return None
        path, _ = self._scope(row)
        projection, _ = (
            self._projection(occurrence, row, path) if path else (None, None)
        )
        if projection is None:
            return None
        publication = repair.get("publication")
        verified = publication == projection and version == _version(projection)
        return {
            "verdict": "verified" if verified else "regressed",
            "verified_version": version,
            "evidence_ref": repair["result"]["evidence_ref"],
        }

    def _report(self, connection: sqlite3.Connection, body: dict) -> dict | None:
        prior = _cached(
            connection,
            digest(
                [
                    "replay",
                    OWNER,
                    body.get("occurrence_id"),
                    OWNER,
                    body.get("issue_ref"),
                    body.get("fixed_version"),
                ]
            ),
        )
        verdict = body.get("verdict")
        if (
            not prior
            or body.get("origin_owner") != OWNER
            or verdict not in ("verified", "regressed")
        ):
            return None
        result = prior["result"]
        if (
            result.get("verdict") != verdict
            or result.get("verified_version") != body.get("fixed_version")
            or result.get("evidence_ref") != body.get("evidence_ref")
            or prior["request"]["payload"].get("original_occurrence_id")
            != body.get("original_occurrence_id")
        ):
            return None
        return {"recorded": True}

    def _reconcile(self, body: dict) -> dict:
        row = body.get("observation")
        occurrence = _occurrence(row)
        if occurrence is None or occurrence != body.get("occurrence_id"):
            return {"state": "unknown"}
        original, siblings = self._scope(row)
        if original is None:
            return {"state": "unknown"}
        seen = {
            digest(item): item for item in siblings if item.get("check_id") in TERMINALS
        }
        status = "unconfirmed"
        if len(seen) == 1:
            terminal = next(iter(seen.values()))
            if terminal.get("actual") not in (None, "unknown", "started"):
                status = "succeeded" if terminal["actual"] in SUCCEEDED else "failed"
        return {
            "state": "done",
            "result": {
                "status": "cost_unknown",
                "cost_state": "unknown",
                "job_status": status,
                "evidence_ref": row.get("evidence_ref")
                or f"sid-occurrence:{occurrence}",
            },
        }

    def apply(self, action: str, value: dict) -> dict:
        key, body = _request(action, value)
        if action == "reconcile":
            return self._reconcile(body)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db, timeout=20)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS actions (action_id TEXT PRIMARY KEY, receipt TEXT NOT NULL)"
            )
            connection.execute("BEGIN IMMEDIATE")
            prior = _cached(connection, key)
            if prior is not None:
                if prior["request"] != value:
                    raise ValueError("conflicting action request")
                return {"result": prior["result"]}
            publication = None
            if action == "triage":
                result = self._triage(body)
            elif action == "repair":
                result, publication = self._repair(connection, key, body)
            elif action == "replay":
                result = self._replay(connection, body)
            else:
                result = self._report(connection, body)
            if result is None:
                return {"state": "unknown"}
            receipt = {"request": value, "result": result}
            if publication is not None:
                receipt["publication"] = publication
            connection.execute(
                "INSERT INTO actions VALUES (?, ?)",
                (key, canonical_bytes(receipt).decode("ascii")),
            )
            return {"result": result}

    def read(self, action: str, key: str) -> dict:
        if not _key(key):
            raise ValueError("invalid action id")
        if not self.db.is_file():
            return {}
        with closing(
            sqlite3.connect(self.db.resolve().as_uri() + "?mode=ro", uri=True)
        ) as connection:
            saved = _cached(connection, key)
        if not saved:
            return {}
        if action == "get-action":
            return {"receipt": {part: saved[part] for part in ("request", "result")}}
        publication = saved.get("publication")
        if publication is None:
            return {}
        if _version(publication) != saved["result"].get("fixed_version"):
            raise ValueError("publication checksum mismatch")
        return {"publication": publication}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--sidecar", action="append", type=Path, default=[])
    parser.add_argument("--sidecar-dir", type=Path)
    parser.add_argument("--capture-dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for action in (*ACTIONS, "reconcile"):
        sub.add_parser(action)
    for action in ("get-action", "get-publication"):
        sub.add_parser(action).add_argument("action_id")
    args = parser.parse_args(argv)
    runtime = OwnerRuntime(args.db, args.sidecar, args.sidecar_dir, args.capture_dir)
    try:
        if args.command in ("get-action", "get-publication"):
            result = runtime.read(args.command, args.action_id)
        else:
            value = json.load(sys.stdin, object_pairs_hook=_unique)
            if not isinstance(value, dict):
                raise ValueError("action object required")
            result = runtime.apply(args.command, value)
        print(canonical_bytes(result).decode("ascii"))
    except (OSError, ValueError, TypeError, KeyError, RecursionError, sqlite3.Error):
        print('{"error":"sid_feedback_action_rejected"}', file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
