"""
Selenium Download Manager Module Unit Tests
测试Selenium下载管理器功能
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.web.selenium.download_manager import DownloadManager


class TestDownloadManager:
    """测试下载管理器"""

    def test_initialization(self):
        """测试初始化"""
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver, download_dir="/tmp/downloads")

        assert manager.driver == mock_driver
        assert manager.download_dir == "/tmp/downloads"
        assert manager.download_count == 0

    def test_initialization_without_download_dir(self):
        """测试无下载目录初始化"""
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        assert manager.driver == mock_driver
        assert manager.download_dir is None

    @patch('src.web.selenium.download_manager.os.path.exists')
    def test_prepare_download_no_dir(self, mock_exists):
        """测试无下载目录的准备下载"""
        mock_exists.return_value = False
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver, download_dir="/tmp/downloads")

        result = manager._prepare_download()

        assert result == True

    @patch('src.web.selenium.download_manager.os.walk')
    @patch('src.web.selenium.download_manager.os.path.exists')
    def test_prepare_download_with_dir(self, mock_exists, mock_walk):
        """测试有下载目录的准备下载"""
        mock_exists.return_value = True
        mock_walk.return_value = []
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver, download_dir="/tmp/downloads")

        result = manager._prepare_download()

        assert result == True

    @patch('src.web.selenium.download_manager.Path')
    def test_check_for_new_file_no_dir(self, mock_path):
        """测试无下载目录时检查新文件"""
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver, download_dir=None)

        result = manager._check_for_new_file()

        assert result is None

    @patch('src.web.selenium.download_manager.os.path.exists')
    def test_check_target_file_exists(self, mock_exists):
        """测试检查目标文件是否存在"""
        from src.core.constants import FileSizeThreshold
        mock_exists.return_value = True
        mock_driver = Mock()

        with patch('os.path.getsize', return_value=FileSizeThreshold.MIN_VALID_PDF + 1):
            manager = DownloadManager(driver=mock_driver)
            result = manager._check_target_file_exists("/tmp/test.pdf")

            assert result == True

    @patch('src.web.selenium.download_manager.os.path.exists')
    def test_check_target_file_not_exists(self, mock_exists):
        """测试检查目标文件不存在"""
        mock_exists.return_value = False
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        result = manager._check_target_file_exists("/tmp/test.pdf")

        assert result == False

    @patch('src.web.selenium.download_manager.os.path.exists')
    @patch('src.web.selenium.download_manager.os.path.getsize')
    @patch('src.web.selenium.download_manager.os.remove')
    def test_handle_timeout(self, mock_remove, mock_getsize, mock_exists):
        """测试处理超时"""
        mock_exists.return_value = True
        mock_getsize.return_value = 100
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        result = manager._handle_timeout("/tmp/test.pdf", 0.0)

        assert result == False
        mock_remove.assert_called_once()

    @patch('src.web.selenium.download_manager.time')
    def test_log_download_progress(self, mock_time):
        """测试记录下载进度"""
        mock_time.time.return_value = 15
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver, download_dir="/tmp/downloads")

        # Should log progress
        manager._log_download_progress(0.0)

    @patch('src.web.selenium.download_manager.Path')
    def test_handle_downloaded_file_no_file(self, mock_path):
        """测试处理不存在的下载文件"""
        mock_file = Mock()
        mock_file.exists.return_value = False
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        result = manager._handle_downloaded_file(mock_file, "/tmp/test.pdf")

        assert result == False

    @patch('src.web.selenium.download_manager.Path')
    def test_handle_downloaded_file_too_small(self, mock_path):
        """测试处理太小的文件"""
        from src.core.constants import FileSizeThreshold
        mock_file = Mock()
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = FileSizeThreshold.MIN_VALID_PDF - 1
        mock_file.suffix = ".pdf"
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        result = manager._handle_downloaded_file(mock_file, "/tmp/test.pdf")

        assert result == False

    @patch('src.web.selenium.download_manager.shutil.move')
    @patch('src.web.selenium.download_manager.Path')
    def test_move_file_to_target_same_path(self, mock_path_class, mock_move):
        """测试移动文件到相同路径"""
        from src.core.constants import FileSizeThreshold
        
        # Setup mocks
        mock_source = MagicMock()
        mock_target = MagicMock()
        
        # Source and target resolve to the same thing
        resolved_path = MagicMock()
        mock_source.resolve.return_value = resolved_path
        mock_target.resolve.return_value = resolved_path
        
        # Size is valid
        mock_source.stat.return_value.st_size = FileSizeThreshold.MIN_VALID_PDF + 1
        
        # Path() calls
        mock_path_class.side_effect = lambda x: mock_target if x == "/tmp/test.pdf" else MagicMock()
        
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        result = manager._move_file_to_target(mock_source, "/tmp/test.pdf")

        assert result == True
        mock_move.assert_not_called()

    @patch('src.web.selenium.download_manager.shutil.move')
    @patch('src.web.selenium.download_manager.Path')
    def test_move_file_to_target_different_path(self, mock_path_class, mock_move):
        """测试移动文件到不同路径"""
        from src.core.constants import FileSizeThreshold
        
        # Setup mocks
        mock_source = MagicMock()
        mock_target = MagicMock()
        
        # Source and target resolve to DIFFERENT things
        mock_source.resolve.return_value = MagicMock()
        mock_target.resolve.return_value = MagicMock()
        
        # Source exists and is valid
        mock_source.exists.return_value = True
        mock_source.stat.return_value.st_size = FileSizeThreshold.MIN_VALID_PDF + 1
        
        # Target exists after move and is valid
        mock_target.exists.return_value = True
        mock_target.stat.return_value.st_size = FileSizeThreshold.MIN_VALID_PDF + 1
        
        # Path() calls
        def path_side_effect(x):
            if x == "/tmp/test.pdf":
                return mock_target
            return MagicMock()
            
        mock_path_class.side_effect = path_side_effect
        
        mock_driver = Mock()
        manager = DownloadManager(driver=mock_driver)

        result = manager._move_file_to_target(mock_source, "/tmp/test.pdf")

        assert result == True
        mock_move.assert_called_once()
