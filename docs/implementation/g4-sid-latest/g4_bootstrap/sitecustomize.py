"""G4-SID-LATEST offline E2E transport bootstrap.

This directory is placed first on ``PYTHONPATH`` only for the child processes
started by ``tests/e2e/test_g4_latest_cli_offline.py``.  CPython's ``site``
module imports ``sitecustomize`` automatically at interpreter start-up, which
lets the test replace exactly one seam — ``urllib.request.urlopen`` — while the
command line stays the real

    python -m src.company_wiki_adapter_cli discover --config <tmp config>

Everything above that seam (``CninfoAnnouncementClient``,
``StockInfoCompanyWikiAdapter``, request validation and JSON serialization) is
the production code, unmodified.

``G4_LOOPBACK`` names the loopback base URL of the test server.  cninfo hosts
are rewritten onto it and the request is then issued with the *original*
``urlopen``, so a genuine HTTP request/response happens over 127.0.0.1.  With
no ``G4_LOOPBACK`` configured any cninfo request fails loudly instead of
reaching the public network.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit

_BASE = os.environ.get("G4_LOOPBACK", "")
_ORIGINAL = urllib.request.urlopen
_REDIRECT_HOSTS = frozenset({"www.cninfo.com.cn", "static.cninfo.com.cn"})


def _rewrite(url: str) -> str:
    parts = urlsplit(url)
    if parts.hostname not in _REDIRECT_HOSTS:
        return url
    if not _BASE:
        raise urllib.error.URLError(
            "g4 offline bootstrap: G4_LOOPBACK is not set, refusing to reach "
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
    return _ORIGINAL(request, *args, **kwargs)


try:  # pragma: no cover - bootstrap must never break interpreter start-up
    urllib.request.urlopen = _loopback_urlopen  # type: ignore[assignment]
except Exception:  # pragma: no cover
    pass
