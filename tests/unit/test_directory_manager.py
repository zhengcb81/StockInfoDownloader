"""
目录管理器单元测试
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.utils.directory_manager import DirectoryManager
from src.data.mapping import MappingManager


class TestDirectoryManager(unittest.TestCase):
    """目录管理器测试类"""

    def setUp(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.temp_dir)

        # 创建模拟的映射管理器
        self.mock_mapping_manager = Mock(spec=MappingManager)
        self.mock_mapping_manager.get_stock_name.return_value = "测试公司"

        self.directory_manager = DirectoryManager(self.mock_mapping_manager)

    def tearDown(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_get_company_directory(self):
        """测试获取公司目录"""
        stock_code = "300470"
        company_dir = self.directory_manager.get_company_directory(stock_code, self.base_dir)

        expected_path = self.base_dir / "测试公司"
        self.assertEqual(company_dir, expected_path)

        # 验证映射管理器被调用
        self.mock_mapping_manager.get_stock_name.assert_called_with(stock_code)

    def test_get_company_directory_fallback(self):
        """测试获取公司目录的回退机制"""
        # 模拟映射管理器返回None
        self.mock_mapping_manager.get_stock_name.return_value = None

        stock_code = "999999"
        company_dir = self.directory_manager.get_company_directory(stock_code, self.base_dir)

        expected_path = self.base_dir / "股票999999"
        self.assertEqual(company_dir, expected_path)

    def test_create_company_directory(self):
        """测试创建公司目录"""
        stock_code = "300470"
        company_dir = self.directory_manager.create_company_directory(stock_code, self.base_dir)

        # 验证目录存在
        self.assertTrue(company_dir.exists())
        self.assertTrue(company_dir.is_dir())

        expected_path = self.base_dir / "测试公司"
        self.assertEqual(company_dir, expected_path)

    def test_create_company_directory_existing(self):
        """测试创建已存在的公司目录"""
        # 先创建目录
        existing_dir = self.base_dir / "测试公司"
        existing_dir.mkdir()

        # 再次创建相同的目录
        stock_code = "300470"
        company_dir = self.directory_manager.create_company_directory(stock_code, self.base_dir)

        # 应该成功且目录仍然存在
        self.assertTrue(company_dir.exists())
        self.assertTrue(company_dir.is_dir())

    def test_ensure_save_directory(self):
        """测试确保保存目录存在"""
        test_file_path = self.base_dir / "subdir" / "test.pdf"

        # 确保目录存在
        self.directory_manager.ensure_save_directory(test_file_path)

        # 验证父目录存在
        self.assertTrue(test_file_path.parent.exists())
        self.assertTrue(test_file_path.parent.is_dir())

    def test_organize_downloaded_file(self):
        """测试组织下载的文件"""
        # 创建临时文件
        temp_file = self.base_dir / "temp_file.pdf"
        temp_file.write_text("test content")

        stock_code = "300470"
        filename = "测试文件.pdf"

        # 组织文件
        final_path = self.directory_manager.organize_downloaded_file(
            temp_file, stock_code, filename, self.base_dir
        )

        # 验证文件被移动
        self.assertFalse(temp_file.exists())  # 临时文件应该不存在了
        self.assertTrue(final_path.exists())  # 最终文件应该存在

        # 验证文件内容
        self.assertEqual(final_path.read_text(), "test content")

        # 验证文件路径
        expected_path = self.base_dir / "测试公司" / "测试文件.pdf"
        self.assertEqual(final_path, expected_path)

    def test_organize_downloaded_file_nonexistent(self):
        """测试组织不存在的文件"""
        nonexistent_file = self.base_dir / "nonexistent.pdf"

        with self.assertRaises(FileNotFoundError):
            self.directory_manager.organize_downloaded_file(
                nonexistent_file, "300470", "test.pdf", self.base_dir
            )

    def test_validate_directory_structure_valid(self):
        """测试验证有效的目录结构"""
        # 创建有效的目录结构
        company_dir = self.base_dir / "测试公司"
        company_dir.mkdir()

        # 创建测试文件
        test_file = company_dir / "test.pdf"
        test_file.write_text("test")

        # 验证目录结构
        is_valid, issues = self.directory_manager.validate_directory_structure(
            self.base_dir, ["测试公司"]
        )

        self.assertTrue(is_valid)
        self.assertEqual(issues, [])

    def test_validate_directory_structure_invalid(self):
        """测试验证无效的目录结构"""
        # 创建根目录文件（无效）
        root_file = self.base_dir / "root_file.pdf"
        root_file.write_text("test")

        # 验证目录结构
        is_valid, issues = self.directory_manager.validate_directory_structure(
            self.base_dir, ["测试公司"]
        )

        self.assertFalse(is_valid)
        self.assertIn("根目录中存在文件", issues[0])
        self.assertIn("公司目录不存在", issues[1])

    def test_validate_directory_structure_nonexistent_base(self):
        """测试验证不存在的基目录"""
        nonexistent_dir = self.base_dir / "nonexistent"

        is_valid, issues = self.directory_manager.validate_directory_structure(
            nonexistent_dir, ["测试公司"]
        )

        self.assertFalse(is_valid)
        self.assertIn("基础目录不存在", issues[0])


if __name__ == "__main__":
    unittest.main()