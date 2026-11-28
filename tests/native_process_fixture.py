"""Start real test children with explicit pipes and no new Windows console."""

import os
import subprocess


def _options(kwargs):
    if "stdin" not in kwargs and "input" not in kwargs:
        kwargs["stdin"] = subprocess.DEVNULL
    if os.name == "nt":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
    return kwargs


def native_run(*args, **kwargs):
    return subprocess.run(*args, **_options(kwargs))


def native_check_output(*args, **kwargs):
    return subprocess.check_output(*args, **_options(kwargs))


def native_start(*args, **kwargs):
    return subprocess.Popen(*args, **_options(kwargs))
