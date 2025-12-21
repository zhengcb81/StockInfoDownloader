#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Research Tab Pagination Diagnostic Tool
Specifically checks the research tab pagination structure for 300470
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.web.anti_crawler import AntiCrawlerStrategy


def setup_driver():
    """Setup Selenium WebDriver with test configuration"""
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Use the download directory from e2e config
    download_dir = str(project_root / "end2end_test" / "test_results")

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def analyze_research_tab(driver, url):
    """Analyze the research tab specifically"""
    print(f"导航到研究标签页: {url}")
    driver.get(url)

    # Apply anti-crawler measures
    anti_crawler = AntiCrawlerStrategy()
    anti_crawler.apply_anti_detection(driver)

    # Wait for page to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    import time
    time.sleep(3)

    current_url = driver.current_url
    print(f"当前URL: {current_url}")

    # Check if we're on the research tab
    if "#research" not in current_url:
        print("⚠️  Not on research tab, trying to switch...")
        try:
            # Try to click research tab
            research_tab = driver.find_element(By.XPATH, "//a[contains(text(), '调研')]")
            research_tab.click()
            time.sleep(3)
            current_url = driver.current_url
            print(f"After switch: {current_url}")
        except Exception as e:
            print(f"Failed to switch tab: {e}")

    # Get page source info
    page_source = driver.page_source
    print(f"页面源码长度: {len(page_source)}")

    # Check for pagination elements specifically
    print("\n=== 检查分页元素 ===")

    # Method 1: Check for Element UI pagination
    try:
        el_pagination = driver.find_elements(By.CSS_SELECTOR, ".el-pagination")
        print(f".el-pagination elements: {len(el_pagination)}")
        if el_pagination:
            for i, elem in enumerate(el_pagination[:3]):
                print(f"  {i+1}. classes: {elem.get_attribute('class')}, text: {elem.text[:100]}")
    except Exception as e:
        print(f"Error checking .el-pagination: {e}")

    # Method 2: Check for el-pager
    try:
        el_pager = driver.find_elements(By.CSS_SELECTOR, ".el-pager")
        print(f".el-pager elements: {len(el_pager)}")
        if el_pager:
            for i, elem in enumerate(el_pager[:3]):
                print(f"  {i+1}. classes: {elem.get_attribute('class')}, text: {elem.text[:100]}")
                # Get child elements
                children = elem.find_elements(By.TAG_NAME, "li")
                print(f"      Child li elements: {len(children)}")
                for j, child in enumerate(children[:5]):
                    print(f"        {j+1}. classes: {child.get_attribute('class')}, text: {child.text}, enabled: {child.is_enabled()}")
    except Exception as e:
        print(f"Error checking .el-pager: {e}")

    # Method 3: Check for next page buttons
    next_selectors = [
        "button.el-pagination__next",
        "button.el-pagination__next:not(.is-disabled)",
        ".el-pager li.number.active + li.number",
        "button.btn-next",
        "li.number.active + li.number"
    ]

    print(f"\n=== 检查下一页按钮候选 ===")
    for selector in next_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for elem in elements:
                    print(f"Selector: {selector}")
                    print(f"  Tag: {elem.tag_name}, Text: '{elem.text}', Enabled: {elem.is_enabled()}, Displayed: {elem.is_displayed()}")
                    print(f"  Classes: {elem.get_attribute('class')}")
                    print(f"  Location: {elem.location}, Size: {elem.size}")
        except Exception as e:
            pass

    # Method 4: Check all buttons for debugging
    print(f"\n=== 所有按钮元素 (前10个) ===")
    all_buttons = driver.find_elements(By.TAG_NAME, "button")
    for i, btn in enumerate(all_buttons[:10]):
        print(f"{i+1}. classes: {btn.get_attribute('class')}, text: '{btn.text}', enabled: {btn.is_enabled()}")

    # Method 5: Check all li elements for pagination
    print(f"\n=== 所有li元素 (前15个) ===")
    all_li = driver.find_elements(By.TAG_NAME, "li")
    for i, li in enumerate(all_li[:15]):
        classes = li.get_attribute('class')
        text = li.text
        if classes and 'number' in classes or 'active' in classes or 'pagination' in classes:
            print(f"{i+1}. classes: {classes}, text: '{text}', enabled: {li.is_enabled()}")

    # Method 6: Get current page info from URL
    print(f"\n=== 当前页面状态 ===")
    print(f"URL: {current_url}")
    print(f"Has #research: {'#research' in current_url}")
    print(f"Has stockCode=300470: {'300470' in current_url}")
    print(f"Has orgId=9900023856: {'9900023856' in current_url}")

    # Try to find any pagination container
    print(f"\n=== 查找分页容器 ===")
    pagination_containers = driver.find_elements(By.CSS_SELECTOR, ".pagination, .el-pagination, [class*='pagination']")
    print(f"Found {len(pagination_containers)} pagination-like containers")
    for i, container in enumerate(pagination_containers[:3]):
        print(f"Container {i+1}:")
        print(f"  Tag: {container.tag_name}")
        print(f"  Classes: {container.get_attribute('class')}")
        print(f"  Text: {container.text[:200]}")

    # Check if there are any clickable elements that look like pagination
    print(f"\n=== 可点击的分页相关元素 ===")
    clickable_selectors = [
        "li.number",
        "li[aria-label*='page']",
        "button[aria-label*='page']",
        ".btn-next",
        ".btn-prev"
    ]

    for selector in clickable_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"Selector '{selector}': {len(elements)} elements")
                for elem in elements[:3]:
                    print(f"  Text: '{elem.text}', Enabled: {elem.is_enabled()}, Displayed: {elem.is_displayed()}")
        except Exception:
            pass

    return {
        "url": current_url,
        "page_length": len(page_source),
        "has_research": "#research" in current_url
    }


def main():
    """Main diagnostic function"""
    print("=== 研究标签页分页结构专项诊断 ===")
    print("针对 300470 的研究标签页进行详细分析")
    print()

    driver = None
    try:
        driver = setup_driver()
        print("[OK] WebDriver 启动成功")
        print()

        # Test the exact URL from failing test case 3
        test_url = "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=300470&orgId=9900023856#research"

        result = analyze_research_tab(driver, test_url)

        print(f"\n{'='*60}")
        print("诊断总结")
        print(f"{'='*60}")
        print(f"URL: {result['url']}")
        print(f"页面长度: {result['page_length']}")
        print(f"在研究标签页: {result['has_research']}")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.quit()
            print("\n✅ WebDriver 已关闭")


if __name__ == "__main__":
    main()