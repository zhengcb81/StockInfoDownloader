# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**StockInfoDownloader** is a comprehensive Python-based web scraper for downloading financial documents from 巨潮资讯网 (cninfo.com.cn). It supports:
- **投资者关系活动记录表** (Investor Relations Activity Records)
- **财务报告** (Financial Reports): 年度报告、半年度报告、季度报告

Features advanced anti-bot detection mechanisms, robust error handling, and unified interface for both document types.

## Architecture

### Core Components

#### 投资者关系下载器
- **`cninfo_activity_downloader.py`** - Main downloader for investor relations activity records with Selenium WebDriver, anti-detection features, and PDF download automation

#### 财务报告下载器
- **`cninfo_financial_real_downloader.py`** - Dedicated financial report downloader (年报、半年报、季报) using proven architecture from investor relations downloader
- **`cninfo_financial_downloader.py`** - Alternative financial report downloader with enum-based report type classification

#### 通用工具
- **`orgid_utils.py`** - Stock code to organization ID mapping utility with caching and fallback mechanisms
- **`orgid_crawler.py`** - Web crawler to retrieve org IDs from stock codes when not in cache
- **`get_stock_name.py`** - Utility to resolve stock codes to company names
- **`unified_downloader.py`** - Unified interface supporting both investor relations and financial reports
- **`get_hikvision_reports.py`** - Simplified direct downloader for Hikvision financial reports

### Anti-Bot Features
- Random User-Agent rotation
- Human behavior simulation (mouse movement, scrolling)
- Random delays between actions (3-8 seconds)
- Session management with automatic restarts
- Precise WebDriver process cleanup (won't affect user's Chrome)
- Smart retry mechanisms with environment reinitialization

### Data Flow

#### 投资者关系下载流程
1. Stock code → orgid_utils → org ID (cached or crawled)
2. org ID → cninfo_activity_downloader → PDF downloads
3. Downloads saved to organized directory structure by company name

#### 财务报告下载流程
1. Stock code → orgid_utils → org ID (cached or crawled)
2. org ID → cninfo_financial_real_downloader → Financial reports
3. Report type filtering (annual/semi-annual/quarterly)
4. Year-based filtering (2020-2024)
5. Downloads saved to organized directory structure with report classification

## Common Commands

### Setup & Dependencies
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt  # For testing
```

### Running the Application

#### 1. 投资者关系活动记录表下载
```bash
# Download investor relations records for configured stock
python cninfo_activity_downloader.py

# Download specific stock
python cninfo_activity_downloader.py --stock-code 002415 --headless
```

#### 2. 财务报告下载 (新增)
```bash
# Download financial reports for Hikvision (海康威视)
python cninfo_financial_real_downloader.py

# Download specific financial reports
python cninfo_financial_real_downloader.py --stock-code 002415 --report-types annual semi_annual --years 2023 2024 --max-reports 50

# Use unified downloader for financial reports
python unified_downloader.py --stock-code 002415 --type financial --report-types all --years 2020 2021 2022 2023 2024 --max-reports 100
```

#### 3. 统一下载器 (支持两种类型)
```bash
# Interactive mode
python unified_downloader.py --interactive

# Command line mode
python unified_downloader.py --stock-code 002415 --type investor_relations --headless
python unified_downloader.py --stock-code 002415 --type financial --report-types annual semi_annual --years 2023 2024
```

#### 4. 专用下载器
```bash
# Hikvision specific downloader
python get_hikvision_reports.py

# Test anti-bot mechanisms
python test_anti_crawler.py

# Crawl org IDs for stock codes
python orgid_crawler.py --test --stock-code 300010
python orgid_crawler.py --start 0 --end 100 --headless

# Get stock name
python get_stock_name.py
```

### Testing
```bash
# Run all tests
python tests/run_tests.py

# Run specific test types
python tests/run_tests.py unit
python tests/run_tests.py integration
python tests/run_tests.py performance

# Run specific test case
python tests/run_tests.py --specific tests.test_orgid_utils.TestOrgidUtils.test_is_valid_stock_code

# Check test dependencies
python tests/run_tests.py --check-deps

# Code quality check
python code_quality_check.py .
```

### Configuration

#### 投资者关系配置
Edit `config.json`:
```json
{
  "stock_code": "002415",
  "save_dir": "downloads",
  "headless": true
}
```

#### 财务报告配置
Extended configuration supports financial report settings:
```json
{
  "stock_code": "002415",
  "save_dir": "downloads",
  "headless": true,
  "download_type": "financial",
  "report_types": ["annual", "semi_annual", "q1", "q3"],
  "years": [2023, 2024],
  "max_reports": 50,
  "overwrite_existing": false
}
```

## File Structure

```
StockInfoDownloader/
├── cninfo_activity_downloader.py      # 投资者关系活动记录表下载器
├── cninfo_financial_real_downloader.py # 财务报告实际下载器
├── cninfo_financial_downloader.py      # 财务报告下载器（枚举版本）
├── unified_downloader.py              # 统一下载器（支持两种类型）
├── get_hikvision_reports.py           # 海康威视专用下载器
├── get_hikvision_reports.py           # 海康威视简化下载器
├── orgid_utils.py                     # 股票代码映射工具
├── orgid_crawler.py                   # 组织ID爬虫
├── get_stock_name.py                  # 股票名称解析器
├── config.json                        # 运行时配置
├── stock_orgid_mapping.json           # 组织ID映射缓存
├── a_stock_codes.csv                  # 股票代码数据库
├── code_quality_check.py              # 代码质量检查器
├── tests/                             # 综合测试套件
│   ├── run_tests.py                   # 测试运行器
│   └── test_*.py                      # 测试模块
├── downloads/                         # PDF输出目录
│   ├── 海康威视/                      # 投资者关系文件
│   └── 海康威视_财务报告/             # 财务报告文件
└── logs/                             # 应用程序日志
```

## Key Patterns

### Error Handling
- Comprehensive try-catch blocks with specific exception types
- Logging via Python's logging module to both console and files
- Graceful degradation when optional dependencies (psutil) unavailable
- **新增**: Financial report type validation and year filtering

### Caching Strategy
- `stock_orgid_mapping.json` for persistent org ID storage
- In-memory caching for stock name lookups
- Force refresh capability via `force_run=True` parameter
- **新增**: Report type caching for faster subsequent runs

### WebDriver Management
- Automatic ChromeDriver version detection via undetected-chromedriver
- Process tracking for precise cleanup
- Session rotation to avoid detection
- **新增**: Financial report specific element detection and handling

### Report Classification
- **Annual Reports** (年度报告): Full year financial statements
- **Semi-Annual Reports** (半年度报告): Mid-year financial updates
- **Quarterly Reports** (季度报告): Q1/Q3 quarterly updates
- **English/Chinese Versions**: Supports both language variants
- **Summary Reports**: Extracts key financial highlights

## Environment Requirements

- **Python**: 3.6+
- **Chrome**: Latest stable version
- **OS**: Windows/Linux/macOS (Windows primarily tested)
- **Network**: Stable internet for cninfo.com.cn access

## Testing Framework

Uses Python's built-in unittest with custom test runner (`tests/run_tests.py`):
- **Unit tests**: Isolated component testing
- **Integration tests**: Real web scraping scenarios
- **Performance tests**: Memory leak detection, concurrency testing
- **Mock tests**: Simulated web responses for reliability