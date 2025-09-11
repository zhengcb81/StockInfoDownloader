#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
严格验证翻页内容真实性
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.logger import get_logger
from src.web.driver import WebDriverManager
from src.web.scraper import WebScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = get_logger(__name__)

def validate_page_content_authenticity():
    """严格验证翻页内容真实性"""
    logger.info("开始严格验证翻页内容真实性...")
    
    # 使用可见模式以便观察
    driver_manager = WebDriverManager(
        headless=False,
        download_dir="validate_page_content",
        page_load_timeout=30,
        implicit_wait=10
    )
    
    try:
        with driver_manager as driver:
            # 测试股票代码 300470 (中密控股)
            stock_code = "300470"
            org_id = "9900023856"
            
            # 构建调研页面URL
            base_url = "https://www.cninfo.com.cn"
            url = f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
            
            logger.info(f"访问页面: {url}")
            
            # 访问页面
            driver.get(url)
            time.sleep(10)  # 更长等待时间确保完全加载
            
            # 创建网页抓取器
            scraper = WebScraper(driver)
            
            # 存储每页的详细内容
            page_contents = {}
            target_document_found = False
            target_document_page = None
            
            # 搜索前3页
            for page_num in range(1, 4):
                logger.info(f"\n{'='*60}")
                logger.info(f"=== 详细分析第{page_num}页 ===")
                logger.info(f"{'='*60}")
                
                if page_num > 1:
                    # 导航到指定页
                    logger.info(f"正在导航到第{page_num}页...")
                    success = scraper.go_to_page(page_num, timeout=15)
                    if not success:
                        logger.error(f"❌ 无法跳转到第{page_num}页")
                        break
                    
                    # 等待页面加载 - 更长时间
                    logger.info("等待页面完全加载...")
                    time.sleep(5)
                
                # 获取页面基本信息
                page_info = scraper.get_current_page_info()
                logger.info(f"页面信息: {page_info}")
                
                # 获取当前页面URL
                current_url = driver.current_url
                logger.info(f"当前URL: {current_url}")
                
                # 详细获取文档列表
                documents = get_detailed_documents(driver, page_num)
                page_contents[page_num] = documents
                
                logger.info(f"第{page_num}页找到 {len(documents)} 个文档")
                
                if documents:
                    # 显示前10个文档的详细信息
                    logger.info(f"\n--- 第{page_num}页前10个文档详细信息 ---")
                    for i, doc in enumerate(documents[:10]):
                        logger.info(f"{i+1}. {doc['title']}")
                        logger.info(f"   日期: {doc['date']}")
                        logger.info(f"   完整文本: {doc['full_text'][:100]}...")
                        
                        # 检查是否为目标文档
                        target_keywords = ["2023年1月31日", "投资者关系活动记录表"]
                        if all(keyword in doc['full_text'] for keyword in target_keywords):
                            logger.info(f"   ✅ 找到目标文档！")
                            target_document_found = True
                            target_document_page = page_num
                
                # 检查页面是否真正加载
                check_page_authenticity(driver, page_num, documents)
                
                # 如果找到目标文档，记录详细信息
                if target_document_found and target_document_page == page_num:
                    logger.info(f"\n🎯 目标文档在第{page_num}页找到！")
                    break
            
            # 比较不同页面的内容
            logger.info(f"\n{'='*60}")
            logger.info("=== 跨页面内容对比分析 ===")
            logger.info(f"{'='*60}")
            
            compare_page_contents(page_contents)
            
            # 总结
            logger.info(f"\n{'='*60}")
            logger.info("=== 验证结果总结 ===")
            logger.info(f"{'='*60}")
            
            if target_document_found:
                logger.info(f"✅ 目标文档已在第{target_document_page}页找到")
                logger.info("✅ 翻页功能正常工作")
                return True, target_document_page
            else:
                logger.info("❌ 在前3页未找到目标文档")
                logger.info("需要继续搜索更多页面或调整搜索策略")
                return False, None
                
    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    
    finally:
        logger.info("页面内容真实性验证完成")

