#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多公司并行下载集成测试
测试新的多公司配置和并行下载功能
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import ConfigManager
from src.services.parallel_downloader import ParallelDownloadManager, TaskPriority, TaskStatus
from src.web.proxy_manager import ProxyManager, ProxyType
from src.web.anti_crawler_enhanced import EnhancedAntiCrawler, AntiCrawlerLevel
from main_parallel import MultiCompanyDownloader, CompanyConfig


class TestConfigManagerMultiCompany:
    """测试配置管理器的多公司支持"""

    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        config_data = {
            "environment": "test",
            "save_dir": "test_downloads",
            "companies": [
                {
                    "stock_code": "300470",
                    "company_name": "中密控股",
                    "enabled": True,
                    "priority": 1,
                    "custom_pages": None
                },
                {
                    "stock_code": "301611",
                    "company_name": "珂玛科技",
                    "enabled": True,
                    "priority": 2,
                    "custom_pages": [
                        {"name": "自定义页面", "suffix": "custom", "allowed_keywords": ["测试"]}
                    ]
                },
                {
                    "stock_code": "000001",
                    "company_name": "测试公司",
                    "enabled": False,
                    "priority": 3,
                    "custom_pages": None
                }
            ],
            "parallel_download": {
                "enabled": True,
                "max_workers": 5,
                "task_timeout": 300
            },
            "proxy_management": {
                "enabled": True,
                "pools": {
                    "test_pool": {
                        "enabled": True,
                        "max_size": 10
                    }
                }
            }
        }

        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(config_data, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()

        yield temp_file.name

        # 清理
        Path(temp_file.name).unlink(missing_ok=True)

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """配置管理器fixture"""
        return ConfigManager(temp_config_file)

    def test_get_companies(self, config_manager):
        """测试获取公司列表"""
        companies = config_manager.get_companies()

        assert len(companies) == 2  # 只有启用的公司
        assert companies[0]['stock_code'] == '300470'  # 按优先级排序
        assert companies[1]['stock_code'] == '301611'
        assert companies[0]['company_name'] == '中密控股'
        assert companies[1]['company_name'] == '珂玛科技'

    def test_get_company_config(self, config_manager):
        """测试获取特定公司配置"""
        company = config_manager.get_company_config('301611')
        assert company is not None
        assert company['stock_code'] == '301611'
        assert company['company_name'] == '珂玛科技'
        assert company['custom_pages'] is not None
        assert len(company['custom_pages']) == 1

    def test_add_company(self, config_manager):
        """测试添加公司"""
        success = config_manager.add_company('000002', '新测试公司', priority=4)
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 3
        assert any(c['stock_code'] == '000002' for c in companies)

    def test_remove_company(self, config_manager):
        """测试移除公司"""
        success = config_manager.remove_company('300470')
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 1
        assert not any(c['stock_code'] == '300470' for c in companies)

    def test_enable_disable_company(self, config_manager):
        """测试启用/禁用公司"""
        # 禁用公司
        success = config_manager.disable_company('301611')
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 1  # 只有一个启用
        assert not any(c['stock_code'] == '301611' for c in companies)

        # 重新启用
        success = config_manager.enable_company('301611')
        assert success

        companies = config_manager.get_companies()
        assert len(companies) == 2

    def test_validate_companies_config(self, config_manager):
        """测试验证公司配置"""
        is_valid, errors = config_manager.validate_companies_config()
        assert is_valid
        assert len(errors) == 0

    def test_validate_invalid_config(self, config_manager):
        """测试验证无效配置"""
        # 添加无效配置
        config_manager.add_company('invalid', '无效公司')

        is_valid, errors = config_manager.validate_companies_config()
        assert not is_valid
        assert any('股票代码格式错误' in error for error in errors)

    def test_get_companies_summary(self, config_manager):
        """测试获取公司配置摘要"""
        summary = config_manager.get_companies_summary()

        assert summary['total_companies'] == 3  # 总公司数（包括禁用的）
        assert summary['enabled_companies'] == 2  # 启用公司数
        assert summary['disabled_companies'] == 1  # 禁用公司数
        assert '300470' in summary['stock_codes']
        assert '301611' in summary['stock_codes']
        assert summary['parallel_download_enabled'] is True
        assert summary['proxy_enabled'] is True
        assert summary['max_workers'] == 5


class TestParallelDownloadManager:
    """测试并行下载管理器"""

    @pytest.fixture
    def download_manager(self):
        """下载管理器fixture"""
        config = {
            'task_timeout': 60,
            'retry_policy': {
                'max_retries': 2,
                'retry_delay': 1,
                'backoff_factor': 1.5
            }
        }
        return ParallelDownloadManager(max_workers=3, config=config)

    def test_add_task(self, download_manager):
        """测试添加任务"""
        task_id = download_manager.add_task(
            stock_code='300470',
            company_name='测试公司',
            target_pages=[{'suffix': 'research', 'allowed_keywords': None}]
        )

        assert task_id is not None
        assert isinstance(task_id, str)

        # 检查任务是否添加成功
        task = download_manager.task_queue.get_task(task_id)
        assert task is not None
        assert task.stock_code == '300470'
        assert task.company_name == '测试公司'

    def test_task_priority(self, download_manager):
        """测试任务优先级"""
        # 添加不同优先级的任务
        task1_id = download_manager.add_task(
            '300470', '公司1', [{'suffix': 'research'}], TaskPriority.LOW
        )
        task2_id = download_manager.add_task(
            '301611', '公司2', [{'suffix': 'research'}], TaskPriority.HIGH
        )

        # 高优先级任务应该先执行
        task1 = download_manager.task_queue.get_task(task1_id)
        task2 = download_manager.task_queue.get_task(task2_id)

        assert task1.priority == TaskPriority.LOW
        assert task2.priority == TaskPriority.HIGH

    def test_start_stop_manager(self, download_manager):
        """测试启动和停止管理器"""
        # 添加任务
        download_manager.add_task('300470', '测试公司', [{'suffix': 'research'}])

        # 启动管理器
        download_manager.start()
        assert download_manager._running is True

        # 等待一段时间让任务处理
        time.sleep(2)

        # 停止管理器
        download_manager.stop()
        assert download_manager._running is False

    def test_task_status_tracking(self, download_manager):
        """测试任务状态跟踪"""
        task_id = download_manager.add_task('300470', '测试公司', [{'suffix': 'research'}])

        # 获取任务状态
        status = download_manager.get_task_status(task_id)
        assert status is not None
        assert status['stock_code'] == '300470'
        assert status['status'] == 'pending'

        # 获取所有任务状态
        all_status = download_manager.get_all_tasks_status()
        assert len(all_status) >= 1

    def test_manager_stats(self, download_manager):
        """测试管理器统计信息"""
        # 添加一些任务
        download_manager.add_task('300470', '公司1', [{'suffix': 'research'}])
        download_manager.add_task('301611', '公司2', [{'suffix': 'research'}])

        stats = download_manager.get_stats()
        assert 'manager_stats' in stats
        assert 'resource_usage' in stats
        assert 'queue_size' in stats
        assert stats['queue_size'] >= 2
        assert stats['max_workers'] == 3


class TestProxyManager:
    """测试代理管理器"""

    @pytest.fixture
    def proxy_config(self):
        """代理配置fixture"""
        return {
            'enabled': True,
            'pools': {
                'test_pool': {
                    'enabled': True,
                    'max_size': 5,
                    'health_check_interval': 30
                }
            },
            'static_proxies': [
                {
                    'ip': '127.0.0.1',
                    'port': 8080,
                    'type': 'http',
                    'pool': 'test_pool'
                },
                {
                    'ip': '127.0.0.1',
                    'port': 1080,
                    'type': 'socks5',
                    'pool': 'test_pool'
                }
            ]
        }

    def test_proxy_manager_initialization(self, proxy_config):
        """测试代理管理器初始化"""
        manager = ProxyManager(proxy_config)
        assert manager is not None
        assert len(manager.pools) == 1
        assert 'test_pool' in manager.pools

    def test_get_proxy(self, proxy_config):
        """测试获取代理"""
        manager = ProxyManager(proxy_config)
        proxy = manager.get_proxy()

        # 由于是测试代理，可能无法连接，但应该返回代理对象
        # 在实际环境中，这里会返回真实的代理
        assert proxy is not None

    def test_proxy_stats(self, proxy_config):
        """测试代理统计信息"""
        manager = ProxyManager(proxy_config)
        stats = manager.get_stats()

        assert 'total_pools' in stats
        assert 'pools' in stats
        assert stats['total_pools'] == 1


class TestEnhancedAntiCrawler:
    """测试增强反爬虫机制"""

    @pytest.fixture
    def anti_crawler_config(self):
        """反爬虫配置fixture"""
        return {
            'enabled': True,
            'level': 'high',
            'fingerprint_randomization': {
                'user_agent_rotation': True,
                'screen_resolution': True,
                'timezone': True,
                'language': True
            },
            'behavior_simulation': {
                'complexity_level': 'high',
                'randomization_factor': 0.3,
                'patterns': ['mouse_movement', 'scrolling', 'typing']
            },
            'adaptive_rate_limiting': {
                'initial_requests_per_minute': 30,
                'max_requests_per_minute': 100,
                'adjustment_factor': 1.2
            },
            'captcha_handling': {
                'strategies': ['delay_retry', 'proxy_rotation'],
                'max_wait_time': 120
            }
        }

    def test_anti_crawler_initialization(self, anti_crawler_config):
        """测试反爬虫初始化"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)
        assert anti_crawler is not None
        assert anti_crawler.enabled is True
        assert anti_crawler.level == AntiCrawlerLevel.HIGH

    def test_before_request(self, anti_crawler_config):
        """测试请求前处理"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        context = {
            'user_agents': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ]
        }

        result = anti_crawler.before_request(context)
        assert result['success'] is True
        assert 'fingerprint_changes' in result
        assert 'behavior_simulation' in result

    def test_after_request(self, anti_crawler_config):
        """测试请求后处理"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        response_data = {
            'page_content': '正常页面内容',
            'response_headers': {'content-type': 'text/html'}
        }

        result = anti_crawler.after_request(True, response_data)
        assert result['success'] is True
        assert 'stats' in result

    def test_captcha_detection(self, anti_crawler_config):
        """测试验证码检测"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        # 测试正常页面
        normal_content = '这是一个正常的页面'
        assert not anti_crawler.captcha_handler.detect_captcha(normal_content)

        # 测试包含验证码的页面
        captcha_content = '请输入验证码以继续'
        assert anti_crawler.captcha_handler.detect_captcha(captcha_content)

    def test_rate_limiting(self, anti_crawler_config):
        """测试速率限制"""
        anti_crawler = EnhancedAntiCrawler(anti_crawler_config)

        # 记录一些成功请求
        for i in range(10):
            anti_crawler.rate_limiter.record_request(True)

        # 检查是否可以继续请求
        can_request, wait_time = anti_crawler.rate_limiter.can_make_request()
        assert can_request is True


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
                    "priority": 1
                },
                {
                    "stock_code": "301611",
                    "company_name": "珂玛科技",
                    "enabled": True,
                    "priority": 2
                }
            ],
            "parallel_download": {
                "enabled": True,
                "max_workers": 2,
                "task_timeout": 30
            },
            "proxy_management": {
                "enabled": False
            }
        }

    @pytest.fixture
    def downloader(self, downloader_config):
        """下载器fixture"""
        with patch('src.data.mapping.MappingManager') as mock_mapping:
            # 模拟映射管理器
            mock_mapping.return_value.get_org_id.return_value = '9900012345'
            mock_mapping.return_value.get_stock_name.return_value = '测试公司'

            with patch('src.services.downloader.DownloadService') as mock_service:
                # 模拟下载服务
                mock_service_instance = Mock()
                mock_service_instance.download_stock_pdfs.return_value = {
                    'success': True,
                    'files_downloaded': 3,
                    'execution_time': 15.0
                }
                mock_service.return_value = mock_service_instance

                return MultiCompanyDownloader(downloader_config)

    def test_get_company_configs(self, downloader):
        """测试获取公司配置"""
        configs = downloader.get_company_configs()

        assert len(configs) == 2
        assert isinstance(configs[0], CompanyConfig)
        assert configs[0].stock_code == '300470'
        assert configs[1].stock_code == '301611'

    def test_download_company(self, downloader):
        """测试下载单个公司"""
        company_config = downloader.get_company_configs()[0]
        result = downloader.download_company(company_config)

        assert result['success'] is True
        assert result['stock_code'] == '300470'
        assert result['files_downloaded'] > 0

    def test_download_companies_sequential(self, downloader):
        """测试串行下载多个公司"""
        configs = downloader.get_company_configs()
        results = downloader.download_companies_sequential(configs)

        assert len(results) == 2
        assert all(result['success'] for result in results)

    def test_download_companies_parallel(self, downloader):
        """测试并行下载多个公司"""
        configs = downloader.get_company_configs()
        results = downloader.download_companies_parallel(configs)

        assert len(results) == 2
        assert all(result['success'] for result in results)

    def test_download_all_companies(self, downloader):
        """测试下载所有公司"""
        results = downloader.download_all_companies()

        assert len(results) == 2
        assert all(result['success'] for result in results)

    def test_print_summary(self, downloader, capsys):
        """测试打印摘要"""
        results = [
            {
                'success': True,
                'stock_code': '300470',
                'company_name': '中密控股',
                'files_downloaded': 3,
                'execution_time': 15.0
            },
            {
                'success': True,
                'stock_code': '301611',
                'company_name': '珂玛科技',
                'files_downloaded': 2,
                'execution_time': 12.0
            }
        ]

        downloader.print_summary(results)

        # 检查输出
        captured = capsys.readouterr()
        assert '总处理公司数: 2' in captured.out
        assert '成功下载公司数: 2' in captured.out
        assert '下载文件总数: 5' in captured.out

    @patch('main_parallel.get_stock_name')
    def test_main_functionality(self, mock_get_stock_name, downloader_config, capsys):
        """测试主要功能"""
        # 模拟股票名称获取
        mock_get_stock_name.return_value = '测试公司'

        with patch('src.data.mapping.MappingManager') as mock_mapping:
            mock_mapping.return_value.get_org_id.return_value = '9900012345'

            with patch('src.services.downloader.DownloadService') as mock_service:
                mock_service_instance = Mock()
                mock_service_instance.download_stock_pdfs.return_value = {
                    'success': True,
                    'files_downloaded': 2,
                    'execution_time': 10.0
                }
                mock_service.return_value = mock_service_instance

                # 测试主程序
                from main_parallel import main
                with patch('sys.argv', ['main_parallel.py', '--config', str(Path(__file__).parent / 'test_config.json')]):
                    with patch('src.core.config.ConfigManager.load_config') as mock_load:
                        mock_load.return_value = downloader_config
                        exit_code = main()

        assert exit_code == 0


# 集成测试
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
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])