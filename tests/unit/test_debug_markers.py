#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试标记系统单元测试

测试DebugStep枚举、DebugMarker类和DebugMarkerManager的功能
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.core.debug_tracker import (
    DebugMarker,
    DebugMarkerManager,
    DebugStep,
    get_debug_marker_manager,
)


class TestDebugStep:
    """测试DebugStep枚举"""

    def test_debug_step_enum_values(self):
        """测试所有调试步骤的值"""
        assert DebugStep.ORG_ID_MAPPING.value == "org_id_mapping"
        assert DebugStep.URL_GENERATION.value == "url_generation"
        assert DebugStep.WEBPAGE_CONNECTION.value == "webpage_connection"
        assert DebugStep.PDF_VISIBILITY.value == "pdf_visibility"
        assert DebugStep.PAGINATION.value == "pagination"
        assert DebugStep.KEYWORD_MATCHING.value == "keyword_matching"
        assert DebugStep.DOWNLOAD_PAGE_OPENING.value == "download_page_opening"
        assert DebugStep.DOWNLOAD_SUCCESS.value == "download_success"

    def test_debug_step_count(self):
        """测试调试步骤数量"""
        assert len(DebugStep) == 8


class TestDebugMarker:
    """测试DebugMarker类"""

    def test_marker_creation_success(self):
        """测试成功标记的创建"""
        marker = DebugMarker(
            step=DebugStep.URL_GENERATION,
            success=True,
            details={"url": "https://example.com", "stock_code": "002415"},
        )

        assert marker.step == DebugStep.URL_GENERATION
        assert marker.success is True
        assert marker.details == {"url": "https://example.com", "stock_code": "002415"}
        assert marker.error is None
        assert marker.marker_id.startswith("url_generation_")
        assert isinstance(marker.timestamp, datetime)

    def test_marker_creation_failure(self):
        """测试失败标记的创建"""
        marker = DebugMarker(
            step=DebugStep.DOWNLOAD_SUCCESS,
            success=False,
            details={"url": "https://example.com"},
            error="下载超时",
        )

        assert marker.step == DebugStep.DOWNLOAD_SUCCESS
        assert marker.success is False
        assert marker.details == {"url": "https://example.com"}
        assert marker.error == "下载超时"

    def test_marker_to_dict(self):
        """测试标记转换为字典"""
        marker = DebugMarker(
            step=DebugStep.ORG_ID_MAPPING,
            success=True,
            details={"stock_code": "002415"},
        )

        marker_dict = marker.to_dict()

        assert marker_dict["step"] == "org_id_mapping"
        assert marker_dict["step_name"] == "ORG_ID_MAPPING"
        assert marker_dict["success"] is True
        assert marker_dict["details"] == {"stock_code": "002415"}
        assert marker_dict["error"] is None
        assert "timestamp" in marker_dict
        assert "timestamp_ms" in marker_dict
        assert "marker_id" in marker_dict

    def test_marker_to_log_string(self):
        """测试标记转换为日志字符串"""
        # 成功标记
        marker_success = DebugMarker(
            step=DebugStep.PDF_VISIBILITY, success=True, details={"count": 5}
        )
        log_str = marker_success.to_log_string()
        assert "SUCCESS" in log_str
        assert "PDF_VISIBILITY" in log_str
        assert '"count":5' in log_str

        # 失败标记
        marker_failure = DebugMarker(
            step=DebugStep.PAGINATION, success=False, error="翻页失败"
        )
        log_str = marker_failure.to_log_string()
        assert "FAILED" in log_str
        assert "PAGINATION" in log_str
        assert "翻页失败" in log_str


