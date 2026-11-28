"""Materialize the SID provider artifact without importing local cache or browser code."""

from pathlib import Path
import shutil

SRC = Path(__file__).resolve().parents[1] / "src"

# Explicit runtime manifest: the CLI's transitive closure, verified by the
# dependency-direction probe.  browser.py / downloader.py / mapping.py / models.py
# are deliberately absent — the provider runtime must not need them.
RUNTIME_FILES = (
    "__init__.py",
    "acquisition_budget.py",
    "cninfo_api.py",
    "cninfo_identity.py",
    "cninfo_report_metadata.py",
    "company_wiki_adapter.py",
    "company_wiki_adapter_cli.py",
    "config.py",
    "constants.py",
    "disclosure_matching.py",
    "exceptions.py",
    "feedback_candidate_capture.py",
    "feedback_files.py",
    "feedback_observation.py",
    "feedback_publish.py",
    "logger.py",
    "runtime_steps.py",
    "string_utils.py",
    "transport_states.py",
)

def copy_runtime(root: Path) -> None:
    package = root / "src"
    package.mkdir(parents=True)
    for name in RUNTIME_FILES:
        shutil.copy2(SRC / name, package / name)
