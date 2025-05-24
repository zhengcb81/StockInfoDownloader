import os
import json
from orgid_crawler import OrgIdCrawler
from get_stock_name import get_stock_name
from typing import Optional

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
    mapping = {}
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
        except Exception:
            mapping = {}
    if not force_run and stock_code in mapping and 'orgId' in mapping[stock_code]:
        return mapping[stock_code]['orgId']
    crawler = OrgIdCrawler(output_file=mapping_file, headless=headless)
    org_id = crawler.get_org_id(stock_code)
    crawler.close_driver()
    if org_id:
        name = get_stock_name(stock_code, mapping_file)
        mapping[stock_code] = {
            'orgId': org_id,
            'name': name,
            'timestamp': __import__('time').time()
        }
        try:
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
        return org_id
    return None

def get_stock_name_by_code(stock_code: str, mapping_file: str = 'stock_orgid_mapping.json') -> Optional[str]:
    """
    根据证券代码获取公司名称。优先查本地映射表，查不到则通过东方财富API获取。
    参数：
        stock_code (str): 证券代码
        mapping_file (str): 映射表文件路径
    返回：
        name (str): 公司名称，查不到返回None
    """
    mapping = {}
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            if stock_code in mapping and 'name' in mapping[stock_code]:
                return mapping[stock_code]['name']
        except Exception:
            pass
    secid = None
    if stock_code.startswith(('000', '001', '002', '003', '300', '301')):
        secid = f'0.{stock_code}'
    elif stock_code.startswith(('600', '601', '603', '605', '688')):
        secid = f'1.{stock_code}'
    else:
        return None
    import requests
    url = f'http://push2.eastmoney.com/api/qt/stock/get?secid={secid}'
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        name = data.get('data', {}).get('name')
        if name:
            mapping[stock_code] = mapping.get(stock_code, {})
            mapping[stock_code]['name'] = name
            try:
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(mapping, f, ensure_ascii=False, indent=4)
            except Exception:
                pass
            return name
    except Exception:
        pass
    return None 