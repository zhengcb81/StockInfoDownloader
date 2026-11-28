"""Local file operations shared by SID's download and feedback paths."""

from contextlib import contextmanager, suppress
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep


_REPLACE_DELAYS = (0.02, 0.04, 0.08)
_WINDOWS_RETRYABLE_ERRORS = {5, 32}  # access denied, sharing violation


def native_path(path: Path, *, descendants: bool = False) -> Path:
    """Use the Win32 namespace for long paths or a whole subtree."""
    if os.name != "nt":
        return path
    absolute = os.path.abspath(path)
    extended = chr(92) * 2 + "?" + chr(92)
    if absolute.startswith(extended):
        return Path(absolute)
    if not descendants and len(absolute.encode("utf-16-le")) // 2 < 240:
        return path
    if absolute.startswith(chr(92) * 2):
        absolute = "UNC" + chr(92) + absolute[2:]
    return Path(extended + absolute)


def replace_file(source: Path, destination: Path) -> None:
    """Publish on the same filesystem, retrying brief Windows sharing failures."""
    native_source = native_path(source)
    native_destination = native_path(destination)
    for delay in _REPLACE_DELAYS:
        try:
            os.replace(native_source, native_destination)
        except OSError as exc:
            if getattr(exc, "winerror", None) not in _WINDOWS_RETRYABLE_ERRORS:
                raise
            sleep(delay)
        else:
            return
    os.replace(native_source, native_destination)


@contextmanager
def atomic_text(path: Path):
    """Publish a complete UTF-8 file or preserve the previous bytes."""
    target = native_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=target.parent, prefix=".sid-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        # Read-only consumers can temporarily hold a non-sharing Windows handle.
        # A refused publication leaves all durable preexisting state untouched.
        replace_file(temporary, target)
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


@contextmanager
def exclusive_file(path: Path):
    """Serialize a short owner's read/modify/write; the OS frees the lock on exit."""
    lock = native_path(path.with_name(path.name + ".lock"))
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b") as stream:
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
