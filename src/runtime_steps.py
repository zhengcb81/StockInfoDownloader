"""The owner can observe an operation without adding a feedback dependency to it."""

from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping


StepRecorder = Callable[[Mapping[str, Any]], None]
_steps: ContextVar[StepRecorder | None] = ContextVar("sid_runtime_steps", default=None)


@contextmanager
def capture_steps(recorder: StepRecorder | None):
    token = _steps.set(recorder)
    try:
        yield
    finally:
        _steps.reset(token)


def checkpoint(stage: str, state: str, **details: Any) -> None:
    recorder = _steps.get()
    if recorder is not None:
        recorder({"stage": stage, "executed_state": state, **details})


def exception_types(error: BaseException) -> list[str]:
    original = []
    seen = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        original.append(type(current).__name__)
        current = current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    return original


@lru_cache(maxsize=1)
def implementation_version() -> str:
    """Fingerprint the source shipped with this SID runtime."""
    root = Path(__file__).resolve().parent
    digest = sha256()
    for source in sorted(root.glob("*.py")):
        digest.update(source.name.encode("utf-8"))
        digest.update(source.read_bytes())
    # The complete runtime also ships the ordinary batch entry point. The
    # standalone provider artifact ships only the browser-free adapter package.
    batch_entry = root.parent / "main.py"
    try:
        batch_source = batch_entry.read_bytes()
    except FileNotFoundError:
        pass
    else:
        digest.update(batch_source)
    return "src-" + digest.hexdigest()
