#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试
测试完整集成工作流
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from main_parallel import MultiCompanyDownloader


class TestIntegration:
    """完整集成测试"""

    def test_end_to_end_workflow(self):
        """端到端工作流测试"""
        # 创建测试配置
        test_config = {
            "companies": [
                {
                    "stock_code": "300470",
                    "company_name": "中密控股",
                    "enabled": True,
                    "priority": 1
                }
            ],
            "parallel_download": {
                "enabled": True,
                "max_workers": 2
            },
            "proxy_management": {
                "enabled": False
            }
        }

        # 模拟依赖服务
        with patch('src.data.mapping.MappingManager') as mock_mapping:
            mock_mapping.return_value.get_org_id.return_value = '9900012345'

            with patch('src.services.downloader.DownloadService') as mock_service:
                mock_service_instance = Mock()
                mock_service_instance.download_stock_pdfs.return_value = {
                    'success': True,
                    'files_downloaded': 1,
                    'execution_time': 5.0
                }
                mock_service.return_value = mock_service_instance

                # 创建下载器
                downloader = MultiCompanyDownloader(test_config)

                # 执行下载
                results = downloader.download_all_companies()

                # 验证结果
                assert len(results) == 1
                assert results[0]['success'] is True
                assert results[0]['stock_code'] == '300470'
                assert results[0]['files_downloaded'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])