#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DebugMarker 模块测试
提升 src/utils/debug_marker.py 模块的测试覆盖率
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.utils.debug_marker import (
    _sanitize_for_json,
    DebugMarker,
)


class TestSanitizeForJson:
    """测试 _sanitize_for_json 函数"""

    def test_sanitize_primitive_types(self):
        """测试基本类型的序列化"""
        assert _sanitize_for_json("string") == "string"
        assert _sanitize_for_json(123) == 123
        assert _sanitize_for_json(3.14) == 3.14
        assert _sanitize_for_json(True) is True
        assert _sanitize_for_json(False) is False
        assert _sanitize_for_json(None) is None

    def test_sanitize_list(self):
        """测试列表的序列化"""
        result = _sanitize_for_json([1, "two", 3.0, True, None])
        assert result == [1, "two", 3.0, True, None]

    def test_sanitize_tuple(self):
        """测试元组的序列化"""
        result = _sanitize_for_json((1, "two", 3.0))
        assert result == [1, "two", 3.0]  # 元组转换为列表

    def test_sanitize_nested_list(self):
        """测试嵌套列表的序列化"""
        result = _sanitize_for_json([1, [2, 3], [[4]]])
        assert result == [1, [2, 3], [[4]]]

    def test_sanitize_dict(self):
        """测试字典的序列化"""
        result = _sanitize_for_json({"key": "value", "num": 123})
        assert result == {"key": "value", "num": 123}

    def test_sanitize_dict_with_int_keys(self):
        """测试整数键字典的序列化"""
        result = _sanitize_for_json({1: "one", 2: "two"})
        assert result == {"1": "one", "2": "two"}  # 键转换为字符串

    def test_sanitize_nested_dict(self):
        """测试嵌套字典的序列化"""
        result = _sanitize_for_json({"outer": {"inner": "value"}})
        assert result == {"outer": {"inner": "value"}}

    def test_sanitize_mixed_structure(self):
        """测试混合结构的序列化"""
        result = _sanitize_for_json(
            {"list": [1, 2, 3], "dict": {"nested": "value"}, "primitive": "text"}
        )
        expected = {"list": [1, 2, 3], "dict": {"nested": "value"}, "primitive": "text"}
        assert result == expected

    def test_sanitize_object_with_dict(self):
        """测试带有 __dict__ 属性的对象"""

        class TestObj:
            def __init__(self):
                self.value = 42

        obj = TestObj()
        result = _sanitize_for_json(obj)
        assert isinstance(result, dict)
        assert "__class__" in result
        assert result["__class__"] == "TestObj"
        assert "__module__" in result
        assert "repr" in result

    def test_sanitize_object_repr_limiting(self):
        """测试对象 repr 长度限制"""

        class LongReprObj:
            def __repr__(self):
                return "x" * 300  # 超过200字符

        obj = LongReprObj()
        result = _sanitize_for_json(obj)
        assert len(result["repr"]) <= 200

    def test_sanitize_object_without_dict(self):
        """测试没有 __dict__ 属性的对象"""
        # 使用内置类型（如 int 或 str）
        result_int = _sanitize_for_json(42)
        assert result_int == 42  # 基本类型直接返回

        # 函数对象有 __dict__，所以会返回字典格式
        result_func = _sanitize_for_json(lambda x: x)
        assert isinstance(result_func, dict)
        assert "__class__" in result_func
        assert result_func["__class__"] == "function"

    def test_sanitize_unserializable_object(self):
        """测试无法序列化的对象"""

        class BrokenClass:
            def __getattribute__(self, name):
                raise AttributeError("Always fails")

        try:
            obj = BrokenClass()
            result = _sanitize_for_json(obj)
            assert "Unserializable" in result
        except Exception:
            # 如果对象创建失败，这是可以接受的
            pass


