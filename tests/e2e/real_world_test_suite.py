#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真实世界端到端测试套件（需要网络连接）
基于真实股票代码和实际网站进行测试，验证整个下载流程
注意：这些测试需要网络连接，并且会访问真实网站，执行时间较长
这是真正的端到端测试，区别于使用mock对象的组件集成测试
"""

import pytest
import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.downloader import DownloadService
from src.core.config import ConfigManager

# 网络环境感知装饰器
try:
    from tests.utils.network_decorators import requires_network, NetworkStatus
    NETWORK_DECORATORS_AVAILABLE = True
except ImportError:
    NETWORK_DECORATORS_AVAILABLE = False
    # 如果装饰器不可用，创建一个简单的替代
    def requires_network(func=None, *, skip_on_failure=True, checker=None, message=None):
        if func is None:
            return lambda f: f  # 返回一个什么都不做的装饰器
        return func

# E2E测试结果分析器
try:
    from tests.utils.e2e_test_analyzer import E2ETestAnalyzer, TestResultCategory
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False


# 标记为慢速测试，默认不运行
pytestmark = pytest.mark.slow


def load_real_stock_codes() -> List[Dict[str, Any]]:
    """加载真实股票代码"""
    config_path = Path(__file__).parent / "real_stock_codes.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["stocks"]


class TestRealWorldEndToEnd:
    """真实世界端到端测试（需要网络连接）"""

    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        cls.logger = logging.getLogger(__name__)
        cls.stock_codes = load_real_stock_codes()
        cls.logger.info(f"加载了 {len(cls.stock_codes)} 个股票代码用于测试")

        # 创建临时下载目录
        cls.temp_dir = Path(__file__).parent / "temp_downloads"
        cls.temp_dir.mkdir(exist_ok=True)

        # 初始化测试结果分析器（如果可用）
        cls.analyzer = None
        if ANALYZER_AVAILABLE:
            try:
                cls.analyzer = E2ETestAnalyzer()
                cls.logger.info("测试结果分析器初始化成功")
            except Exception as e:
                cls.logger.warning(f"测试结果分析器初始化失败: {e}")
        else:
            cls.logger.info("测试结果分析器不可用，跳过分析功能")

    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        # 清理临时文件
        import shutil
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
            cls.logger.info(f"清理临时目录: {cls.temp_dir}")

        # 生成测试结果分析报告（如果分析器可用）
        if cls.analyzer is not None:
            try:
                report_file = cls.analyzer.generate_report()
                cls.logger.info(f"测试结果分析报告已生成: {report_file}")

                # 打印摘要信息
                summary = cls.analyzer.get_summary()
                cls.logger.info(f"测试结果摘要: 总共 {summary['total_tests']} 个测试, "
                              f"成功 {summary['successful_tests']} 个, "
                              f"失败 {summary['failed_tests']} 个")

                if summary['failed_tests'] > 0:
                    cls.logger.warning(f"有 {summary['failed_tests']} 个测试失败，请查看详细报告")
            except Exception as e:
                cls.logger.error(f"生成测试结果分析报告失败: {e}")

    @pytest.fixture
    def download_service(self):
        """创建下载服务实例"""
        config = ConfigManager()
        service = DownloadService(
            save_dir=str(self.temp_dir),
            config_file=config.config_path
        )
        yield service
        # 测试后清理
        service.cleanup()

    @pytest.mark.network
    @requires_network
    def test_single_stock_download(self, download_service):
        """测试单个股票下载"""
        if not self.stock_codes:
            pytest.skip("没有可用的股票代码")

        stock = self.stock_codes[0]
        self.logger.info(f"测试股票下载: {stock['code']} - {stock['name']}")

        # 下载股票PDF
        result = download_service.download_stock_pdfs(
            stock_codes=[stock['code']],
            max_pages=1,  # 限制页数
            timeout=120  # 延长超时时间
        )

        # 验证结果
        assert result is not None
        assert "success" in result or "completed" in result or result.get("status") in ["completed", "success"]

        # 检查下载历史
        history = download_service.get_download_history()
        assert len(history) > 0

        self.logger.info(f"股票 {stock['code']} 下载完成，结果: {result}")

    @pytest.mark.network
    def test_multiple_stocks_download(self, download_service):
        """测试多个股票下载"""
        if len(self.stock_codes) < 2:
            pytest.skip("没有足够的股票代码")

        test_codes = [stock['code'] for stock in self.stock_codes[:2]]
        self.logger.info(f"测试多个股票下载: {test_codes}")

        result = download_service.download_stock_pdfs(
            stock_codes=test_codes,
            max_pages=1,
            timeout=180
        )

        assert result is not None
        self.logger.info(f"多个股票下载完成，结果: {result}")

    @pytest.mark.network
    @pytest.mark.long
    def test_full_workflow_with_retry(self, download_service):
        """测试完整工作流，包括重试机制"""
        if not self.stock_codes:
            pytest.skip("没有可用的股票代码")

        stock = self.stock_codes[0]

        # 模拟网络问题，测试重试机制
        original_retry = download_service.max_retries
        download_service.max_retries = 2

        try:
            result = download_service.download_stock_pdfs(
                stock_codes=[stock['code']],
                max_pages=1,
                timeout=90
            )
            assert result is not None
        finally:
            download_service.max_retries = original_retry

        self.logger.info(f"完整工作流测试完成，结果: {result}")

    @pytest.mark.network
    def test_download_with_proxy(self):
        """测试使用代理下载"""
        # 检查是否配置了代理
        config = ConfigManager()
        proxy_config = config.config.get("proxy", {})

        if not proxy_config.get("enabled", False):
            pytest.skip("代理未启用")

        # 创建带代理的下载服务
        service = DownloadService(
            save_dir=str(self.temp_dir),
            max_downloads_per_session=1,
            config_file=config.config_path
        )

        if not self.stock_codes:
            pytest.skip("没有可用的股票代码")

        stock = self.stock_codes[0]
        result = service.download_stock_pdfs(
            stock_codes=[stock['code']],
            max_pages=1,
            timeout=120
        )

        assert result is not None
        self.logger.info(f"代理下载测试完成，结果: {result}")

        service.cleanup()

    @pytest.mark.network
    def test_error_handling_in_real_world(self, download_service):
        """测试真实世界中的错误处理"""
        # 使用无效股票代码测试错误处理
        invalid_codes = ["999999", "INVALID"]

        result = download_service.download_stock_pdfs(
            stock_codes=invalid_codes,
            max_pages=1,
            timeout=60
        )

        # 即使股票代码无效，也应该有相应的错误处理结果
        assert result is not None
        self.logger.info(f"错误处理测试完成，结果: {result}")

    def test_offline_mode(self, download_service):
        """测试离线模式（不实际下载）"""
        # 模拟无网络情况
        self.logger.info("测试离线模式 - 仅验证逻辑，不实际下载")

        # 验证服务初始化正常
        assert download_service is not None
        assert download_service.save_dir == str(self.temp_dir)

        # 验证配置加载正常
        config = download_service.config
        assert config is not None

        self.logger.info("离线模式测试完成")

    @pytest.mark.network
    def test_performance_benchmark(self, download_service):
        """测试性能基准"""
        if not self.stock_codes:
            pytest.skip("没有可用的股票代码")

        stock = self.stock_codes[0]

        import time
        start_time = time.time()

        result = download_service.download_stock_pdfs(
            stock_codes=[stock['code']],
            max_pages=1,
            timeout=120
        )

        end_time = time.time()
        elapsed = end_time - start_time

        self.logger.info(f"性能测试 - 股票 {stock['code']} 下载耗时: {elapsed:.2f} 秒")

        # 验证下载时间在合理范围内
        assert elapsed < 300  # 5分钟上限

        assert result is not None


if __name__ == "__main__":
    # 直接运行测试（需要网络）
    pytest.main([__file__, "-v", "-m", "network"])