class TestDebugMarkerManager:
    """测试DebugMarkerManager类"""

    def setup_method(self):
        """每个测试前重置单例"""
        # 清除单例实例以便测试
        DebugMarkerManager.reset_instance()

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = DebugMarkerManager()
        manager2 = DebugMarkerManager()
        assert manager1 is manager2

    def test_add_marker(self):
        """测试添加标记"""
        manager = DebugMarkerManager()
        marker = manager.add_marker(
            step=DebugStep.ORG_ID_MAPPING,
            success=True,
            details={"stock_code": "002415"},
        )

        assert len(manager.markers) == 1
        assert manager.markers[0] is marker
        assert marker.step == DebugStep.ORG_ID_MAPPING

    def test_get_summary(self):
        """测试获取摘要"""
        manager = DebugMarkerManager()

        # 添加多个标记
        manager.add_marker(DebugStep.ORG_ID_MAPPING, True, {"stock": "002415"})
        manager.add_marker(DebugStep.URL_GENERATION, False, {}, "URL错误")
        manager.add_marker(
            DebugStep.WEBPAGE_CONNECTION, True, {"url": "https://example.com"}
        )

        summary = manager.get_summary()

        assert summary["total_markers"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert abs(summary["success_rate"] - 66.67) < 0.01  # 允许浮点数精度误差
        assert "org_id_mapping" in summary["steps"]
        assert "url_generation" in summary["steps"]

    def test_get_markers_for_e2e_test(self):
        """测试为e2e_test提供标记数据"""
        manager = DebugMarkerManager()
        manager.add_marker(DebugStep.PAGINATION, True, {"page": 2})

        markers = manager.get_markers_for_e2e_test()

        assert len(markers) == 1
        assert isinstance(markers[0], dict)
        assert markers[0]["step"] == "pagination"
        assert markers[0]["success"] is True

    def test_clear(self):
        """测试清空标记"""
        manager = DebugMarkerManager()
        manager.add_marker(DebugStep.PDF_VISIBILITY, True)
        assert len(manager.markers) == 1

        manager.clear()
        assert len(manager.markers) == 0


class TestDebugMarkerIntegration:
    """测试调试标记系统集成"""

    def test_get_debug_marker_manager(self):
        """测试获取标记管理器的便捷函数"""
        manager = get_debug_marker_manager()
        assert isinstance(manager, DebugMarkerManager)

    def test_marker_file_creation(self):
        """测试标记文件的创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            DebugMarkerManager.reset_instance()
            manager = DebugMarkerManager(log_dir=temp_dir)

            # 添加标记
            manager.add_marker(DebugStep.DOWNLOAD_SUCCESS, True, {"file": "test.pdf"})

            # 检查文件是否创建
            marker_files = list(Path(temp_dir).glob("markers_*.jsonl"))
            assert len(marker_files) == 1

            # 检查文件内容
            with open(marker_files[0], "r", encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) == 1

                marker_data = json.loads(lines[0])
                assert marker_data["step"] == "download_success"
                assert marker_data["success"] is True

    def test_multiple_markers_in_file(self):
        """测试多个标记写入文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            DebugMarkerManager.reset_instance()
            manager = DebugMarkerManager(log_dir=temp_dir)

            # 添加多个标记
            for i in range(3):
                manager.add_marker(
                    DebugStep.PAGINATION, success=i % 2 == 0, details={"page": i}
                )

            # 检查文件内容
            marker_files = list(Path(temp_dir).glob("markers_*.jsonl"))
            with open(marker_files[0], "r", encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) == 3

                # 验证每行都是有效的JSON
                for line in lines:
                    data = json.loads(line)
                    assert "marker_id" in data
                    assert "step" in data
                    assert "success" in data


class TestUnifiedDownloaderWithDebugMarkers:
    """测试UnifiedDownloader中的调试标记功能"""

    def setup_method(self):
        """每个测试前重置单例"""
        from src.core.debug_tracker import DebugMarkerManager

        DebugMarkerManager.reset_instance()

    def test_unified_downloader_has_debug_methods(self):
        """测试UnifiedDownloader有调试标记方法"""
        from src.services.unified_downloader import UnifiedDownloader

        # 检查类是否有必要的方法
        assert hasattr(UnifiedDownloader, "_debug_step")
        assert hasattr(UnifiedDownloader, "_log_debug_marker")
        assert hasattr(UnifiedDownloader, "get_debug_markers")
        assert hasattr(UnifiedDownloader, "get_debug_summary")

    def test_debug_step_wrapper(self):
        """测试_debug_step封装器"""
        from src.services.unified_downloader import UnifiedDownloader

        # 创建一个简单的mock函数
        def mock_func(x, y):
            return x + y

        # 创建下载器实例（使用最小配置）
        config = {"save_dir": tempfile.mkdtemp()}
        downloader = UnifiedDownloader(config)

        # 测试成功情况
        result = downloader._debug_step(DebugStep.URL_GENERATION, mock_func, 10, 20)
        assert result == 30

        # 检查标记已记录
        markers = downloader.get_debug_markers()
        assert len(markers) == 1
        assert markers[0]["step"] == "url_generation"
        assert markers[0]["success"] is True

    def test_debug_step_wrapper_failure(self):
        """测试_debug_step封装器处理失败"""
        from src.services.unified_downloader import UnifiedDownloader

        def failing_func():
            raise ValueError("测试错误")

        config = {"save_dir": tempfile.mkdtemp()}
        downloader = UnifiedDownloader(config)

        # 测试失败情况
        with pytest.raises(ValueError, match="测试错误"):
            downloader._debug_step(DebugStep.DOWNLOAD_SUCCESS, failing_func)

        # 检查失败标记已记录
        markers = downloader.get_debug_markers()
        assert len(markers) == 1
        assert markers[0]["step"] == "download_success"
        assert markers[0]["success"] is False
        assert "测试错误" in markers[0]["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
