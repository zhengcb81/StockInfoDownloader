# -*- coding: utf-8 -*-
"""Unit tests for src.progress.ProgressTracker."""
import json
from pathlib import Path

import pytest

from src.progress import ProgressTracker


class TestProgressTrackerLoadSave:
    """Test loading, saving, and re-loading the progress file."""

    def test_fresh_tracker_creates_default_structure(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        assert tracker.data["completed"] == []
        assert tracker.data["failed"] == []
        assert tracker.data["total"] == 0

    def test_save_creates_file(self, tmp_path):
        f = tmp_path / "progress.json"
        tracker = ProgressTracker(log_file=str(f))
        tracker.init_run("companies.txt", 10)
        assert f.exists()
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["total"] == 10
        assert data["companies_file"] == "companies.txt"

    def test_reload_preserves_state(self, tmp_path):
        f = tmp_path / "progress.json"
        t1 = ProgressTracker(log_file=str(f))
        t1.init_run("companies.txt", 20)
        t1.mark_completed("000001")
        t1.mark_completed("000002")
        t1.mark_failed("000003")

        t2 = ProgressTracker(log_file=str(f))
        assert t2.is_completed("000001")
        assert t2.is_completed("000002")
        assert not t2.is_completed("000003")
        assert "000003" in t2.data["failed"]

    def test_empty_file_treated_as_fresh(self, tmp_path):
        f = tmp_path / "progress.json"
        f.write_text("", encoding="utf-8")
        tracker = ProgressTracker(log_file=str(f))
        assert tracker.data["completed"] == []

    def test_corrupt_json_treated_as_fresh(self, tmp_path):
        f = tmp_path / "progress.json"
        f.write_text("{bad json", encoding="utf-8")
        tracker = ProgressTracker(log_file=str(f))
        assert tracker.data["completed"] == []

    def test_missing_keys_treated_as_fresh(self, tmp_path):
        f = tmp_path / "progress.json"
        f.write_text('{"foo": "bar"}', encoding="utf-8")
        tracker = ProgressTracker(log_file=str(f))
        assert tracker.data["completed"] == []


class TestIsCompleted:
    def test_not_completed_initially(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        assert not tracker.is_completed("000001")

    def test_completed_after_mark(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_completed("000001")
        assert tracker.is_completed("000001")

    def test_different_code_not_completed(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_completed("000001")
        assert not tracker.is_completed("000002")


class TestMarkCompleted:
    def test_marks_and_persists(self, tmp_path):
        f = tmp_path / "progress.json"
        tracker = ProgressTracker(log_file=str(f))
        tracker.mark_completed("000001")
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "000001" in data["completed"]

    def test_no_duplicates(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_completed("000001")
        tracker.mark_completed("000001")
        assert tracker.data["completed"].count("000001") == 1

    def test_removes_from_failed(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_failed("000001")
        assert "000001" in tracker.data["failed"]
        tracker.mark_completed("000001")
        assert "000001" not in tracker.data["failed"]
        assert "000001" in tracker.data["completed"]


class TestMarkFailed:
    def test_marks_and_persists(self, tmp_path):
        f = tmp_path / "progress.json"
        tracker = ProgressTracker(log_file=str(f))
        tracker.mark_failed("000001")
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "000001" in data["failed"]

    def test_no_duplicates(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_failed("000001")
        tracker.mark_failed("000001")
        assert tracker.data["failed"].count("000001") == 1


class TestGetPending:
    def test_all_pending_initially(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        pending = tracker.get_pending(["000001", "000002", "000003"])
        assert pending == ["000001", "000002", "000003"]

    def test_skips_completed(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_completed("000001")
        pending = tracker.get_pending(["000001", "000002", "000003"])
        assert pending == ["000002", "000003"]

    def test_failed_codes_are_pending(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_failed("000002")
        pending = tracker.get_pending(["000001", "000002", "000003"])
        assert "000002" in pending

    def test_preserves_order(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.mark_completed("000002")
        pending = tracker.get_pending(["000001", "000002", "000003", "000004"])
        assert pending == ["000001", "000003", "000004"]


class TestSummary:
    def test_summary_fresh(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.init_run("companies.txt", 10)
        s = tracker.summary()
        assert "0/10 completed" in s
        assert "10 pending" in s

    def test_summary_with_completed_and_failed(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.init_run("companies.txt", 10)
        tracker.mark_completed("000001")
        tracker.mark_completed("000002")
        tracker.mark_failed("000003")
        s = tracker.summary()
        assert "2/10 completed" in s
        assert "1 failed" in s
        assert "8 pending" in s

    def test_summary_no_failed(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.init_run("companies.txt", 5)
        tracker.mark_completed("000001")
        s = tracker.summary()
        assert "failed" not in s


class TestClean:
    def test_clean_removes_file(self, tmp_path):
        f = tmp_path / "progress.json"
        tracker = ProgressTracker(log_file=str(f))
        tracker.init_run("companies.txt", 5)
        assert f.exists()
        ProgressTracker.clean(log_file=str(f))
        assert not f.exists()

    def test_clean_nonexistent_is_noop(self, tmp_path):
        f = tmp_path / "nonexistent.json"
        ProgressTracker.clean(log_file=str(f))  # should not raise


class TestInitRun:
    def test_sets_metadata_on_fresh(self, tmp_path):
        tracker = ProgressTracker(log_file=str(tmp_path / "progress.json"))
        tracker.init_run("my_companies.txt", 42)
        assert tracker.data["companies_file"] == "my_companies.txt"
        assert tracker.data["total"] == 42

    def test_does_not_overwrite_companies_file_on_resume(self, tmp_path):
        f = tmp_path / "progress.json"
        t1 = ProgressTracker(log_file=str(f))
        t1.init_run("original.txt", 10)
        t1.mark_completed("000001")

        t2 = ProgressTracker(log_file=str(f))
        t2.init_run("different.txt", 20)
        assert t2.data["companies_file"] == "original.txt"
        assert t2.data["total"] == 20
