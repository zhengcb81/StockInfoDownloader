#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试下载功能修复 - 专门测试文件下载按钮点击机制
"""

import os
import sys
import time
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def log(message):
    """简单的日志输出"""
    timestamp = time.strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {message}")
    except UnicodeEncodeError:
        # 处理编码问题
        safe_message = message.encode('gbk', errors='ignore').decode('gbk')
        print(f"[{timestamp}] {safe_message}")

def test_download_button():
    """测试下载按钮点击功能"""
    log("开始测试下载按钮点击功能...")
    
    # 测试Selenium策略
    log("\n=== 测试Selenium策略 ===")
    try:
        from src.web.selenium_strategy import SeleniumStrategy
        
        # 创建Selenium策略实例
        selenium_strategy = SeleniumStrategy(
            headless=True,
            download_dir="end2end_test/test_results"
        )
        
        # 创建浏览器
        selenium_strategy.create_driver()
        log("Selenium浏览器创建成功")
        
        # 测试导航到详情页
        test_url = "https://www.cninfo.com.cn/new/disclosure/detail?plate=szse&orgId=9900056250&stockCode=301611&announcementId=1224316725&announcementTime=2025-07-28%2009:18"
        if selenium_strategy.navigate(test_url):
            log(f"成功导航到: {test_url}")
            
            # 获取页面标题
            title = selenium_strategy.get_page_title()
            log(f"页面标题: {title}")
            
            # 查找下载按钮
            download_button = selenium_strategy.find_element("//button[contains(., '公告下载')]", by="xpath")
            if download_button:
                log("✅ 找到下载按钮")
                
                # 获取按钮文本
                button_text = selenium_strategy.get_text(download_button)
                log(f"下载按钮文本: {button_text}")
                
                # 测试下载文件
                save_path = "end2end_test/test_results/珂玛科技/test_download_selenium.pdf"
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                success = selenium_strategy.download_file(test_url, save_path, timeout=30)
                if success:
                    log(f"✅ 文件下载成功: {save_path}")
                    # 检查文件大小
                    if os.path.exists(save_path):
                        file_size = os.path.getsize(save_path)
                        log(f"文件大小: {file_size} bytes")
                        if file_size > 10 * 1024:
                            log("✅ 文件大小正常")
                        else:
                            log("⚠️ 文件太小")
                    else:
                        log("❌ 文件不存在")
                else:
                    log("❌ 文件下载失败")
            else:
                log("❌ 未找到下载按钮")
                # 获取页面源代码帮助调试
                page_source = selenium_strategy.get_page_source()
                if page_source:
                    # 查找所有按钮元素
                    buttons = selenium_strategy.find_elements("button")
                    log(f"页面中找到 {len(buttons)} 个按钮")
                    for i, button in enumerate(buttons[:5]):  # 只显示前5个
                        try:
                            text = selenium_strategy.get_text(button)
                            log(f"按钮 {i+1}: {text}")
                        except:
                            log(f"按钮 {i+1}: [无法获取文本]")
        else:
            log("❌ 导航失败")
            
        selenium_strategy.close()
        
    except Exception as e:
        log(f"Selenium测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试Playwright策略
    log("\n=== 测试Playwright策略 ===")
    try:
        from src.web.playwright_strategy import PlaywrightStrategy
        
        # 创建Playwright策略实例
        playwright_strategy = PlaywrightStrategy(
            headless=True,
            download_dir="end2end_test/test_results"
        )
        
        # 创建浏览器
        playwright_strategy.create_driver()
        log("Playwright浏览器创建成功")
        
        # 测试导航到详情页
        test_url = "https://www.cninfo.com.cn/new/disclosure/detail?plate=szse&orgId=9900056250&stockCode=301611&announcementId=1224316725&announcementTime=2025-07-28%2009:18"
        if playwright_strategy.navigate(test_url):
            log(f"成功导航到: {test_url}")
            
            # 获取页面标题
            title = playwright_strategy.get_page_title()
            log(f"页面标题: {title}")
            
            # 查找下载按钮
            download_button = playwright_strategy.find_element("button:has-text('公告下载')")
            if download_button:
                log("✅ 找到下载按钮")
                
                # 获取按钮文本
                button_text = playwright_strategy.get_text(download_button)
                log(f"下载按钮文本: {button_text}")
                
                # 测试下载文件
                save_path = "end2end_test/test_results/珂玛科技/test_download_playwright.pdf"
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                success = playwright_strategy.download_file(test_url, save_path, timeout=30)
                if success:
                    log(f"✅ 文件下载成功: {save_path}")
                    # 检查文件大小
                    if os.path.exists(save_path):
                        file_size = os.path.getsize(save_path)
                        log(f"文件大小: {file_size} bytes")
                        if file_size > 10 * 1024:
                            log("✅ 文件大小正常")
                        else:
                            log("⚠️ 文件太小")
                    else:
                        log("❌ 文件不存在")
                else:
                    log("❌ 文件下载失败")
            else:
                log("❌ 未找到下载按钮")
                # 获取页面源代码帮助调试
                page_source = playwright_strategy.get_page_source()
                if page_source and '公告下载' in page_source:
                    log("✅ 页面源代码中包含'公告下载'文本")
                else:
                    log("❌ 页面源代码中未找到'公告下载'文本")
        else:
            log("❌ 导航失败")
            
        playwright_strategy.close()
        
    except Exception as e:
        log(f"Playwright测试异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_download_button()