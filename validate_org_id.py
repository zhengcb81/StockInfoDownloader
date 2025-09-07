#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Org ID验证模块 - 通过配置驱动
验证org ID的有效性并自动清理无效缓存
"""

import requests
import json
import time
import logging
from typing import Optional, Dict, Any
from src.core.config import ConfigManager
from orgid_utils import get_org_id_by_code, _load_mapping

# 配置管理器
config_manager = ConfigManager()
logger = logging.getLogger(__name__)

def load_validation_config() -> Dict[str, Any]:
    """加载验证配置"""
    try:
        return config_manager.get('org_id_validation', {})
    except Exception:
        return {
            'base_url': 'https://www.cninfo.com.cn/new/disclosure/stock',
            'validation_timeout': 10,
            'max_retries': 3,
            'retry_delay': 2,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }

def load_cache_config() -> Dict[str, Any]:
    """加载缓存配置"""
    try:
        return config_manager.get('cache_management', {})
    except Exception:
        return {
            'auto_invalidate': True,
            'force_refresh': False,
            'save_mapping': True,
            'mapping_file': 'stock_orgid_mapping.json'
        }

def validate_org_id_url(stock_code: str, org_id: str, config: Dict[str, Any] = None) -> bool:
    """
    简化验证org ID对应的URL是否有效
    仅检查HTTP状态码和基本响应
    
    Args:
        stock_code: 股票代码
        org_id: 组织ID
        config: 验证配置，从config.json读取
        
    Returns:
        bool: URL是否有效
    """
    if config is None:
        config = load_validation_config()
    
    base_url = config.get('base_url', 'https://www.cninfo.com.cn/new/disclosure/stock')
    timeout = config.get('validation_timeout', 10)
    headers = config.get('headers', {})
    max_retries = config.get('max_retries', 3)
    retry_delay = config.get('retry_delay', 2)
    
    url = f"{base_url}?stockCode={stock_code}&orgId={org_id}&sjstsBond=false#latestAnnouncement"
    
    for attempt in range(max_retries):
        try:
            # 使用HEAD请求进行轻量级验证
            response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            
            # 仅检查状态码
            is_valid = response.status_code == 200
            
            if is_valid:
                logger.info(f"验证成功: {stock_code} 的 org ID {org_id} 有效")
                return True
            else:
                logger.warning(f"验证失败: {stock_code} 的 org ID {org_id} 无效 (状态码: {response.status_code})")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return False
        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            return False
    
    return False

def invalidate_cache(stock_code: str, mapping_file: str = None) -> Optional[str]:
    """
    使缓存失效并重新获取org ID
    
    Args:
        stock_code: 股票代码
        mapping_file: 映射文件路径，从配置读取
    
    Returns:
        Optional[str]: 新的有效org ID
    """
    cache_config = load_cache_config()
    if mapping_file is None:
        mapping_file = cache_config.get('mapping_file', 'stock_orgid_mapping.json')
    
    try:
        mapping = _load_mapping(mapping_file)
        
        if stock_code in mapping:
            old_org_id = mapping[stock_code]['orgId']
            del mapping[stock_code]
            
            if cache_config.get('save_mapping', True):
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(mapping, f, ensure_ascii=False, indent=4)
            
            logger.info(f"🗑️  已删除 {stock_code} 的无效缓存: {old_org_id}")
        
        new_org_id = get_org_id_by_code(stock_code, force_run=True, mapping_file=mapping_file)
        
        if new_org_id:
            logger.info(f"✅ 重新获取成功: {stock_code} 的新 org ID: {new_org_id}")
            return new_org_id
        else:
            logger.error(f"❌ 重新获取失败: {stock_code} 无法获取有效 org ID")
            return None
            
    except Exception as e:
        logger.error(f"🚨 缓存失效过程出错: {e}")
        return None

def validate_and_refresh_org_id(stock_code: str, mapping_file: str = None) -> Optional[str]:
    """
    验证org ID有效性，如无效则重新获取
    
    Args:
        stock_code: 股票代码
        mapping_file: 映射文件路径，从配置读取
        
    Returns:
        Optional[str]: 有效的org ID
    """
    cache_config = load_cache_config()
    if mapping_file is None:
        mapping_file = cache_config.get('mapping_file', 'stock_orgid_mapping.json')
    
    try:
        current_org_id = get_org_id_by_code(stock_code, mapping_file=mapping_file)
        
        if not current_org_id:
            logger.info(f"🔍 {stock_code} 无缓存，开始获取...")
            return get_org_id_by_code(stock_code, force_run=True, mapping_file=mapping_file)
        
        validation_config = load_validation_config()
        is_valid = validate_org_id_url(stock_code, current_org_id, validation_config)
        
        if is_valid:
            return current_org_id
        elif cache_config.get('auto_invalidate', True):
            logger.warning(f"⚠️  {stock_code} 的 org ID {current_org_id} 无效，重新获取...")
            return invalidate_cache(stock_code, mapping_file)
        else:
            logger.warning(f"⚠️  {stock_code} 的 org ID {current_org_id} 无效但auto_invalidate=false")
            return current_org_id
            
    except Exception as e:
        logger.error(f"🚨 验证和刷新过程出错: {e}")
        return None

def test_stock_validation(stock_code: str = "300470"):
    """测试特定股票的org ID验证"""
    print(f"开始验证股票 {stock_code} 的 org ID...")
    
    valid_org_id = validate_and_refresh_org_id(stock_code)
    
    if valid_org_id:
        print("最终有效org ID:", valid_org_id)
        return valid_org_id
    else:
        print("无法获取有效org ID")
        return None

if __name__ == "__main__":
    # 运行测试
    test_stock_validation("300470")