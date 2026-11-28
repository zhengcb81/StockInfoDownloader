"""Collect canonical SID tests and record one actual offline execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
POLICY = Path(__file__).with_name("s6_test_policy.json")
_RUNTIME_ENV = {
    "PATH", "PATHEXT", "COMSPEC", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE",
    "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROGRAMDATA",
    "PROGRAMFILES", "PROGRAMFILES(X86)", "LD_LIBRARY_PATH", "G4_CWP_REPO", "G4_CWP_COMMIT",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args()
    platform = "windows" if os.name == "nt" else sys.platform
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    selection = policy["platforms"][platform]
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    inventory = evidence / f"{platform}-collected.json"
    # Keep the reference's fresh-process import probe isolated from the owner
    # tests, which can already have imported its standard-library sentinel.
    executed = [
        evidence / f"{platform}-executed-{index}.json"
        for index in range(len(selection["roots"]))
    ]
    for report in (inventory, *executed):
        report.unlink(missing_ok=True)
    command = [
        sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
        "-p", "tools.anti_trick_gate_spec.pytest_probe", "--s6-revision", args.revision,
        "-m", selection["markexpr"],
    ]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with TemporaryDirectory(prefix="sid-ci-") as scratch:
        env = {
            **{key: value for key, value in os.environ.items() if key.upper() in _RUNTIME_ENV},
            **dict.fromkeys(("HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "TMPDIR", "TEMP", "TMP"), scratch),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "RESEARCH_FEEDBACK_STATE_ROOT": str(Path(scratch) / "owner-state"),
        }
        runs = [
            (inventory, ["--collect-only", "-q"], selection["roots"]),
            *((report, ["--durations=8"], [root]) for report, root in zip(executed, selection["roots"])),
        ]
        for report, options, roots in runs:
            result = subprocess.run(
                [*command, "--basetemp", str(Path(scratch) / report.stem),
                 "--s6-evidence", str(report), *options, *roots],
                cwd=ROOT, env=env, stdin=subprocess.DEVNULL, creationflags=flags, check=False,
            )
            if result.returncode:
                return result.returncode

        return subprocess.run(
            [sys.executable, "-B", "-m", "tools.anti_trick_gate_spec", "coverage",
             "--revision", args.revision, "--policy", str(POLICY), "--platform", platform,
             str(inventory), *(str(report) for report in executed)],
            cwd=ROOT, env=env, stdin=subprocess.DEVNULL, creationflags=flags, check=False,
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
