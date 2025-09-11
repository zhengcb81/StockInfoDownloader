"""
映射管理模块
管理股票代码与组织ID的映射关系
"""

import os
import json
import time
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

from .models import OrgIdMapping
from ..core.exceptions import OrgIdError
from ..core.logger import get_logger

logger = get_logger(__name__)


class MappingManager:
    """映射管理器，管理股票代码与组织ID的映射"""
    
    def __init__(self, mapping_file: str = "stock_orgid_mapping.json"):
        """
        初始化映射管理器
        
        Args:
            mapping_file: 映射文件路径
        """
        self.mapping_file = Path(mapping_file)
        self._mappings: Dict[str, OrgIdMapping] = {}
        
        self._load_mappings()
    
    @property
    def mapping_data(self) -> Dict[str, OrgIdMapping]:
        """
        获取映射数据属性
        
        Returns:
            Dict[str, OrgIdMapping]: 映射数据字典
        """
        return self._mappings.copy()
    
    def reload_mapping(self) -> bool:
        """
        重新加载映射数据
        
        Returns:
            bool: 重新加载是否成功
        """
        try:
            self._mappings.clear()
            self._load_mappings()
            logger.info("映射数据重新加载成功")
            return True
        except Exception as e:
            logger.error(f"重新加载映射数据失败: {e}")
            return False
    
    def _load_mappings(self) -> None:
        """加载映射文件"""
        if not self.mapping_file.exists():
            logger.info("映射文件不存在，创建空映射")
            return
        
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for stock_code, mapping_data in data.items():
                org_id = mapping_data.get('orgId')
                stock_name = mapping_data.get('name', 'Unknown')
                
                if org_id:
                    mapping = OrgIdMapping(
                        stock_code=stock_code,
                        org_id=org_id,
                        stock_name=stock_name,
                        source=mapping_data.get('source', 'auto'),
                        confidence=mapping_data.get('confidence', 0.8)
                    )
                    self._mappings[stock_code] = mapping
            
            logger.info(f"已加载 {len(self._mappings)} 个映射")
            
        except Exception as e:
            logger.error(f"加载映射文件失败: {e}")
            self._mappings = {}
    
    def _save_mappings(self) -> None:
        """保存映射到文件"""
        try:
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for stock_code, mapping in self._mappings.items():
                data[stock_code] = {
                    'orgId': mapping.org_id,
                    'name': mapping.stock_name,
                    'source': mapping.source,
                    'timestamp': mapping.last_updated.timestamp(),
                    'confidence': mapping.confidence
                }
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(self._mappings)} 个映射")
            
        except Exception as e:
            logger.error(f"保存映射文件失败: {e}")
            raise OrgIdError(f"保存映射文件失败: {e}")
    
    def get_org_id(self, stock_code: str, force_refresh: bool = False) -> Optional[str]:
        """
        获取组织ID
        
        Args:
            stock_code: 股票代码
            force_refresh: 是否强制刷新
            
        Returns:
            Optional[str]: 组织ID，不存在返回None
        """
        stock_code = stock_code.strip().zfill(6)
        
        if not force_refresh and stock_code in self._mappings:
            mapping = self._mappings[stock_code]
            
            # 检查映射是否过期（30天）
            if datetime.now() - mapping.last_updated > timedelta(days=30):
                logger.info(f"映射已过期: {stock_code}")
                return None
            
            return mapping.org_id
        
        # 如果映射中不存在，尝试直接从JSON文件中查找（兼容旧版本）
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if stock_code in data:
                    mapping_data = data[stock_code]
                    org_id = mapping_data.get('orgId')
                    stock_name = mapping_data.get('name', 'Unknown')
                    
                    if org_id:
                        # 将找到的映射添加到内存中
                        mapping = OrgIdMapping(
                            stock_code=stock_code,
                            org_id=org_id,
                            stock_name=stock_name,
                            source=mapping_data.get('source', 'file'),
                            confidence=mapping_data.get('confidence', 0.8)
                        )
                        self._mappings[stock_code] = mapping
                        logger.info(f"从文件加载映射: {stock_code} -> {org_id}")
                        return org_id
                        
            except Exception as e:
                logger.error(f"从文件加载映射失败: {e}")
        
        return None
    
    def add_mapping(self, 
                   stock_code: str, 
                   org_id: str, 
                   stock_name: str,
                   source: str = "auto",
                   confidence: float = 0.8) -> bool:
        """
        添加映射
        
        Args:
            stock_code: 股票代码
            org_id: 组织ID
            stock_name: 股票名称
            source: 来源
            confidence: 置信度
            
        Returns:
            bool: 添加是否成功
        """
        try:
            stock_code = stock_code.strip().zfill(6)
            
            mapping = OrgIdMapping(
                stock_code=stock_code,
                org_id=org_id,
                stock_name=stock_name,
                source=source,
                confidence=confidence
            )
            
            self._mappings[stock_code] = mapping
            self._save_mappings()
            
            logger.info(f"添加映射: {stock_code} -> {org_id} ({stock_name})")
            return True
        except Exception as e:
            logger.error(f"添加映射失败: {e}")
            return False
    
    def remove_mapping(self, stock_code: str) -> bool:
        """
        移除映射
        
        Args:
            stock_code: 股票代码
            
        Returns:
            bool: 是否成功移除
        """
        stock_code = stock_code.strip().zfill(6)
        
        if stock_code in self._mappings:
            del self._mappings[stock_code]
            self._save_mappings()
            logger.info(f"移除映射: {stock_code}")
            return True
        
        return False
    
    def update_mapping(self, 
                      stock_code: str, 
                      org_id: str = None, 
                      stock_name: str = None,
                      confidence: float = None) -> bool:
        """
        更新映射
        
        Args:
            stock_code: 股票代码
            org_id: 新的组织ID
            stock_name: 新的股票名称
            confidence: 新的置信度
            
        Returns:
            bool: 是否成功更新
        """
        stock_code = stock_code.strip().zfill(6)
        
        if stock_code not in self._mappings:
            return False
        
        mapping = self._mappings[stock_code]
        
        if org_id is not None:
            mapping.org_id = org_id
        if stock_name is not None:
            mapping.stock_name = stock_name
        if confidence is not None:
            mapping.confidence = confidence
        
        mapping.last_updated = datetime.now()
        self._save_mappings()
        
        logger.info(f"更新映射: {stock_code}")
        return True
    
    def add_duplicate_mapping(self, 
                            stock_code: str, 
                            org_id: str, 
                            stock_name: str,
                            source: str = "auto",
                            confidence: float = 0.8) -> bool:
        """
        添加重复映射（应该失败）
        
        Args:
            stock_code: 股票代码
            org_id: 组织ID
            stock_name: 股票名称
            source: 来源
            confidence: 置信度
            
        Returns:
            bool: 添加是否成功（应该总是返回False）
        """
        stock_code = stock_code.strip().zfill(6)
        
        # 检查是否已存在
        if stock_code in self._mappings:
            logger.warning(f"尝试添加重复映射: {stock_code} -> {org_id}")
            return False
        
        # 如果不存在，正常添加
        return self.add_mapping(stock_code, org_id, stock_name, source, confidence)
    
    def get_all_mappings(self) -> Dict[str, OrgIdMapping]:
        """获取所有映射"""
        return self._mappings.copy()
    
    def get_mappings_by_source(self, source: str) -> List[OrgIdMapping]:
        """
        根据来源获取映射
        
        Args:
            source: 来源
            
        Returns:
            List[OrgIdMapping]: 映射列表
        """
        return [m for m in self._mappings.values() if m.source == source]
    
    def get_expired_mappings(self, days: int = 30) -> List[str]:
        """
        获取过期映射的股票代码
        
        Args:
            days: 过期天数
            
        Returns:
            List[str]: 过期映射的股票代码列表
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        expired_codes = []
        
        for stock_code, mapping in self._mappings.items():
            if mapping.last_updated < cutoff_date:
                expired_codes.append(stock_code)
        
        return expired_codes
    
    def validate_org_id(self, org_id: str) -> bool:
        """
        验证组织ID格式
        
        Args:
            org_id: 组织ID
            
        Returns:
            bool: 是否有效
        """
        if not org_id:
            return False
        
        # 检查是否为数字字符串
        return org_id.isdigit() and len(org_id) >= 6
    
    def get_statistics(self) -> Dict[str, int]:
        """获取映射统计信息"""
        stats = {
            'total': len(self._mappings),
            'auto': len([m for m in self._mappings.values() if m.source == 'auto']),
            'preset': len([m for m in self._mappings.values() if m.source == 'preset']),
            'manual': len([m for m in self._mappings.values() if m.source == 'manual'])
        }
        return stats
    
    def clear_expired_mappings(self, days: int = 90) -> int:
        """
        清除过期映射
        
        Args:
            days: 过期天数
            
        Returns:
            int: 清除的映射数量
        """
        expired_codes = self.get_expired_mappings(days)
        
        for code in expired_codes:
            if code in self._mappings:
                del self._mappings[code]
        
        if expired_codes:
            self._save_mappings()
            logger.info(f"清除 {len(expired_codes)} 个过期映射")
        
        return len(expired_codes)
    
    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        获取股票名称
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[str]: 股票名称，不存在返回None
        """
        stock_code = stock_code.strip().zfill(6)
        
        # 首先从内存中的映射查找
        if stock_code in self._mappings:
            return self._mappings[stock_code].stock_name
        
        # 如果内存中不存在，尝试直接从JSON文件中查找（兼容旧版本）
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if stock_code in data:
                    stock_name = data[stock_code].get('name')
                    if stock_name:
                        logger.info(f"从文件获取股票名称: {stock_code} -> {stock_name}")
                        return stock_name
                        
            except Exception as e:
                logger.error(f"从文件获取股票名称失败: {e}")
        
        return None
    
    def get_all_stock_codes(self) -> List[str]:
        """
        获取所有股票代码
        
        Returns:
            List[str]: 股票代码列表
        """
        # 从内存中的映射获取
        stock_codes = list(self._mappings.keys())
        
        # 如果内存中没有，尝试从JSON文件中获取（兼容旧版本）
        if not stock_codes and self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                stock_codes = list(data.keys())
                logger.info(f"从文件获取 {len(stock_codes)} 个股票代码")
            except Exception as e:
                logger.error(f"从文件获取股票代码失败: {e}")
        
        return stock_codes
    
    def get_org_info(self, stock_code: str) -> Optional[Dict[str, str]]:
        """
        获取组织信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            Optional[Dict[str, str]]: 组织信息，不存在返回None
        """
        stock_code = stock_code.strip().zfill(6)
        
        # 首先从内存中的映射查找
        if stock_code in self._mappings:
            mapping = self._mappings[stock_code]
            return {
                'org_id': mapping.org_id,
                'stock_name': mapping.stock_name,
                'source': mapping.source,
                'confidence': str(mapping.confidence),
                'last_updated': mapping.last_updated.isoformat()
            }
        
        # 如果内存中不存在，尝试直接从JSON文件中查找（兼容旧版本）
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if stock_code in data:
                    mapping_data = data[stock_code]
                    return {
                        'org_id': mapping_data.get('orgId'),
                        'stock_name': mapping_data.get('name'),
                        'source': mapping_data.get('source', 'file'),
                        'confidence': str(mapping_data.get('confidence', 0.8)),
                        'last_updated': datetime.fromtimestamp(mapping_data.get('timestamp', time.time())).isoformat()
                    }
                        
            except Exception as e:
                logger.error(f"从文件获取组织信息失败: {e}")
        
        return None
    
    def _validate_mapping_data(self, data: dict) -> bool:
        """
        验证映射数据格式
        
        Args:
            data: 要验证的数据
            
        Returns:
            bool: 数据是否有效
        """
        if not isinstance(data, dict):
            return False
        
        for stock_code, mapping in data.items():
            if not isinstance(mapping, dict):
                return False
            
            # 检查必需字段
            if 'org_id' not in mapping or 'name' not in mapping:
                return False
            
            # 检查字段值不为空且不是明显的无效值
            if (not mapping['org_id'] or 
                not mapping['name'] or 
                mapping['org_id'] == 'invalid' or 
                mapping['name'] == 'invalid'):
                return False
        
        return True