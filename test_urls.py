#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试URL构造是否正确
"""

import json

def test_url_construction():
    # 读取映射文件
    with open('stock_orgid_mapping.json', 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    
    # 测试两个股票代码
    stock_codes = ['002050', '301611']
    
    for stock_code in stock_codes:
        if stock_code in mapping:
            org_id = mapping[stock_code]['orgId']
            name = mapping[stock_code]['name']
            
            # 构造URL
            url = f"https://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#research"
            
            print(f"股票代码: {stock_code}")
            print(f"股票名称: {name}")
            print(f"组织ID: {org_id}")
            print(f"访问URL: {url}")
            print("-" * 80)
        else:
            print(f"股票代码 {stock_code} 不在映射表中")

if __name__ == "__main__":
    test_url_construction()