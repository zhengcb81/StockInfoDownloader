"""Offline contract tests for the canonical three-case E2E suite.

These tests deliberately do not contact cninfo.  They protect the checked-in
fixtures, cleanup semantics, expected-baseline immutability, and truthful
runner result aggregation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.downloader import StockDownloader
from src.models import DownloadRequest
from tests.e2e import official_e2e_test as runner
from tests.utils.cleaner_tool import CleanerTool


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_CONFIG = PROJECT_ROOT / "config_e2e_official.json"
EXPECTED_ROOT = PROJECT_ROOT / "end2end_test" / "expected_results"
ACTUAL_ROOT = PROJECT_ROOT / "end2end_test" / "test_results"

CANONICAL_CASES = [
    ("301611", "research", False),
    ("300470", "periodicReports", True),
    ("300470", "research", True),
]

CANONICAL_PDFS = {
    Path("珂玛科技") / "珂玛科技：301611珂玛科技投资者关系管理信息20250725.pdf":
        "89f5dd0515c4d3afc1d30201da9ef6d5ccc1930d7e5edbcd6cefd9d69e1ba283",
    Path("中密控股") / "中密控股：2025年一季度报告.pdf":
        "ea1d21ef1077e2defc05cb4f62912c68774561849dfd10d770e6e766f8b843e8",
    Path("中密控股") / "中密控股：2023年1月31日投资者关系活动记录表.pdf":
        "8c986ff644e4b4da51604d87efd59d7283366a965bea72287a0127e6a32ab310",
}

RETAINED_RELATIVE_PATH = next(
    path for path in CANONICAL_PDFS if path.parts[0] == "珂玛科技"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_config() -> dict:
    return json.loads(OFFICIAL_CONFIG.read_text(encoding="utf-8"))


def test_official_config_is_exactly_the_original_three_case_contract():
    config = _load_config()

    assert config["save_dir"] == "end2end_test/test_results"
    assert config["expected_result_dir"] == "end2end_test/expected_results"
    assert [
        (case["stock_code"], case["suffix"], case["delete_later"])
        for case in config["test_cases"]
    ] == CANONICAL_CASES


def test_expected_baseline_contains_exactly_three_hash_locked_pdfs():
    actual = {
        path.relative_to(EXPECTED_ROOT)
        for path in EXPECTED_ROOT.rglob("*.pdf")
    }
    assert actual == set(CANONICAL_PDFS)

    for relative_path, expected_hash in CANONICAL_PDFS.items():
        pdf = EXPECTED_ROOT / relative_path
        assert pdf.stat().st_size > 0
        assert _sha256(pdf) == expected_hash


def test_test_results_retains_only_the_false_case_and_matches_expected():
    actual = {
        path.relative_to(ACTUAL_ROOT)
        for path in ACTUAL_ROOT.rglob("*.pdf")
    }
    assert actual == {RETAINED_RELATIVE_PATH}
    assert _sha256(ACTUAL_ROOT / RETAINED_RELATIVE_PATH) == _sha256(
        EXPECTED_ROOT / RETAINED_RELATIVE_PATH
    )


def test_retained_false_case_exercises_real_downloader_skip_branch():
    retained = ACTUAL_ROOT / RETAINED_RELATIVE_PATH
    before = retained.read_bytes()
    config = {
        "save_dir": str(ACTUAL_ROOT),
        "skip_browser_init": True,
        "max_retries": 1,
        "files": {
            "mapping_file": str(PROJECT_ROOT / "src" / "stock_orgid_mapping.json")
        },
    }
    downloader = StockDownloader(config=config)
    downloader._browser = MagicMock()
    request = DownloadRequest(
        stock_code="301611",
        stock_name="珂玛科技",
        save_dir=str(ACTUAL_ROOT),
    )

    result = downloader._download_single_link(
        request,
        RETAINED_RELATIVE_PATH.name.removesuffix(".pdf"),
        "https://example.invalid/must-not-download.pdf",
    )

    assert result == str(retained)
    assert downloader.skipped_files == [str(retained)]
    downloader._browser.download_file.assert_not_called()
    assert retained.read_bytes() == before


def test_retained_false_case_is_not_ignored_by_git():
    retained = ACTUAL_ROOT / RETAINED_RELATIVE_PATH
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", str(retained)],
        cwd=PROJECT_ROOT,
        check=False,
    )
    assert result.returncode == 1


def test_expected_validation_is_read_only_when_an_extra_file_exists(tmp_path):
    expected = tmp_path / "expected"
    company = expected / "珂玛科技"
    company.mkdir(parents=True)
    canonical = company / RETAINED_RELATIVE_PATH.name
    canonical.write_bytes(b"canonical")
    extra = company / "extra.pdf"
    extra.write_bytes(b"must-not-be-deleted")
    before = {path.relative_to(expected): path.read_bytes() for path in expected.rglob("*") if path.is_file()}

    config = {
        "expected_result_dir": str(expected),
        "test_cases": [
            {
                "stock_code": "301611",
                "allowed_keywords": ["投资者关系管理信息20250725"],
            }
        ],
    }
    valid, _message = runner.validate_expected_results(config)

    after = {path.relative_to(expected): path.read_bytes() for path in expected.rglob("*") if path.is_file()}
    assert valid is False
    assert after == before
    assert extra.exists()


def test_directory_compare_rejects_same_name_same_size_different_content(tmp_path):
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    (actual / "公司").mkdir(parents=True)
    (expected / "公司").mkdir(parents=True)
    (actual / "公司" / "报告.pdf").write_bytes(b"AAAA")
    (expected / "公司" / "报告.pdf").write_bytes(b"BBBB")

    matches, message = runner.compare_directories(actual, expected)

    assert matches is False
    assert "content" in message.lower() or "hash" in message.lower()


def test_directory_compare_ignores_untracked_empty_directories(tmp_path):
    actual = tmp_path / "actual"
    expected = tmp_path / "expected"
    (actual / "公司").mkdir(parents=True)
    (expected / "公司").mkdir(parents=True)
    (expected / "本地空目录").mkdir()
    (actual / "公司" / "报告.pdf").write_bytes(b"same")
    (expected / "公司" / "报告.pdf").write_bytes(b"same")

    matches, _message = runner.compare_directories(actual, expected)

    assert matches is True


@pytest.mark.parametrize(
    ("main_success", "compare_success", "expected"),
    [
        (True, True, True),
        (False, True, False),
        (True, False, False),
        (False, False, False),
    ],
)
def test_overall_success_requires_main_and_compare(
    main_success, compare_success, expected
):
    assert runner.compute_overall_success(main_success, compare_success) is expected


def test_cleaner_preserves_false_case_and_removes_true_cases(tmp_path, monkeypatch):
    config = _load_config()
    actual = tmp_path / "test_results"
    expected_snapshot = {
        relative: _sha256(EXPECTED_ROOT / relative)
        for relative in CANONICAL_PDFS
    }
    for relative in CANONICAL_PDFS:
        target = actual / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((EXPECTED_ROOT / relative).read_bytes())

    monkeypatch.chdir(PROJECT_ROOT)
    summary = CleanerTool(str(actual)).clean_test_directory(config["test_cases"])

    remaining = {
        path.relative_to(actual)
        for path in actual.rglob("*.pdf")
    }
    assert remaining == {RETAINED_RELATIVE_PATH}
    assert summary["preserved_files"] == 1
    assert summary["deleted_dirs"] == 1
    assert {
        relative: _sha256(EXPECTED_ROOT / relative)
        for relative in CANONICAL_PDFS
    } == expected_snapshot


def test_official_and_extended_reports_have_distinct_paths():
    official = runner.report_path_for_config(PROJECT_ROOT / "config_e2e_official.json")
    extended = runner.report_path_for_config(PROJECT_ROOT / "config_e2e_extended.json")

    assert official != extended
    assert official.name == "e2e_official_report.json"
    assert extended.name == "e2e_extended_report.json"


def test_runner_exit_is_nonzero_when_main_fails_but_directories_match(
    tmp_path, monkeypatch
):
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    relative = Path("珂玛科技") / RETAINED_RELATIVE_PATH.name
    for root in (expected, actual):
        target = root / relative
        target.parent.mkdir(parents=True)
        target.write_bytes(b"x" * 1024)

    config_path = tmp_path / "config_e2e_truthful_exit.json"
    config_path.write_text(
        json.dumps(
            {
                "save_dir": str(actual),
                "expected_result_dir": str(expected),
                "test_cases": [
                    {
                        "stock_code": "301611",
                        "suffix": "research",
                        "allowed_keywords": ["投资者关系管理信息20250725"],
                        "delete_later": False,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(runner, "run_main_py", lambda *_args: False)
    monkeypatch.setattr(runner, "report_path_for_config", lambda _path: report_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["official_e2e_test.py", "--config", str(config_path)],
    )

    exit_code = runner.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["main_py_success"] is False
    assert report["directory_compare_success"] is True
    assert report["overall_success"] is False