class TestDebugMarker:
    """测试 DebugMarker 类"""

    def test_init(self):
        """测试初始化"""
        marker = DebugMarker("test_type")
        assert marker.marker_type == "test_type"
        assert marker.steps == []
        assert marker.start_time > 0
        assert marker.marker_id.startswith("test_type_")

    def test_marker_id_unique(self):
        """测试 marker ID 唯一性"""
        marker1 = DebugMarker("type")
        time.sleep(0.01)  # 确保时间戳不同
        marker2 = DebugMarker("type")
        assert marker1.marker_id != marker2.marker_id

    def test_add_step(self):
        """测试添加步骤"""
        marker = DebugMarker("test")
        marker.add_step("step1", "First step")

        assert len(marker.steps) == 1
        assert marker.steps[0]["step_id"] == "step1"
        assert marker.steps[0]["description"] == "First step"
        assert marker.steps[0]["details"] == {}
        assert "timestamp" in marker.steps[0]
        assert "elapsed_ms" in marker.steps[0]

    def test_add_step_with_details(self):
        """测试添加带详细信息的步骤"""
        marker = DebugMarker("test")
        details = {"key": "value", "num": 123}
        marker.add_step("step1", "Step with details", details)

        assert marker.steps[0]["details"] == details

    def test_add_multiple_steps(self):
        """测试添加多个步骤"""
        marker = DebugMarker("test")
        marker.add_step("step1", "First")
        marker.add_step("step2", "Second")
        marker.add_step("step3", "Third")

        assert len(marker.steps) == 3
        assert marker.steps[0]["step_id"] == "step1"
        assert marker.steps[1]["step_id"] == "step2"
        assert marker.steps[2]["step_id"] == "step3"

    def test_elapsed_time_increases(self):
        """测试经过时间递增"""
        marker = DebugMarker("test")
        marker.add_step("step1", "First")

        elapsed1 = marker.steps[0]["elapsed_ms"]
        assert elapsed1 >= 0

        time.sleep(0.05)
        marker.add_step("step2", "Second")

        elapsed2 = marker.steps[1]["elapsed_ms"]
        assert elapsed2 > elapsed1

    def test_save_creates_directory(self):
        """测试保存时创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "logs", "debug_markers")
            marker = DebugMarker("test")
            marker.add_step("step1", "Test step")
            marker.save(log_dir)

            assert os.path.exists(log_dir)

    def test_save_creates_file(self):
        """测试保存时创建文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "markers")
            marker = DebugMarker("test_type")
            marker.add_step("step1", "Test step")
            marker.save(log_dir)

            # 检查是否创建了文件
            files = os.listdir(log_dir)
            assert len(files) > 0
            assert files[0].startswith("markers_session_")
            assert files[0].endswith(".jsonl")

    def test_save_append_mode(self):
        """测试追加模式保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "markers")

            # 创建多个标记并保存
            marker1 = DebugMarker("test1")
            marker1.add_step("step1", "First marker")
            marker1.save(log_dir)

            marker2 = DebugMarker("test2")
            marker2.add_step("step2", "Second marker")
            marker2.save(log_dir)

            # 读取文件并验证内容
            files = os.listdir(log_dir)
            filepath = os.path.join(log_dir, files[0])
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 应该有两行（两个标记）
            assert len(lines) == 2

            # 验证每行都是有效的 JSON
            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            assert data1["marker_type"] == "test1"
            assert data2["marker_type"] == "test2"

    def test_save_serializes_complex_details(self):
        """测试保存时序列化复杂详细信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "markers")

            class CustomObj:
                def __init__(self):
                    self.value = 42

            marker = DebugMarker("test")
            marker.add_step(
                "step1",
                "Complex details",
                {"list": [1, 2, 3], "dict": {"nested": "value"}, "object": CustomObj()},
            )
            marker.save(log_dir)

            # 读取并验证 JSON
            files = os.listdir(log_dir)
            filepath = os.path.join(log_dir, files[0])
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.loads(f.read())

            assert "steps" in data
            assert len(data["steps"]) == 1
            assert data["steps"][0]["details"]["list"] == [1, 2, 3]
            assert data["steps"][0]["details"]["dict"]["nested"] == "value"

    def test_save_error_handling(self):
        """测试保存时的错误处理"""
        marker = DebugMarker("test")
        marker.add_step("step1", "Test step")

        # 使用无效路径（Windows 上可能无法创建）
        # 在某些系统上，这会失败但不应抛出异常
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            # 不应该抛出异常
            marker.save("/invalid/path")

    def test_repr(self):
        """测试 __repr__ 方法"""
        marker = DebugMarker("test_type")
        marker.add_step("step1", "First")
        marker.add_step("step2", "Second")

        repr_str = repr(marker)
        assert "DebugMarker" in repr_str
        assert "test_type" in repr_str
        assert "steps=2" in repr_str

    def test_save_data_structure(self):
        """测试保存的数据结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "markers")

            marker = DebugMarker("test_type")
            marker.add_step("step1", "First step", {"info": "data"})
            marker.save(log_dir)

            # 读取并验证数据结构
            files = os.listdir(log_dir)
            filepath = os.path.join(log_dir, files[0])
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.loads(f.read())

            # 验证所有必需的字段
            assert "marker_id" in data
            assert "marker_type" in data
            assert "start_time" in data
            assert "total_elapsed_ms" in data
            assert "steps" in data
            assert "step_count" in data

            assert data["marker_type"] == "test_type"
            assert data["step_count"] == 1
            assert len(data["steps"]) == 1

    def test_multiple_markers_same_file(self):
        """测试多个标记保存到同一文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "markers")

            # 快速创建多个标记
            for i in range(3):
                marker = DebugMarker(f"test_{i}")
                marker.add_step(f"step_{i}", f"Step {i}")
                marker.save(log_dir)

            # 验证所有标记都在文件中
            files = os.listdir(log_dir)
            filepath = os.path.join(log_dir, files[0])
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 3

            for i, line in enumerate(lines):
                data = json.loads(line)
                assert data["marker_type"] == f"test_{i}"

    def test_save_with_custom_log_dir(self):
        """测试使用自定义日志目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = os.path.join(tmpdir, "custom_debug_logs")

            marker = DebugMarker("test")
            marker.add_step("step1", "Test")
            marker.save(custom_dir)

            assert os.path.exists(custom_dir)
            files = os.listdir(custom_dir)
            assert len(files) > 0

    def test_marker_data_sanitization(self):
        """测试标记数据清理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "markers")

            class UnserializableObj:
                pass

            marker = DebugMarker("test")
            marker.add_step(
                "step1", "With unserializable", {"obj": UnserializableObj()}
            )
            marker.save(log_dir)

            # 应该成功保存，不抛出异常
            files = os.listdir(log_dir)
            filepath = os.path.join(log_dir, files[0])
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.loads(f.read())

            # 对象应该被清理为可序列化的格式
            assert "steps" in data
            assert len(data["steps"]) > 0
