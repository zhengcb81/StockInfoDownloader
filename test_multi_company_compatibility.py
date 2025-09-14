#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试多公司配置和并行下载功能
验证新架构的配置兼容性
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import ConfigManager
from main_parallel import MultiCompanyDownloader, CompanyConfig

def test_multi_company_config():
    """测试多公司配置"""
    print("=== 测试多公司配置 ===")

    # 测试配置文件加载
    config_manager = ConfigManager("config.json")
    config = config_manager.load_config()

    # 验证多公司配置结构
    if 'companies' not in config:
        print("❌ 错误：缺少companies配置")
        return False

    companies = config['companies']
    print(f"✅ 找到 {len(companies)} 个公司配置")

    # 验证每个公司配置
    enabled_companies = []
    for company in companies:
        if company.get('enabled', True):
            enabled_companies.append(company)
            print(f"✅ 启用公司: {company['stock_code']} - {company['company_name']}")

    print(f"✅ 总共启用 {len(enabled_companies)} 个公司")

    # 验证并行下载配置
    parallel_config = config.get('parallel_download', {})
    if parallel_config.get('enabled', False):
        print("✅ 并行下载已启用")
        print(f"   最大工作线程: {parallel_config.get('max_workers', 1)}")
        print(f"   任务超时时间: {parallel_config.get('task_timeout', 300)}秒")
    else:
        print("❌ 并行下载未启用")

    return True

def test_multi_company_downloader():
    """测试多公司下载器"""
    print("\n=== 测试多公司下载器 ===")

    try:
        # 加载配置文件
        config_manager = ConfigManager("config.json")
        config = config_manager.load_config()

        # 创建多公司下载器实例
        downloader = MultiCompanyDownloader(config, "config.json")

        # 获取公司配置
        company_configs = downloader.get_company_configs()
        print(f"✅ 成功获取 {len(company_configs)} 个公司配置")

        # 验证配置结构
        for config in company_configs:
            if isinstance(config, CompanyConfig):
                print(f"✅ 公司配置: {config.stock_code} - {config.company_name}")
                print(f"   优先级: {config.priority}")
                print(f"   自定义页面: {config.custom_pages}")
            else:
                print(f"❌ 配置格式错误: {config}")

        return True

    except Exception as e:
        print(f"❌ 创建多公司下载器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_compatibility():
    """测试配置兼容性"""
    print("\n=== 测试配置兼容性 ===")

    config_manager = ConfigManager("config.json")
    config = config_manager.load_config()

    # 验证必需的配置项
    required_keys = [
        'browser.strategy',
        'download.max_downloads_per_session',
        'timeout.page_load',
        'pages'
    ]

    missing_keys = []
    for key in required_keys:
        keys = key.split('.')
        current = config
        try:
            for k in keys:
                current = current[k]
        except (KeyError, TypeError):
            missing_keys.append(key)

    if missing_keys:
        print(f"❌ 缺少配置项: {missing_keys}")
        return False

    print("✅ 所有必需配置项都存在")

    # 验证页面配置
    pages = config.get('pages', [])
    print(f"✅ 找到 {len(pages)} 个页面配置")

    for page in pages:
        suffix = page.get('suffix', 'unknown')
        allowed = page.get('allowed_keywords', [])
        excluded = page.get('excluded_keywords', [])
        max_pages = page.get('max_pages', 1)
        print(f"   {suffix}: 允许关键词{len(allowed) if allowed else '无'}, 排除关键词{len(excluded) if excluded else '无'}, 最大页数{max_pages}")

    return True

def test_browser_strategy_compatibility():
    """测试浏览器策略兼容性"""
    print("\n=== 测试浏览器策略兼容性 ===")

    from src.web.browser_strategy_manager import BrowserStrategyManager
    from src.services.downloader_v2 import DownloadServiceV2

    try:
        # 测试浏览器策略管理器
        manager = BrowserStrategyManager("config.json")
        strategy = manager.get_strategy()
        print(f"✅ 浏览器策略管理器创建成功: {manager.get_current_type()}")

        # 测试下载器与策略的集成
        downloader = DownloadServiceV2(
            save_dir="test_downloads",
            mapping_file="stock_orgid_mapping.json",
            browser_strategy=manager.get_current_type().value
        )
        print(f"✅ 下载器创建成功，使用策略: {downloader.browser_strategy_type}")

        # 测试策略切换
        new_strategy = manager.switch_strategy("selenium")
        print(f"✅ 策略切换成功: {manager.get_current_type()}")

        return True

    except Exception as e:
        print(f"❌ 浏览器策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试多公司配置和兼容性...")

    tests = [
        ("多公司配置", test_multi_company_config),
        ("多公司下载器", test_multi_company_downloader),
        ("配置兼容性", test_configuration_compatibility),
        ("浏览器策略兼容性", test_browser_strategy_compatibility),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"运行测试: {test_name}")
        print('='*50)

        try:
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"测试结果: {passed}/{total} 通过")
    print('='*50)

    if passed == total:
        print("🎉 所有测试通过！重构后的下载器配置兼容性良好。")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败，请检查配置和实现。")
        sys.exit(1)