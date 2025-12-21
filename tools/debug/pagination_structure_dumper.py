#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pagination Structure Diagnostic Tool
Captures the actual HTML structure of pagination elements on cninfo.com.cn
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


def capture_pagination_html(driver, url):
    """Navigate to URL and capture pagination HTML structure"""
    print(f"导航到: {url}")
    driver.get(url)

    # Apply anti-crawler measures
    anti_crawler = AntiCrawlerStrategy()
    anti_crawler.apply_anti_detection(driver)

    # Wait for page to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # Give AJAX time to complete (for dynamic pagination)
    import time
    time.sleep(3)

    current_url = driver.current_url
    print(f"当前URL: {current_url}")

    # Capture detailed HTML structure
    results = {
        "timestamp": datetime.now().isoformat(),
        "url": url,
        "current_url": current_url,
        "page_source_length": len(driver.page_source),
        "pagination_info": {}
    }

    # Method 1: Look for common pagination patterns
    pagination_selectors = [
        # Element UI patterns
        "button.el-pagination__next",
        "button.el-pagination__prev",
        ".el-pagination",
        ".el-pager",

        # Bootstrap/common patterns
        ".pagination",
        "[aria-label='Next page']",
        "[aria-label='下一页']",
        ".next",
        ".page-link",

        # Custom patterns
        "a[href*='page']",
        "button[href*='page']",

        # Chinese specific
        "button:contains('下一页')",
        "a:contains('下一页')",
        "li:contains('下一页')",

        # All buttons/links for manual inspection
        "button",
        "a"
    ]

    results["pagination_info"]["found_elements"] = []

    for selector in pagination_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector.replace(":contains('下一页')", ""))
            if selector == "button" or selector == "a":
                # Limit to first 20 for these broad selectors
                elements = elements[:20]

            if elements:
                for elem in elements:
                    try:
                        elem_data = {
                            "selector": selector,
                            "tag": elem.tag_name,
                            "text": elem.text.strip()[:100],
                            "enabled": elem.is_enabled(),
                            "classes": elem.get_attribute("class"),
                            "id": elem.get_attribute("id"),
                            "href": elem.get_attribute("href"),
                            "onclick": elem.get_attribute("onclick"),
                            "aria_label": elem.get_attribute("aria-label")
                        }
                        results["pagination_info"]["found_elements"].append(elem_data)
                    except Exception as e:
                        continue
        except Exception:
            continue

    # Look for specific next page button patterns
    next_page_selectors = [
        "button.el-pagination__next:not(.is-disabled)",
        ".pagination .next:not(.disabled)",
        "a[aria-label='下一页']:not(.disabled)",
        ".el-pager li.number.active + li.number",
        "button[aria-label='Next page']:not([disabled])",
        "//button[contains(text(), '下一页')]",
        "//a[contains(text(), '下一页')]"
    ]

    results["pagination_info"]["next_page_candidates"] = []

    for selector in next_page_selectors:
        try:
            if selector.startswith("//"):
                # XPath
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)

            if elements:
                for elem in elements:
                    try:
                        candidate = {
                            "selector": selector,
                            "tag": elem.tag_name,
                            "text": elem.text.strip()[:100],
                            "enabled": elem.is_enabled(),
                            "is_displayed": elem.is_displayed(),
                            "location": elem.location,
                            "size": elem.size,
                            "classes": elem.get_attribute("class"),
                            "id": elem.get_attribute("id")
                        }
                        results["pagination_info"]["next_page_candidates"].append(candidate)
                    except Exception:
                        continue
        except Exception:
            continue

    # Capture current page info
    results["current_page_info"] = {
        "url_hash": current_url.split("#")[1] if "#" in current_url else None,
        "has_301611": "301611" in current_url,
        "has_300470": "300470" in current_url,
        "has_research": "research" in current_url,
        "has_periodic": "periodicReports" in current_url
    }

    return results


def main():
    """Main diagnostic function"""
    print("=== 网页分页结构诊断工具 ===")
    print("此工具将捕获 cninfo.com.cn 的实际HTML分页结构")
    print()

    driver = None
    try:
        driver = setup_driver()
        print("[OK] WebDriver 启动成功")
        print()

        # Test case 3 scenario - research tab for 300470 (must use corporation ID 9900023856)
        test_urls = [
            # Test scenario from failed test case 3
            "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=300470&orgId=9900023856#research",
        ]

        all_results = []

        for url in test_urls:
            print(f"\n{'='*80}")
            print(f"测试URL: {url}")
            print(f"{'='*80}")

            result = capture_pagination_html(driver, url)
            all_results.append(result)

            # Print summary
            pagination_info = result["pagination_info"]
            found_count = len(pagination_info["found_elements"])
            candidates_count = len(pagination_info["next_page_candidates"])

            print(f"\n[STATS] 统计结果:")
            print(f"  - 找到 {found_count} 个可能的分页元素")
            print(f"  - 找到 {candidates_count} 个下一页按钮候选")

            if candidates_count > 0:
                print(f"\n[NEXT] 下一页按钮候选:")
                for i, candidate in enumerate(pagination_info["next_page_candidates"][:5], 1):
                    print(f"  {i}. {candidate['selector']}")
                    print(f"     文本: '{candidate['text']}'")
                    print(f"     类名: {candidate['classes']}")
                    print(f"     启用: {candidate['enabled']}")
                    print(f"     可见: {candidate['is_displayed']}")
                    print()
            else:
                print(f"\n[EMPTY] 未找到下一页按钮候选")

            if found_count > 0:
                print(f"\n[FIND] 找到的分页元素样本 (前5个):")
                for i, elem in enumerate(pagination_info["found_elements"][:5], 1):
                    print(f"  {i}. [{elem['selector']}] {elem['tag']} - '{elem['text'][:50]}'")
                    if elem['classes']:
                        print(f"     classes: {elem['classes']}")

        # Save detailed results
        output_file = project_root / "tools" / "debug" / "pagination_diagnostic_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 详细结果已保存到: {output_file}")

        # Generate recommendations
        print(f"\n{'='*80}")
        print("📋 诊断建议")
        print(f"{'='*80}")

        candidates = all_results[0]["pagination_info"]["next_page_candidates"]
        if candidates:
            print("建议使用以下CSS选择器修复 selenium_strategy.py:")
            print()

            # Find unique, working selectors
            unique_selectors = []
            for c in candidates:
                if c["enabled"] and c["is_displayed"]:
                    unique_selectors.append(c["selector"])

            if unique_selectors:
                print("推荐的下一页选择器 (已验证可用):")
                for selector in unique_selectors[:3]:
                    print(f'  "{selector}",')
            else:
                print("⚠️  候选元素存在但可能不可点击，需要进一步排查")
        else:
            print("❌ 未发现可用的下一页按钮")
            print("建议:")
            print("1. 检查网站是否使用JavaScript动态加载分页")
            print("2. 尝试使用XPath选择器")
            print("3. 检查页面是否有反爬虫机制")

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