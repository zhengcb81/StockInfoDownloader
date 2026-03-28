#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试跟踪模块 (debug_tracker.py) 单元测试
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.debug_tracker import (
    DebugMarker,
    DebugMarkerManager,
    DebugStep,
    get_debug_marker_manager,
)


class TestDebugStep:
    """测试 DebugStep 枚举"""

    def test_debug_step_values(self):
        """测试枚举值"""
        assert DebugStep.ORG_ID_MAPPING.value == "org_id_mapping"
        assert DebugStep.URL_GENERATION.value == "url_generation"
        assert DebugStep.WEBPAGE_CONNECTION.value == "webpage_connection"
        assert DebugStep.PDF_VISIBILITY.value == "pdf_visibility"
        assert DebugStep.PAGINATION.value == "pagination"
        assert DebugStep.KEYWORD_MATCHING.value == "keyword_matching"
        assert DebugStep.DOWNLOAD_PAGE_OPENING.value == "download_page_opening"
        assert DebugStep.DOWNLOAD_SUCCESS.value == "download_success"


class TestDebugMarker:
    """测试 DebugMarker 类"""

    def test_init_success(self):
        """测试成功标记初始化"""
        marker = DebugMarker(
            step=DebugStep.ORG_ID_MAPPING,
            success=True,
            details={"org_id": "12345"},
        )
        assert marker.step == DebugStep.ORG_ID_MAPPING
        assert marker.success is True
        assert marker.details == {"org_id": "12345"}
        assert marker.error is None
        assert marker.timestamp is not None
        assert marker.marker_id is not None

    def test_init_failure(self):
        """测试失败标记初始化"""
        marker = DebugMarker(
            step=DebugStep.DOWNLOAD_SUCCESS,
            success=False,
            details={"file": "test.pdf"},
            error="Connection timeout",
        )
        assert marker.step == DebugStep.DOWNLOAD_SUCCESS
        assert marker.success is False
        assert marker.error == "Connection timeout"

    def test_init_default_details(self):
        """测试默认详情"""
        marker = DebugMarker(step=DebugStep.PDF_VISIBILITY, success=True)
        assert marker.details == {}

    def test_to_dict(self):
        """测试转换为字典"""
        marker = DebugMarker(
            step=DebugStep.URL_GENERATION,
            success=True,
            details={"url": "http://example.com"},
        )
        result = marker.to_dict()

        assert result["step"] == "url_generation"
        assert result["step_name"] == "URL_GENERATION"
        assert result["success"] is True
        assert result["details"] == {"url": "http://example.com"}
        assert result["error"] is None
        assert "timestamp" in result
        assert "timestamp_ms" in result
        assert "marker_id" in result

    def test_to_dict_with_error(self):
        """测试带错误的字典转换"""
        marker = DebugMarker(
            step=DebugStep.WEBPAGE_CONNECTION,
            success=False,
            error="Timeout",
        )
        result = marker.to_dict()
        assert result["error"] == "Timeout"

    def test_to_json(self):
        """测试 JSON 序列化"""
        marker = DebugMarker(
            step=DebugStep.PAGINATION,
            success=True,
            details={"page": 1},
        )
        json_str = marker.to_dict()
        # 验证可以序列化为 JSON
        json.dumps(json_str)

    def test_to_log_string_success(self):
        """测试成功日志字符串"""
        marker = DebugMarker(
            step=DebugStep.ORG_ID_MAPPING,
            success=True,
            details={"org_id": "123"},
        )
        log_str = marker.to_log_string()

        assert "SUCCESS" in log_str
        assert "ORG_ID_MAPPING" in log_str
        assert "123" in log_str

    def test_to_log_string_failure(self):
        """测试失败日志字符串"""
        marker = DebugMarker(
            step=DebugStep.DOWNLOAD_SUCCESS,
            success=False,
            details={"file": "test.pdf"},
            error="Connection failed",
        )
        log_str = marker.to_log_string()

        assert "FAILED" in log_str
        assert "DOWNLOAD_SUCCESS" in log_str
        assert "Error: Connection failed" in log_str

    def test_log(self):
        """测试日志输出"""
        marker = DebugMarker(
            step=DebugStep.PDF_VISIBILITY,
            success=True,
            details={"count": 10},
        )
        # 不应该抛出异常
        marker.log()


