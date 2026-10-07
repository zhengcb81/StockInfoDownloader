"""G5-SID-RUNTIME offline child bootstrap.

This directory is put first on ``PYTHONPATH`` only for the child processes
started by ``tests/e2e/test_g5_browserless_provider.py``.  CPython's ``site``
module imports ``sitecustomize`` automatically at interpreter start-up, so the
child runs the real command line

    python -m src.company_wiki_adapter_cli discover --config <owned config>

while three seams are replaced *before any provider code loads*:

1. **official-host mapping** — ``urllib.request.urlopen`` rewrites only
   ``www.cninfo.com.cn`` / ``static.cninfo.com.cn`` onto the loopback
   ``ThreadingHTTPServer`` named by ``G5_LOOPBACK``.  Without it a cninfo URL
   fails loudly instead of reaching the public network;
2. **non-loopback refusal** — ``socket.getaddrinfo`` and ``socket.socket.connect``
   refuse every non-loopback destination, so an unexpected outbound call is an
   error rather than silent traffic;
3. **browser runtime refusal** — ``playwright``, ``src.browser``,
   ``src.downloader`` and ``src.orgid`` raise ``ImportError`` the moment
   anything imports them, so a provider that still reached for the legacy
   browser stack could not even start.

Everything above those seams (request validation, ``cninfo_identity``,
``CninfoAnnouncementClient``, ``StockInfoCompanyWikiAdapter``, budget
accounting, JSON serialization) is unmodified production code.
"""

from __future__ import annotations

import os
import socket
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

_G5_OFFLINE = True
_BASE = os.environ.get("G5_LOOPBACK", "")
_ORIGINAL_URLOPEN = urllib.request.urlopen
_ORIGINAL_GETADDRINFO = socket.getaddrinfo
_ORIGINAL_CONNECT = socket.socket.connect
_REDIRECT_HOSTS = frozenset({"www.cninfo.com.cn", "static.cninfo.com.cn"})
_LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1", "0000::1"})
_BLOCKED_MODULES = ("playwright", "src.browser", "src.downloader", "src.orgid")


def _rewrite(url: str) -> str:
    parts = urlsplit(url)
    if parts.hostname not in _REDIRECT_HOSTS:
        return url
    if not _BASE:
        raise urllib.error.URLError(
            "g5 offline bootstrap: G5_LOOPBACK is not set, refusing to reach "
            f"the public network for {url!r}"
        )
    base = urlsplit(_BASE)
    return urlunsplit((base.scheme, base.netloc, parts.path, parts.query, ""))


def _loopback_urlopen(request, *args, **kwargs):
    if isinstance(request, urllib.request.Request):
        request.full_url = _rewrite(request.full_url)
    elif isinstance(request, (str, bytes)):
        text = request if isinstance(request, str) else request.decode("utf-8")
        request = _rewrite(text)
    return _ORIGINAL_URLOPEN(request, *args, **kwargs)


def _is_loopback(host: object) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    if not isinstance(host, str):
        return True
    name = host.strip("[]").lower()
    if name in _LOOPBACK_NAMES:
        return True
    return name.startswith("127.")


def _refuse(host: object) -> None:
    if not _is_loopback(host):
        raise OSError(
            -2, f"g5 offline bootstrap: non-loopback network refused: {host!r}"
        )


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    _refuse(host)
    return _ORIGINAL_GETADDRINFO(host, port, *args, **kwargs)


def _guarded_connect(self, address):
    if isinstance(address, tuple) and address:
        _refuse(address[0])
    return _ORIGINAL_CONNECT(self, address)


class _BlockedImport:
    def find_spec(self, fullname, path=None, target=None):
        for blocked in _BLOCKED_MODULES:
            if fullname == blocked or fullname.startswith(blocked + "."):
                raise ImportError(
                    f"g5 offline bootstrap: browser runtime import refused: {fullname}"
                )
        return None


def _install() -> None:  # pragma: no cover - bootstrap must never break start-up
    urllib.request.urlopen = _loopback_urlopen  # type: ignore[assignment]
    _loopback_urlopen._g5_offline_guard = True  # type: ignore[attr-defined]
    socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
    _guarded_getaddrinfo._g5_offline_guard = True  # type: ignore[attr-defined]
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign,assignment]
    _guarded_connect._g5_offline_guard = True  # type: ignore[attr-defined]
    sys.meta_path.insert(0, _BlockedImport())


_install()
