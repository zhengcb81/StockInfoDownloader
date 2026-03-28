#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多公司下载器测试
测试多公司下载器的功能
"""

import os

# 添加项目根目录到Python路径
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.tools.legacy.main_parallel import CompanyConfig, MultiCompanyDownloader


class TestMultiCompanyDownloader:
    """测试多公司下载器"""

    @pytest.fixture
    def downloader_config(self):
        """下载器配置fixture"""
        return {
            "environment": "test",
            "save_dir": "test_downloads",
            "companies": [
                {
                    "stock_code": "300470",
                    "company_name": "中密控股",
                    "enabled": True,
                    "priority": 1,
                },
                {
                    "stock_code": "301611",
                    "company_name": "珂玛科技",
                    "enabled": True,
                    "priority": 2,
                },
            ],
            "parallel_download": {
                "enabled": True,
                "max_workers": 2,
                "task_timeout": 30,
            },
            "proxy_management": {"enabled": False},
        }

    @pytest.fixture
    def downloader(self, downloader_config):
        """下载器fixture"""
        with patch("src.data.mapping.MappingManager") as mock_mapping:
            # 模拟映射管理器
            mock_mapping.return_value.get_org_id.return_value = "9900012345"
            mock_mapping.return_value.get_stock_name.return_value = "测试公司"

            # 关键修复：拦截 main_parallel 中的 downloader_factory 实例方法
            with patch(
                "src.tools.legacy.main_parallel.downloader_factory.create_legacy_adapter"
            ) as mock_factory:
                mock_adapter_instance = Mock()

                # 创建DownloadResult对象（适配main_parallel.py的期望）
                from src.interfaces.downloader_interface import DownloadResult

                mock_result = DownloadResult(
                    success=True,
                    downloaded_files=[
                        "downloads/测试公司/test1.pdf",
                        "downloads/测试公司/test2.pdf",
                        "downloads/测试公司/test3.pdf",
                    ],
                    total_files=3,
                    errors=[],
                    duration_seconds=1.0,
                    metadata={},
                )
                mock_adapter_instance.download_stock_pdfs.return_value = mock_result
                mock_factory.return_value = mock_adapter_instance

                yield MultiCompanyDownloader(downloader_config)

    def test_get_company_configs(self, downloader):
        """测试获取公司配置"""
        configs = downloader.get_company_configs()

        assert len(configs) == 2
        assert isinstance(configs[0], CompanyConfig)
        assert configs[0].stock_code == "300470"
        assert configs[1].stock_code == "301611"

    def test_download_company(self, downloader):
        """测试下载单个公司"""
        company_config = downloader.get_company_configs()[0]
        result = downloader.download_company(company_config)

        assert result["success"] is True
        assert result["stock_code"] == "300470"
        assert result["files_downloaded"] > 0

    def test_download_companies_sequential(self, downloader):
        """测试串行下载多个公司"""
        configs = downloader.get_company_configs()
        results = downloader.download_companies_sequential(configs)

        assert len(results) == 2
        assert all(result["success"] for result in results)

    def test_download_companies_parallel(self, downloader):
        """测试并行下载多个公司"""
        configs = downloader.get_company_configs()
        results = downloader.download_companies_parallel(configs)

        assert len(results) == 2
        assert all(result["success"] for result in results)

    def test_download_all_companies(self, downloader):
        """测试下载所有公司"""
        results = downloader.download_all_companies()

        assert len(results) == 2
        assert all(result["success"] for result in results)

    def test_print_summary(self, downloader, caplog):
        """测试打印摘要"""
        results = [
            {
                "success": True,
                "stock_code": "300470",
                "company_name": "中密控股",
                "files_downloaded": 3,
                "execution_time": 15.0,
            },
            {
                "success": True,
                "stock_code": "301611",
                "company_name": "珂玛科技",
                "files_downloaded": 2,
                "execution_time": 12.0,
            },
        ]

        downloader.print_summary(results)

        # 检查日志输出（使用caplog捕获logger输出）
        log_messages = [record.message for record in caplog.records]
        log_text = "\n".join(log_messages)

        assert "总处理公司数: 2" in log_text
        assert "成功下载公司数: 2" in log_text
        assert "下载文件总数: 5" in log_text

    @patch("src.tools.legacy.main_parallel.get_stock_name")
    def test_main_functionality(self, mock_get_stock_name, downloader_config, capsys):
        """测试主要功能"""
        # 模拟股票名称获取
        mock_get_stock_name.return_value = "测试公司"

        with patch("src.data.mapping.MappingManager") as mock_mapping:
            mock_mapping.return_value.get_org_id.return_value = "9900012345"

            # 关键修复：使用工厂模式mock
            with patch(
                "src.tools.legacy.main_parallel.downloader_factory.create_legacy_adapter"
            ) as mock_factory:
                mock_adapter_instance = Mock()
                # 创建DownloadResult对象（适配main_parallel.py的期望）
                from src.interfaces.downloader_interface import DownloadResult

                mock_result = DownloadResult(
                    success=True,
                    downloaded_files=[
                        "downloads/测试公司/test1.pdf",
                        "downloads/测试公司/test2.pdf",
                    ],
                    total_files=2,
                    errors=[],
                    duration_seconds=1.0,
                    metadata={},
                )
                mock_adapter_instance.download_stock_pdfs.return_value = mock_result
                mock_factory.return_value = mock_adapter_instance

                # 娴嬭瘯涓荤▼搴
                from src.tools.legacy.main_parallel import main

                with patch(
                    "sys.argv", ["main_parallel.py", "--config", "test_config.json"]
                ):
                    with patch("os.path.exists", return_value=True):
                        with patch(
                            "src.core.config.ConfigManager.load_config"
                        ) as mock_load:
                            mock_load.return_value = downloader_config
                            exit_code = main()

        assert exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
