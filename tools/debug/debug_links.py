#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug script to investigate link finding issues on cninfo.com
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.web.selenium_strategy import SeleniumStrategy
from src.core.config import ConfigManager

def debug_link_finding():
    """Debug link finding on actual website"""
    
    config = ConfigManager()
    browser_config = {
        'window_size': config.get('webdriver.window_size', '1920,1080'),
        'page_load_timeout': config.get('timeout.page_load', 15),
        'implicit_wait': config.get('timeout.element_wait', 3),
        'max_downloads_per_session': config.get('download.max_downloads_per_session', 10),
        'user_agents': config.get('webdriver.user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
    }
    
    strategy = SeleniumStrategy(headless=False, download_dir='debug_downloads', config=browser_config)
    
    try:
        driver = strategy.create_driver()
        
        # Test URL for 301611 stock
        test_url = "https://www.cninfo.com.cn/new/disclosure/stock?orgId=9900001611&stockCode=301611#research"
        
        print(f"Navigating to: {test_url}")
        if not strategy.navigate(test_url):
            print("Navigation failed")
            return
        
        # Wait for page to load
        time.sleep(10)
        
        # Get page title
        title = strategy.get_page_title()
        print(f"Page title: {title}")
        
        # Get current URL
        current_url = strategy.get_current_url()
        print(f"Current URL: {current_url}")
        
        # Get page source for debugging
        page_source = strategy.get_page_source()
        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("Page source saved to debug_page_source.html")
        
        # Find all links
        links = strategy.find_elements("a")
        print(f"Found {len(links)} total links")
        
        # Analyze links
        detail_links = []
        for i, link in enumerate(links):
            try:
                text = strategy.get_text(link)
                href = strategy.get_attribute(link, "href")
                
                if href and '/new/disclosure/detail' in href:
                    detail_links.append((text, href))
                    print(f"Detail link {len(detail_links)}: {text} -> {href}")
                
                # Print first few links for analysis
                if i < 10:
                    print(f"Link {i}: text='{text}', href='{href}'")
                    
            except Exception as e:
                print(f"Error processing link {i}: {e}")
        
        print(f"\nFound {len(detail_links)} detail page links")
        
        # Check if stock code is in URL
        stock_code_in_url = []
        for text, href in detail_links:
            if 'stockCode=301611' in href:
                stock_code_in_url.append((text, href))
        
        print(f"Found {len(stock_code_in_url)} links with stock code 301611")
        for text, href in stock_code_in_url:
            print(f"  - {text}: {href}")
        
        # Keep browser open for manual inspection
        input("Press Enter to close browser...")
        
    except Exception as e:
        print(f"Error during debugging: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        strategy.close()

if __name__ == "__main__":
    debug_link_finding()