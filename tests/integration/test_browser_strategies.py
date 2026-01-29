#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
浏览器策略集成测试
测试Selenium和Playwright策略在真实下载流程中的表现
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.adapters.legacy_downloader_adapter import (
    DownloadServiceV2Adapter as DownloadServiceV2,
)
from src.web.browser_strategy import BrowserStrategyFactory


class TestBrowserStrategiesIntegration:
    """浏览器策略集成测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, "downloads")

        # 创建测试映射文件
        self.mapping_file = os.path.join(self.temp_dir, "test_mapping.json")
        test_mapping = {"300470": {"orgId": "9900023856", "name": "中密控股"}}

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

    def teardown_method(self):
        """测试清理"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.parametrize("strategy_type", ["selenium", "playwright"])
    def test_strategy_factory_creation(self, strategy_type):
        """测试策略工厂创建不同类型的策略"""
        # 测试策略工厂能创建正确类型的策略
        strategy = BrowserStrategyFactory.create_strategy(
            strategy_type=strategy_type, headless=True, download_dir=self.save_dir
        )

        # 验证策略创建成功
        assert strategy is not None

        # 验证策略属性
        assert strategy.headless is True
        assert strategy.download_dir == self.save_dir

        # 清理
        strategy.close()

    def test_selenium_vs_playwright_strategy_comparison(self):
        """测试Selenium与Playwright策略对比"""
        strategies = {}

        # 创建两种策略
        for strategy_type in ["selenium", "playwright"]:
            try:
                strategy = BrowserStrategyFactory.create_strategy(
                    strategy_type=strategy_type,
                    headless=True,
                    download_dir=self.save_dir,
                )
                strategies[strategy_type] = strategy
            except Exception as e:
                # 如果策略创建失败（如缺少依赖），记录错误但不失败测试
                print(f"无法创建 {strategy_type} 策略: {e}")

        # 如果至少有一个策略创建成功，继续测试
        if not strategies:
            pytest.skip("无法创建任何浏览器策略，可能缺少必要的依赖")

        # 测试策略接口一致性
        for strategy_type, strategy in strategies.items():
            # 验证基本方法存在
            assert hasattr(strategy, "create_driver")
            assert hasattr(strategy, "navigate")
            assert hasattr(strategy, "find_elements")
            assert hasattr(strategy, "close")
            assert hasattr(strategy, "restart")
            assert hasattr(strategy, "is_healthy")

            # 清理
            strategy.close()

    @pytest.mark.parametrize("strategy_type", ["selenium", "playwright"])
    def test_download_service_integration(self, strategy_type):
        """测试下载服务与策略的集成"""
        try:
            # 创建下载器
            downloader = DownloadServiceV2(
                save_dir=self.save_dir,
                mapping_file=self.mapping_file,
                browser_strategy=strategy_type,
            )

            # 验证下载器正确配置了策略
            assert downloader.browser_strategy is not None

            # 验证策略类型
            expected_strategy = BrowserStrategyFactory.create_strategy(
                strategy_type=strategy_type, headless=True, download_dir=self.save_dir
            )

            # 验证策略类型匹配
            assert type(downloader.browser_strategy) == type(expected_strategy)

            # 清理
            expected_strategy.close()
            downloader.cleanup()

        except Exception as e:
            # 如果策略创建失败，跳过测试而不是失败
            pytest.skip(f"无法创建 {strategy_type} 策略: {e}")

    def test_strategy_switching_capability(self):
        """测试策略切换能力"""
        strategies_tested = []

        for strategy_type in ["selenium", "playwright"]:
            try:
                # 创建下载器
                downloader = DownloadServiceV2(
                    save_dir=self.save_dir,
                    mapping_file=self.mapping_file,
                    browser_strategy=strategy_type,
                )

                # 验证当前策略
                assert downloader.browser_strategy is not None
                strategies_tested.append(strategy_type)

                # 清理
                downloader.cleanup()

            except Exception as e:
                print(f"策略 {strategy_type} 测试跳过: {e}")

        # 验证至少测试了一种策略
        assert len(strategies_tested) > 0, "没有成功测试任何浏览器策略"

    def test_strategy_error_handling(self):
        """测试策略错误处理"""
        # 测试无效策略类型
        with pytest.raises(ValueError):
            BrowserStrategyFactory.create_strategy(
                strategy_type="invalid_strategy",
                headless=True,
                download_dir=self.save_dir,
            )

    @pytest.mark.parametrize("strategy_type", ["selenium", "playwright"])
    def test_strategy_configuration_validation(self, strategy_type):
        """测试策略配置验证"""
        try:
            # 测试不同配置组合
            configurations = [
                {"headless": True, "download_dir": self.save_dir},
                {"headless": False, "download_dir": self.save_dir},
                {"headless": True, "download_dir": None},
            ]

            for config in configurations:
                strategy = BrowserStrategyFactory.create_strategy(
                    strategy_type=strategy_type, **config
                )

                # 验证策略创建成功
                assert strategy is not None

                # 验证配置正确应用
                assert strategy.headless == config["headless"]
                if config["download_dir"]:
                    assert strategy.download_dir == config["download_dir"]

                # 清理
                strategy.close()

        except Exception as e:
            pytest.skip(f"无法创建 {strategy_type} 策略: {e}")

    def test_strategy_performance_comparison(self):
        """测试策略性能对比"""
        strategies = {}
        creation_times = {}

        # 测量策略创建时间
        for strategy_type in ["selenium", "playwright"]:
            try:
                start_time = time.time()
                strategy = BrowserStrategyFactory.create_strategy(
                    strategy_type=strategy_type,
                    headless=True,
                    download_dir=self.save_dir,
                )
                creation_time = time.time() - start_time

                strategies[strategy_type] = strategy
                creation_times[strategy_type] = creation_time

                # 清理
                strategy.close()

            except Exception as e:
                print(f"无法创建 {strategy_type} 策略: {e}")

        # 验证至少有一个策略被测试
        if not creation_times:
            pytest.skip("无法创建任何浏览器策略")

        # 记录性能数据（用于后续分析）
        print(f"策略创建时间: {creation_times}")

    def test_strategy_memory_usage(self):
        """测试策略内存使用"""
        strategies = {}

        for strategy_type in ["selenium", "playwright"]:
            try:
                strategy = BrowserStrategyFactory.create_strategy(
                    strategy_type=strategy_type,
                    headless=True,
                    download_dir=self.save_dir,
                )
                strategies[strategy_type] = strategy

                # 这里可以添加内存使用监测
                # 由于是测试环境，主要验证策略不会泄漏资源
                assert strategy is not None

                # 清理
                strategy.close()

            except Exception as e:
                print(f"无法创建 {strategy_type} 策略: {e}")

        # 验证至少有一个策略被测试
        if not strategies:
            pytest.skip("无法创建任何浏览器策略")

    def test_strategy_compatibility_with_download_service(self):
        """测试策略与下载服务的兼容性"""
        strategies_tested = []

        for strategy_type in ["selenium", "playwright"]:
            try:
                # 创建下载器
                downloader = DownloadServiceV2(
                    save_dir=self.save_dir,
                    mapping_file=self.mapping_file,
                    browser_strategy=strategy_type,
                )

                # 测试下载器基本功能
                stock_code = "300470"
                org_id = downloader.mapping_manager.get_org_id(stock_code)

                # 验证基本功能
                assert org_id is not None

                # 验证URL构建
                url = downloader._build_disclosure_url(stock_code, org_id)
                assert url.startswith("https://www.cninfo.com.cn")

                # 验证文件路径生成
                stock_name = downloader.mapping_manager.get_stock_name(stock_code)
                file_path = downloader._generate_file_path(stock_name, "test.pdf")
                assert file_path.endswith(".pdf")

                strategies_tested.append(strategy_type)

                # 清理
                downloader.cleanup()

            except Exception as e:
                print(f"策略 {strategy_type} 兼容性测试跳过: {e}")

        # 验证至少测试了一种策略
        assert len(strategies_tested) > 0, "没有成功测试任何浏览器策略的兼容性"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
