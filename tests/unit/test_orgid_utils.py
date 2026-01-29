#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
orgid_utils 模块单元测试 (Refactored to Pytest)
"""

import json
import os
from unittest.mock import patch

import pytest

from src.tools.legacy.orgid_utils import _load_mapping, get_org_id_by_code

# 从标准测试数据加载
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "test_data", "standard_test_cases.json"
)
with open(DATA_PATH, "r", encoding="utf-8") as f:
    STANDARD_DATA = json.load(f)


@pytest.fixture
def temp_mapping_file(tmp_path):
    """创建临时映射文件 fixture"""
    mapping_dir = tmp_path / "data"
    mapping_dir.mkdir()
    mapping_file = mapping_dir / "stock_orgid_mapping.json"

    initial_data = {
        code: {"orgId": info["org_id"], "name": info["name"]}
        for code, info in STANDARD_DATA["stocks"].items()
    }

    mapping_file.write_text(
        json.dumps(initial_data, ensure_ascii=False), encoding="utf-8"
    )
    return str(mapping_file)


def is_valid_stock_code(code):
    """验证股票代码是否有效 (保持逻辑一致)"""
    if not code or not isinstance(code, str):
        return False
    return len(code) == 6 and code.isdigit()


@pytest.mark.unit
@pytest.mark.parametrize(
    "code, expected",
    [
        ("000001", True),
        ("600000", True),
        ("300470", True),
        ("", False),
        ("123", False),
        ("ABCDEF", False),
        (None, False),
        ("1234567", False),
    ],
)
def test_stock_code_validation(code, expected):
    """测试股票代码验证"""
    assert is_valid_stock_code(code) == expected


@pytest.mark.unit
def test_load_mapping_success(temp_mapping_file):
    """测试成功加载映射文件"""
    mapping = _load_mapping(temp_mapping_file)
    assert isinstance(mapping, dict)
    assert len(mapping) >= len(STANDARD_DATA["stocks"])
    for code in STANDARD_DATA["stocks"]:
        assert code in mapping
        assert "orgId" in mapping[code]


@pytest.mark.unit
def test_load_mapping_not_found():
    """测试加载不存在的文件"""
    mapping = _load_mapping("non_existent_file.json")
    assert mapping == {}


@pytest.mark.unit
def test_get_org_id_by_code_existing(temp_mapping_file):
    """测试从映射获取已有的组织ID"""
    for code, info in STANDARD_DATA["stocks"].items():
        org_id = get_org_id_by_code(code, mapping_file=temp_mapping_file)
        assert org_id == info["org_id"]


@pytest.mark.unit
@patch("src.tools.legacy.orgid_utils._crawl_org_id")
def test_get_org_id_force_refresh(mock_crawl, temp_mapping_file):
    """测试强制刷新映射"""
    mock_crawl.return_value = "newly_crawled_id"
    code = "000001"

    org_id = get_org_id_by_code(code, force_run=True, mapping_file=temp_mapping_file)

    assert org_id == "newly_crawled_id"
    mock_crawl.assert_called_once()


@pytest.mark.integration
def test_mapping_file_lifecycle(tmp_path):
    """集成测试：映射文件生命周期"""
    test_file = tmp_path / "lifecycle.json"

    # 1. 初始空加载
    assert _load_mapping(str(test_file)) == {}

    # 2. 模拟保存 (通过 get_org_id 间接测试保存逻辑或直接调用)
    # 此处假设 get_org_id 会在 force_run 时保存
    with patch("src.tools.legacy.orgid_utils._crawl_org_id") as mock_crawl:
        mock_crawl.return_value = "saved_id"
        get_org_id_by_code("000001", force_run=True, mapping_file=str(test_file))

    # 3. 验证持久化
    new_mapping = _load_mapping(str(test_file))
    assert "000001" in new_mapping
    assert new_mapping["000001"]["orgId"] == "saved_id"
