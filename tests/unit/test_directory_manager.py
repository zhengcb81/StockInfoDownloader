"""
目录管理器单元测试
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.utils.directory_manager import DirectoryManager
from src.data.mapping import MappingManager
from tests.test_config_manager import ConfigManagerTool


@pytest.fixture
def temp_directory():
    """创建临时目录的fixture"""
    temp_dir = tempfile.mkdtemp()
    base_dir = Path(temp_dir)
    yield base_dir

    # 清理
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_mapping_manager():
    """创建模拟映射管理器的fixture"""
    mock_manager = Mock(spec=MappingManager)
    mock_manager.get_stock_name.return_value = "测试公司"
    return mock_manager


@pytest.fixture
def test_config():
    """测试配置的fixture"""
    return ConfigManagerTool()


@pytest.fixture
def directory_manager(mock_mapping_manager):
    """目录管理器的fixture"""
    return DirectoryManager(mock_mapping_manager)


def test_get_company_directory(directory_manager, mock_mapping_manager, test_config, temp_directory):
    """测试获取公司目录"""
    test_stock = test_config.get_test_stock("300470")
    stock_code = test_stock.get('code', '300470')
    company_dir = directory_manager.get_company_directory(stock_code, temp_directory)

    expected_path = temp_directory / "测试公司"
    assert company_dir == expected_path

    # 验证映射管理器被调用
    mock_mapping_manager.get_stock_name.assert_called_with(stock_code)


def test_get_company_directory_fallback(directory_manager, mock_mapping_manager, temp_directory):
    """测试获取公司目录的回退机制"""
    # 模拟映射管理器返回None
    mock_mapping_manager.get_stock_name.return_value = None

    stock_code = "999999"
    company_dir = directory_manager.get_company_directory(stock_code, temp_directory)

    expected_path = temp_directory / "999999"
    assert company_dir == expected_path


def test_create_company_directory(directory_manager, mock_mapping_manager, test_config, temp_directory):
    """测试创建公司目录"""
    test_stock = test_config.get_test_stock("300470")
    stock_code = test_stock.get('code', '300470')
    company_dir = directory_manager.create_company_directory(stock_code, temp_directory)

    # 验证目录存在
    assert company_dir.exists()
    assert company_dir.is_dir()

    expected_path = temp_directory / "测试公司"
    assert company_dir == expected_path


def test_create_company_directory_existing(directory_manager, mock_mapping_manager, test_config, temp_directory):
    """测试创建已存在的公司目录"""
    # 先创建目录
    existing_dir = temp_directory / "测试公司"
    existing_dir.mkdir()

    # 再次创建相同的目录
    test_stock = test_config.get_test_stock("300470")
    stock_code = test_stock.get('code', '300470')
    company_dir = directory_manager.create_company_directory(stock_code, temp_directory)

    # 应该成功且目录仍然存在
    assert company_dir.exists()
    assert company_dir.is_dir()


def test_ensure_save_directory(directory_manager, temp_directory):
    """测试确保保存目录存在"""
    test_file_path = temp_directory / "subdir" / "test.pdf"

    # 确保目录存在
    directory_manager.ensure_save_directory(test_file_path)

    # 验证父目录存在
    assert test_file_path.parent.exists()
    assert test_file_path.parent.is_dir()


def test_organize_downloaded_file(directory_manager, mock_mapping_manager, test_config, temp_directory):
    """测试组织下载的文件"""
    # 创建临时文件
    temp_file = temp_directory / "temp_file.pdf"
    temp_file.write_text("test content")

    test_stock = test_config.get_test_stock("300470")
    stock_code = test_stock.get('code', '300470')
    filename = "测试文件.pdf"

    # 组织文件
    final_path = directory_manager.organize_downloaded_file(
        temp_file, stock_code, filename, temp_directory
    )

    # 验证文件被移动
    assert not temp_file.exists()  # 临时文件应该不存在了
    assert final_path.exists()  # 最终文件应该存在

    # 验证文件内容
    assert final_path.read_text() == "test content"

    # 验证文件路径
    expected_path = temp_directory / "测试公司" / "测试文件.pdf"
    assert final_path == expected_path


def test_organize_downloaded_file_nonexistent(directory_manager, mock_mapping_manager, test_config, temp_directory):
    """测试组织不存在的文件"""
    nonexistent_file = temp_directory / "nonexistent.pdf"

    test_stock = test_config.get_test_stock("300470")
    stock_code = test_stock.get('code', '300470')

    with pytest.raises(FileNotFoundError):
        directory_manager.organize_downloaded_file(
            nonexistent_file, stock_code, "test.pdf", temp_directory
        )


def test_validate_directory_structure_valid(directory_manager, temp_directory):
    """测试验证有效的目录结构"""
    # 创建有效的目录结构
    company_dir = temp_directory / "测试公司"
    company_dir.mkdir()

    # 创建测试文件
    test_file = company_dir / "test.pdf"
    test_file.write_text("test")

    # 验证目录结构
    is_valid, issues = directory_manager.validate_directory_structure(
        temp_directory, ["测试公司"]
    )

    assert is_valid
    assert issues == []


def test_validate_directory_structure_invalid(directory_manager, temp_directory):
    """测试验证无效的目录结构"""
    # 创建根目录文件（无效）
    root_file = temp_directory / "root_file.pdf"
    root_file.write_text("test")

    # 验证目录结构
    is_valid, issues = directory_manager.validate_directory_structure(
        temp_directory, ["测试公司"]
    )

    assert not is_valid
    assert "根目录中存在文件" in issues[0]
    assert "公司目录不存在" in issues[1]


def test_validate_directory_structure_nonexistent_base(directory_manager, temp_directory):
    """测试验证不存在的基目录"""
    nonexistent_dir = temp_directory / "nonexistent"

    is_valid, issues = directory_manager.validate_directory_structure(
        nonexistent_dir, ["测试公司"]
    )

    assert not is_valid
    assert "基础目录不存在" in issues[0]