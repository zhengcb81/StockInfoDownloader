"""Unit tests for models."""
from src.models import DownloadRequest, DownloadResult, OrgIdMapping


class TestDownloadRequest:
    def test_defaults(self):
        req = DownloadRequest(stock_code="000001")
        assert req.stock_code == "000001"
        assert req.max_pages == 5
        assert req.reverse_order is False
        assert req.allowed_keywords is None

    def test_with_all_fields(self):
        req = DownloadRequest(
            stock_code="300470",
            stock_name="中密控股",
            org_id="9900023856",
            suffix="research",
            allowed_keywords=["测试"],
            max_pages=3,
            reverse_order=True,
            save_dir="/tmp/downloads",
        )
        assert req.reverse_order is True
        assert req.allowed_keywords == ["测试"]


class TestDownloadResult:
    def test_defaults(self):
        res = DownloadResult(success=True)
        assert res.success is True
        assert res.downloaded_files == []
        assert res.skipped_files == []
        assert res.pages_traversed == 0

    def test_with_data(self):
        res = DownloadResult(
            success=True,
            downloaded_files=["/tmp/a.pdf"],
            skipped_files=["/tmp/b.pdf"],
            pages_traversed=3,
        )
        assert len(res.downloaded_files) == 1
        assert len(res.skipped_files) == 1
        assert res.pages_traversed == 3


class TestOrgIdMapping:
    def test_creation(self):
        m = OrgIdMapping(stock_code="300470", org_id="9900023856", stock_name="中密控股")
        assert m.stock_code == "300470"
        assert m.org_id == "9900023856"
