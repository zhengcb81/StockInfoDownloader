#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
组织ID工具模块

提供股票代码与组织ID的映射功能
"""

import os
import json
import time
from typing import Optional
from get_stock_name import get_stock_name

def get_org_id_by_code(stock_code: str, force_run: bool = False, mapping_file: str = 'stock_orgid_mapping.json', headless: bool = True) -> Optional[str]:
    """
    通用API：根据证券代码获取org id。
    
    参数：
        stock_code (str): 证券代码
        force_run (bool): 是否强制重新爬取org id，默认False
        mapping_file (str): 映射表文件路径，默认'stock_orgid_mapping.json'
        headless (bool): 是否无头模式，默认True
        
    返回：
        org_id (str): 组织ID字符串，获取失败返回None
    """
    # 加载现有映射
    mapping = _load_mapping(mapping_file)
    
    # 如果不强制运行且已有映射，直接返回
    if not force_run and stock_code in mapping and 'orgId' in mapping[stock_code]:
        return mapping[stock_code]['orgId']
    
    # 尝试从预设映射中获取
    org_id = _get_from_preset_mapping(stock_code)
    if org_id:
        _save_to_mapping(stock_code, org_id, mapping, mapping_file)
        return org_id
    
    # 使用爬虫获取
    org_id = _crawl_org_id(stock_code, mapping_file, headless)
    if org_id:
        _save_to_mapping(stock_code, org_id, mapping, mapping_file)
        return org_id
    
    return None

def _load_mapping(mapping_file: str) -> dict:
    """加载映射文件"""
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _get_from_preset_mapping(stock_code: str) -> Optional[str]:
    """从预设映射表获取组织ID"""
    preset_mapping = {
        "000001": "9900000001",  # 平安银行
        "000002": "9900000002",  # 万科A
        "000063": "9900000063",  # 中兴通讯
        "000333": "9900000333",  # 美的集团
        "000651": "9900000651",  # 格力电器
        "000858": "9900000858",  # 五粮液
        "002714": "9900008369",  # 牧原股份
        "300010": "9900008267",  # 豆神教育
        "300059": "9900008316",  # 东方财富
        "300750": "9900009007",  # 宁德时代
        "600000": "9900010000",  # 浦发银行
        "600009": "9900010009",  # 上海机场
        "600016": "9900010016",  # 民生银行
        "600036": "9900010036",  # 招商银行
        "600276": "9900010276",  # 恒瑞医药
        "600519": "9900010519",  # 贵州茅台
        "600887": "9900010887",  # 伊利股份
        "601318": "9900011318",  # 中国平安
        "601398": "9900011398",  # 工商银行
        "603288": "9900013288"   # 海天味业
    }
    return preset_mapping.get(stock_code)

def _crawl_org_id(stock_code: str, mapping_file: str, headless: bool) -> Optional[str]:
    """使用爬虫获取组织ID"""
    try:
        from orgid_crawler import OrgIdCrawler
        crawler = OrgIdCrawler(output_file=mapping_file, headless=headless)
        org_id = crawler.get_org_id(stock_code)
        crawler.close_driver()
        return org_id
    except Exception:
        return None

def _save_to_mapping(stock_code: str, org_id: str, mapping: dict, mapping_file: str):
    """保存到映射文件"""
    try:
        name = get_stock_name(stock_code, mapping_file)
        mapping[stock_code] = {
            'orgId': org_id,
            'name': name,
            'timestamp': time.time()
        }
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=4)
    except Exception:
        pass 