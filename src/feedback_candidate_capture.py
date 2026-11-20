"""Owner evidence for a candidate identity that was lost during serialization."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .feedback_observation import OWNER, cninfo_announcement_ref

CAPTURE = "sid-candidate-capture/1"
CAPTURE_REF = "sid-candidate-capture:"
CAPTURE_ENV = "RESEARCH_FEEDBACK_SID_CAPTURE_DIR"
CAPTURE_DIR = ".sid-candidate-captures"
IDENTITY = ("owner", "origin_owner", "run_id", "attempt_id", "step_id", "check_id")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _public_links(published: dict[str, Any], code: str, document: str) -> bool:
    """Keep public CNINFO identifiers without retaining URL authentication."""
    try:
        source, transport = (
            urlsplit(published[name]) for name in ("source_url", "transport_url")
        )
        if (
            source.scheme != "https"
            or source.netloc != "www.cninfo.com.cn"
            or source.fragment
            or source.path != "/new/disclosure/detail"
            or transport.scheme != "https"
            or transport.netloc != "static.cninfo.com.cn"
            or transport.query
            or transport.fragment
        ):
            return False
        query = parse_qs(source.query, keep_blank_values=True, strict_parsing=True)
        return (
            set(query) <= {"stockCode", "announcementId", "announcementTime"}
            and query.get("stockCode") == [code]
            and query.get("announcementId") == [document]
            and (
                "announcementTime" not in query
                or len(query["announcementTime"]) == 1
                and _publication_time(query["announcementTime"][0])
            )
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _publication_time(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return False
    return True


def repaired_candidate(capture: dict[str, Any]) -> dict[str, Any] | None:
    legacy = capture.get("published")
    if not isinstance(legacy, dict) or legacy.get("security_id") not in (None, ""):
        return None
    native_id = capture.get("native_security_id")
    native_document = capture.get("native_document_id")
    if (
        cninfo_announcement_ref(native_id) is None
        or native_id != capture.get("requested_security_id")
        or cninfo_announcement_ref(native_document) is None
        or legacy.get("provider_document_id") != native_document
        or legacy.get("candidate_id") != f"cninfo:{native_document}"
        or legacy.get("provider") != "cninfo"
        or legacy.get("identity_method") != "announcement_id"
        or legacy.get("market") != "CN"
        or not _public_links(legacy, native_id, native_document)
    ):
        return None
    return {**legacy, "security_id": native_id}


def capture_missing_identity(
    sidecar: Path,
    observation: dict[str, str],
    requested_security_id: str,
    published: dict[str, Any],
    native: dict[str, Any],
) -> str | None:
    """Persist only an affected candidate from the real native projection.

    Eligibility requires the original typed candidate and its public
    serialization to differ in the lost identity field alone.
    """
    capture = {
        "schema_version": CAPTURE,
        "occurrence_id": digest([observation[key] for key in IDENTITY]),
        "version": observation["version"],
        "requested_security_id": requested_security_id,
        "native_security_id": native.get("security_id"),
        "native_document_id": native.get("provider_document_id"),
        "published": published,
    }
    repaired = repaired_candidate(capture)
    if repaired is None or repaired != native:
        return None

    proof = digest(capture)
    configured = os.environ.get(CAPTURE_ENV)
    directory = Path(configured) if configured else sidecar.parent / CAPTURE_DIR
    target = directory / f"{proof}.json"
    temporary = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        raw = canonical_bytes(capture)
        if target.exists():
            if target.read_bytes() != raw:
                return None
        else:
            with NamedTemporaryFile(
                "wb", dir=directory, prefix=".candidate-", delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            temporary = None
    except OSError:
        return None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    return CAPTURE_REF + proof
