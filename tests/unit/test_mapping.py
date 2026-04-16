"""Unit tests for mapping module."""
import json
import tempfile

from src.mapping import MappingManager


class TestMappingManager:
    def _make_manager(self, data=None, auto_fetch=False):
        if data is None:
            data = {
                "000001": {"orgId": "9900000001", "name": "平安银行"},
                "300470": {"orgId": "9900023856", "name": "中密控股"},
            }
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(data, f)
        f.close()
        return MappingManager(mapping_file=f.name, auto_fetch=auto_fetch)

    def test_get_org_id(self):
        mm = self._make_manager()
        assert mm.get_org_id("000001") == "9900000001"
        assert mm.get_org_id("300470") == "9900023856"

    def test_get_stock_name(self):
        mm = self._make_manager()
        assert mm.get_stock_name("000001") == "平安银行"
        assert mm.get_stock_name("300470") == "中密控股"

    def test_missing_code_returns_none(self):
        mm = self._make_manager(auto_fetch=False)
        assert mm.get_org_id("999999") is None
        assert mm.get_stock_name("999999") is None

    def test_statistics(self):
        mm = self._make_manager()
        stats = mm.get_statistics()
        assert stats["total"] == 2

    def test_add_mapping(self):
        mm = self._make_manager()
        assert mm.add_mapping("600519", "9900010519", "贵州茅台") is True
        assert mm.get_org_id("600519") == "9900010519"
        assert mm.get_stock_name("600519") == "贵州茅台"

    def test_remove_mapping(self):
        mm = self._make_manager()
        assert mm.remove_mapping("000001") is True
        assert mm.get_org_id("000001") is None

    def test_get_all_stock_codes(self):
        mm = self._make_manager()
        codes = mm.get_all_stock_codes()
        assert "000001" in codes
        assert "300470" in codes
