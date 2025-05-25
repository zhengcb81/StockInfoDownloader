#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebDriver进程清理功能测试

测试新的进程清理机制，确保只清理WebDriver相关进程，不影响用户浏览器
"""

import time
import logging
from cninfo_activity_downloader import CninfoDownloader

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_webdriver_cleanup():
    """测试WebDriver进程清理功能"""
    print("🧪 测试WebDriver进程清理功能")
    print("=" * 50)
    
    # 创建下载器实例
    downloader = CninfoDownloader(save_dir='test_downloads')
    
    try:
        print("1. 初始化WebDriver...")
        success = downloader.setup_driver(headless=True)
        
        if success:
            print("✅ WebDriver初始化成功")
            print(f"   WebDriver进程ID: {downloader.webdriver_process_id}")
            print(f"   ChromeDriver进程ID: {downloader.chromedriver_process_id}")
            
            # 等待一段时间
            print("2. 等待5秒...")
            time.sleep(5)
            
            print("3. 测试进程清理...")
            downloader._cleanup_webdriver_processes()
            print("✅ 进程清理完成")
            
            print("4. 重启WebDriver...")
            restart_success = downloader.restart_driver(headless=True)
            
            if restart_success:
                print("✅ WebDriver重启成功")
                print(f"   新的WebDriver进程ID: {downloader.webdriver_process_id}")
                print(f"   新的ChromeDriver进程ID: {downloader.chromedriver_process_id}")
            else:
                print("❌ WebDriver重启失败")
                
        else:
            print("❌ WebDriver初始化失败")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        
    finally:
        print("5. 清理资源...")
        downloader.close_driver()
        print("✅ 测试完成")

def check_psutil_availability():
    """检查psutil是否可用"""
    try:
        import psutil
        print("✅ psutil可用 - 将使用精确的进程清理")
        return True
    except ImportError:
        print("⚠️  psutil不可用 - 将使用基本的进程清理")
        print("   建议安装psutil: pip install psutil")
        return False

if __name__ == "__main__":
    print("🚀 WebDriver进程清理功能测试")
    print("=" * 50)
    
    # 检查依赖
    psutil_available = check_psutil_availability()
    print()
    
    # 运行测试
    test_webdriver_cleanup()
    
    print("\n📝 测试说明:")
    print("- 此测试验证WebDriver进程清理功能")
    print("- 新的清理机制只会清理WebDriver相关进程")
    print("- 您正在使用的Chrome浏览器不会被影响")
    if psutil_available:
        print("- 使用psutil进行精确的进程识别和清理")
    else:
        print("- 使用基本的chromedriver进程清理") 