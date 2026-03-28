"""
Directory Manager Module Tests
Tests for directory management functionality
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.utils.directory_manager import DirectoryManager, create_directory_manager


class TestDirectoryManager:
    """DirectoryManager class tests"""

    def test_init_default(self):
        """Test initialization without mapping manager"""
        manager = DirectoryManager()
        assert manager.mapping_manager is None

    def test_init_with_mapping_manager(self):
        """Test initialization with mapping manager"""
        mock_manager = MagicMock()
        manager = DirectoryManager(mock_manager)
        assert manager.mapping_manager is mock_manager

    def test_get_company_directory_no_manager(self):
        """Test get company directory without mapping manager"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test")
        result = manager.get_company_directory("000001", base_dir)

        # Should return stock code as directory name
        assert result == base_dir / "000001"

    def test_get_company_directory_with_manager(self):
        """Test get company directory with mapping manager"""
        mock_manager = MagicMock()
        mock_manager.get_stock_name.return_value = "TestCompany"

        manager = DirectoryManager(mock_manager)
        base_dir = Path("/tmp/test")
        result = manager.get_company_directory("000001", base_dir)

        assert result == base_dir / "TestCompany"
        mock_manager.get_stock_name.assert_called_once_with("000001")

    def test_get_company_directory_manager_returns_none(self):
        """Test get company directory when manager returns None"""
        mock_manager = MagicMock()
        mock_manager.get_stock_name.return_value = None

        manager = DirectoryManager(mock_manager)
        base_dir = Path("/tmp/test")
        result = manager.get_company_directory("000001", base_dir)

        # Should fall back to stock code
        assert result == base_dir / "000001"

    def test_create_company_directory(self):
        """Test creating company directory"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test_dir_manager")
        stock_code = "000001"

        with patch("pathlib.Path.mkdir"):
            result = manager.create_company_directory(stock_code, base_dir)
            assert result == base_dir / "000001"

    def test_ensure_save_directory(self):
        """Test ensuring save directory exists"""
        manager = DirectoryManager()
        save_path = Path("/tmp/test/file.pdf")

        with patch("pathlib.Path.mkdir"):
            manager.ensure_save_directory(save_path)

    def test_organize_downloaded_file(self):
        """Test organizing downloaded file"""
        manager = DirectoryManager()
        temp_path = Path("/tmp/temp_file.pdf")
        base_dir = Path("/tmp/downloads")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.move"), \
             patch("pathlib.Path.mkdir"):
            result = manager.organize_downloaded_file(
                temp_path, "000001", "file.pdf", base_dir
            )
            assert result == base_dir / "000001" / "file.pdf"

    def test_organize_downloaded_file_not_exists(self):
        """Test organizing file when temp file doesn't exist"""
        manager = DirectoryManager()
        temp_path = Path("/tmp/nonexistent.pdf")
        base_dir = Path("/tmp/downloads")

        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                manager.organize_downloaded_file(
                    temp_path, "000001", "file.pdf", base_dir
                )

    def test_organize_downloaded_file_move_failure(self):
        """Test organizing file when move fails"""
        manager = DirectoryManager()
        temp_path = Path("/tmp/temp_file.pdf")
        base_dir = Path("/tmp/downloads")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("shutil.move", side_effect=Exception("Move failed")), \
             patch("pathlib.Path.mkdir"):
            with pytest.raises(Exception, match="Move failed"):
                manager.organize_downloaded_file(
                    temp_path, "000001", "file.pdf", base_dir
                )

    def test_validate_directory_structure_no_base_dir(self):
        """Test validation when base directory doesn't exist"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/nonexistent")

        with patch("pathlib.Path.exists", return_value=False):
            is_valid, issues = manager.validate_directory_structure(base_dir, [])
            assert is_valid is False
            assert "基础目录不存在" in issues[0]

    def test_validate_directory_structure_with_files(self):
        """Test validation when root has files"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test")
        expected = ["CompanyA", "CompanyB"]

        mock_item = MagicMock()
        mock_item.is_file.return_value = True
        mock_item.name = "temp.txt"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.iterdir", return_value=[mock_item]):
            is_valid, issues = manager.validate_directory_structure(base_dir, expected)
            assert is_valid is False
            assert "根目录中存在文件" in issues[0]

    def test_validate_directory_structure_unexpected_dirs(self):
        """Test validation with unexpected directories"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test")
        expected = ["CompanyA"]

        mock_item = MagicMock()
        mock_item.is_file.return_value = False
        mock_item.is_dir.return_value = True
        mock_item.name = "UnexpectedDir"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.iterdir", return_value=[mock_item]):
            is_valid, issues = manager.validate_directory_structure(base_dir, expected)
            assert is_valid is False
            assert "非预期的目录" in issues[0]

    def test_validate_directory_structure_missing_dirs(self):
        """Test validation with missing expected directories"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test")
        expected = ["CompanyA"]

        # Base dir exists but company dir doesn't
        mock_item = MagicMock()
        mock_item.is_file.return_value = False
        mock_item.is_dir.return_value = True
        mock_item.name = "CompanyB"

        # Only base_dir exists, CompanyA doesn't exist
        def mock_exists(self):
            return self == base_dir

        with patch("pathlib.Path.exists", mock_exists), \
             patch("pathlib.Path.is_dir", return_value=False), \
             patch("pathlib.Path.iterdir", return_value=[mock_item]):
            is_valid, issues = manager.validate_directory_structure(base_dir, expected)
            assert is_valid is False
            assert any("目录不存在" in issue for issue in issues)

    def test_validate_directory_structure_success(self):
        """Test successful validation"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test")
        expected = ["CompanyA", "CompanyB"]

        # Mock items: expected directories exist
        mock_item_a = MagicMock()
        mock_item_a.is_file.return_value = False
        mock_item_a.is_dir.return_value = True
        mock_item_a.name = "CompanyA"

        mock_item_b = MagicMock()
        mock_item_b.is_file.return_value = False
        mock_item_b.is_dir.return_value = True
        mock_item_b.name = "CompanyB"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_dir", return_value=True), \
             patch("pathlib.Path.iterdir", return_value=[mock_item_a, mock_item_b]):
            is_valid, issues = manager.validate_directory_structure(base_dir, expected)
            assert is_valid is True
            assert len(issues) == 0

    def test_validate_directory_structure_with_path_is_file(self):
        """Test validation when company path is a file not directory"""
        manager = DirectoryManager()
        base_dir = Path("/tmp/test")
        expected = ["CompanyA"]

        mock_item = MagicMock()
        mock_item.is_file.return_value = False
        mock_item.is_dir.return_value = False
        mock_item.name = "CompanyA"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.iterdir", return_value=[mock_item]):
            is_valid, issues = manager.validate_directory_structure(base_dir, expected)
            assert is_valid is False
            assert "路径不是目录" in issues[0]


class TestCreateDirectoryManager:
    """create_directory_manager function tests"""

    @patch("src.data.mapping.MappingManager")
    def test_create_directory_manager_default(self, mock_mm):
        """Test creating directory manager with default file"""
        mock_manager = MagicMock()
        mock_mm.return_value = mock_manager

        result = create_directory_manager()

        mock_mm.assert_called_once_with("stock_orgid_mapping.json")
        assert isinstance(result, DirectoryManager)

    @patch("src.data.mapping.MappingManager")
    def test_create_directory_manager_custom_file(self, mock_mm):
        """Test creating directory manager with custom file"""
        mock_manager = MagicMock()
        mock_mm.return_value = mock_manager

        result = create_directory_manager("custom_mapping.json")

        mock_mm.assert_called_once_with("custom_mapping.json")
        assert isinstance(result, DirectoryManager)