def get_detailed_documents(driver, page_num):
    """获取详细的文档信息"""
    try:
        documents = []
        
        # 查找表格行 - 使用更具体的选择器
        table_selectors = [
            ".el-table__row",
            ".table-row", 
            "tr[data-row-key]",
            "tbody tr",
            ".el-table tbody tr"
        ]
        
        table_rows = []
        for selector in table_selectors:
            try:
                rows = driver.find_elements(By.CSS_SELECTOR, selector)
                if rows:
                    table_rows = rows
                    logger.info(f"使用选择器 '{selector}' 找到 {len(rows)} 行")
                    break
            except:
                continue
        
        if not table_rows:
            logger.warning("未找到表格行")
            return documents
        
        # 解析每一行
        for i, row in enumerate(table_rows):
            try:
                # 获取行内所有文本
                cells = row.find_elements(By.CSS_SELECTOR, "td, .el-table__cell")
                
                doc_info = {
                    'page': page_num,
                    'row_index': i + 1,
                    'cells_count': len(cells),
                    'full_text': row.text.strip(),
                    'title': '',
                    'date': ''
                }
                
                # 尝试提取标题和日期
                if len(cells) >= 2:
                    # 通常第一列是标题，第二列是日期
                    title_cell = cells[0].text.strip()
                    date_cell = cells[1].text.strip() if len(cells) > 1 else ''
                    
                    doc_info['title'] = title_cell
                    doc_info['date'] = date_cell
                else:
                    # 如果没有表格结构，使用整行文本
                    doc_info['title'] = doc_info['full_text'][:100]
                
                documents.append(doc_info)
                
            except Exception as e:
                logger.debug(f"解析第{i+1}行失败: {e}")
                continue
        
        return documents
        
    except Exception as e:
        logger.error(f"获取详细文档失败: {e}")
        return []

def check_page_authenticity(driver, page_num, documents):
    """检查页面真实性"""
    logger.info(f"\n--- 第{page_num}页真实性检查 ---")
    
    # 检查1: 文档数量是否合理
    if len(documents) == 0:
        logger.warning(f"⚠️ 第{page_num}页没有找到任何文档")
        return False
    elif len(documents) > 50:
        logger.warning(f"⚠️ 第{page_num}页文档数量异常: {len(documents)}")
        return False
    
    # 检查2: 文档内容是否有意义
    meaningful_docs = 0
    for doc in documents[:10]:  # 检查前10个
            if len(doc['full_text']) > 20 and '投资者' in doc['full_text'] or '关系' in doc['full_text']:
                meaningful_docs += 1
    
    if meaningful_docs < 5:
        logger.warning(f"⚠️ 第{page_num}页有意义文档数量较少: {meaningful_docs}/10")
        return False
    
    # 检查3: 日期分布是否合理
    dates = []
    for doc in documents[:10]:
        if doc['date']:
            dates.append(doc['date'])
    
    if dates:
        logger.info(f"第{page_num}页日期样本: {dates[:5]}")
    
    logger.info(f"✅ 第{page_num}页真实性检查通过")
    return True

def compare_page_contents(page_contents):
    """比较不同页面的内容"""
    if len(page_contents) < 2:
        logger.info("不足2页，无法比较")
        return
    
    logger.info("进行跨页面内容对比...")
    
    # 比较第1页和第2页
    if 1 in page_contents and 2 in page_contents:
        page1_docs = [doc['full_text'] for doc in page_contents[1][:10]]
        page2_docs = [doc['full_text'] for doc in page_contents[2][:10]]
        
        if page1_docs == page2_docs:
            logger.error("❌ 第1页和第2页内容完全相同！翻页可能失败")
            logger.info("第1页前3个文档:")
            for i, doc in enumerate(page1_docs[:3]):
                logger.info(f"  {i+1}. {doc[:80]}...")
            logger.info("第2页前3个文档:")
            for i, doc in enumerate(page2_docs[:3]):
                logger.info(f"  {i+1}. {doc[:80]}...")
        else:
            logger.info("✅ 第1页和第2页内容不同，翻页成功")
            
            # 显示差异
            unique_to_page1 = set(page1_docs) - set(page2_docs)
            unique_to_page2 = set(page2_docs) - set(page1_docs)
            
            logger.info(f"第1页独有文档: {len(unique_to_page1)} 个")
            logger.info(f"第2页独有文档: {len(unique_to_page2)} 个")
    
    # 比较第2页和第3页
    if 2 in page_contents and 3 in page_contents:
        page2_docs = [doc['full_text'] for doc in page_contents[2][:10]]
        page3_docs = [doc['full_text'] for doc in page_contents[3][:10]]
        
        if page2_docs == page3_docs:
            logger.error("❌ 第2页和第3页内容完全相同！翻页可能失败")
        else:
            logger.info("✅ 第2页和第3页内容不同，翻页成功")

if __name__ == "__main__":
    success, target_page = validate_page_content_authenticity()
    if success:
        logger.info(f"✅ 验证成功! 目标文档在第{target_page}页")
    else:
        logger.info("❌ 验证失败! 需要进一步调查")
    
    if target_page:
        sys.exit(0)
    else:
        sys.exit(1)