class TestDebugMarkerManager:
    """测试 DebugMarkerManager 类"""

    def setup_method(self):
        """设置测试环境"""
        # 重置单例实例
        DebugMarkerManager.reset_instance()

    def teardown_method(self):
        """清理测试环境"""
        DebugMarkerManager.reset_instance()

    def test_singleton(self):
        """测试单例模式"""
        manager1 = DebugMarkerManager()
        manager2 = DebugMarkerManager()

        assert manager1 is manager2

    def test_init(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)
            assert manager.markers == []
            assert manager.log_dir == Path(tmpdir)
            assert manager.session_id is not None
            assert manager.log_file is not None

    def test_init_not_reinitialized(self):
        """测试不会重复初始化"""
        manager1 = DebugMarkerManager()
        session_id1 = manager1.session_id

        manager2 = DebugMarkerManager()
        session_id2 = manager2.session_id

        assert session_id1 == session_id2

    def test_reset_instance(self):
        """测试重置实例"""
        manager1 = DebugMarkerManager()
        DebugMarkerManager.reset_instance()
        manager2 = DebugMarkerManager()

        assert manager1 is not manager2

    def test_add_marker(self):
        """测试添加标记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)
            marker = manager.add_marker(
                step=DebugStep.ORG_ID_MAPPING,
                success=True,
                details={"org_id": "12345"},
            )

            assert len(manager.markers) == 1
            assert marker.step == DebugStep.ORG_ID_MAPPING
            assert marker.success is True

    def test_add_marker_writes_to_file(self):
        """测试标记写入文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)
            manager.add_marker(
                step=DebugStep.URL_GENERATION,
                success=True,
                details={"url": "http://example.com"},
            )

            # 验证文件被创建并包含内容
            assert manager.log_file.exists()
            content = manager.log_file.read_text()
            assert "url_generation" in content

    def test_add_multiple_markers(self):
        """测试添加多个标记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)

            manager.add_marker(DebugStep.ORG_ID_MAPPING, True, {"org_id": "1"})
            manager.add_marker(DebugStep.URL_GENERATION, True, {"url": "url1"})
            manager.add_marker(DebugStep.PDF_VISIBILITY, False, error="Not found")

            assert len(manager.markers) == 3

    def test_get_summary_empty(self):
        """测试空标记摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)
            summary = manager.get_summary()

            assert summary["total_markers"] == 0
            assert summary["successful"] == 0
            assert summary["failed"] == 0
            assert summary["success_rate"] == 0

    def test_get_summary_with_markers(self):
        """测试有标记的摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)

            manager.add_marker(DebugStep.ORG_ID_MAPPING, True)
            manager.add_marker(DebugStep.ORG_ID_MAPPING, True)
            manager.add_marker(DebugStep.ORG_ID_MAPPING, False)

            summary = manager.get_summary()

            assert summary["total_markers"] == 3
            assert summary["successful"] == 2
            assert summary["failed"] == 1
            assert summary["success_rate"] == pytest.approx(66.67, rel=0.1)

    def test_get_summary_steps(self):
        """测试步骤统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)

            manager.add_marker(DebugStep.ORG_ID_MAPPING, True)
            manager.add_marker(DebugStep.ORG_ID_MAPPING, True)
            manager.add_marker(DebugStep.URL_GENERATION, True)
            manager.add_marker(DebugStep.URL_GENERATION, False)

            summary = manager.get_summary()

            assert "org_id_mapping" in summary["steps"]
            assert summary["steps"]["org_id_mapping"]["total"] == 2
            assert summary["steps"]["org_id_mapping"]["success"] == 2
            assert summary["steps"]["url_generation"]["total"] == 2
            assert summary["steps"]["url_generation"]["success"] == 1

    def test_get_markers_for_e2e_test(self):
        """测试获取 E2E 测试标记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)

            manager.add_marker(DebugStep.ORG_ID_MAPPING, True, {"org_id": "1"})
            manager.add_marker(DebugStep.DOWNLOAD_SUCCESS, True, {"file": "test.pdf"})

            markers = manager.get_markers_for_e2e_test()

            assert len(markers) == 2
            assert markers[0]["step"] == "org_id_mapping"
            assert markers[1]["step"] == "download_success"

    def test_clear(self):
        """测试清空标记"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DebugMarkerManager(log_dir=tmpdir)

            manager.add_marker(DebugStep.ORG_ID_MAPPING, True)
            manager.add_marker(DebugStep.URL_GENERATION, True)

            manager.clear()

            assert len(manager.markers) == 0


class TestGetDebugMarkerManager:
    """测试 get_debug_marker_manager 函数"""

    def setup_method(self):
        """设置测试环境"""
        DebugMarkerManager.reset_instance()

    def teardown_method(self):
        """清理测试环境"""
        DebugMarkerManager.reset_instance()

    def test_returns_manager(self):
        """测试返回管理器实例"""
        manager = get_debug_marker_manager()
        assert isinstance(manager, DebugMarkerManager)

    def test_returns_same_instance(self):
        """测试返回相同实例"""
        manager1 = get_debug_marker_manager()
        manager2 = get_debug_marker_manager()
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
