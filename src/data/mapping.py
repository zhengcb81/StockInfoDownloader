"""
映射管理模块
管理股票代码与组织ID的映射关系
"""

import os
import json
import time
from typing import Dict, Optional, List, Any
from pathlib import Path
from datetime import datetime, timedelta

from .models import OrgIdMapping
from ..core.exceptions import OrgIdError
from ..core.logger import get_logger
from .storage import JsonStorage
from ..utils.string_optimizer import standardize_stock_code

logger = get_logger(__name__)

class MappingManager:
    """映射管理器，管理股票代码与组织ID的映射"""
    
    def __init__(self, mapping_file: Optional[str] = None):
        """
        初始化映射管理器
        
        Args:
            mapping_file: 映射文件路径，如果为 None 则使用默认路径
        """
        self.logger = logger
        self._mappings: Dict[str, OrgIdMapping] = {}
        
        # 智能路径解析
        if mapping_file:
            self.mapping_file = Path(mapping_file)
        else:
            # 默认路径优先级：1. src/data/ 2. 根目录
            default_internal = Path(__file__).parent / "stock_orgid_mapping.json"
            default_root = Path("stock_orgid_mapping.json")
            
            if default_internal.exists():
                self.mapping_file = default_internal
            elif default_root.exists():
                self.mapping_file = default_root
            else:
                self.mapping_file = default_internal
                
        self.storage = JsonStorage(str(self.mapping_file))
        self._load_mapping()
    
    @property
    def mapping_data(self) -> Dict[str, OrgIdMapping]:
        """获取映射数据副本"""
        return self._mappings.copy()
    
    def reload_mapping(self) -> bool:
        """重新加载映射数据。如果解析失败则返回 False。"""
        try:
            # 在加载前先尝试 load，如果抛出异常（JSON损坏），直接返回 False
            data = self.storage.load()
            if data is None: # 表示解析失败 (取决于 JsonStorage 实现)
                return False
            self._load_mapping_from_data(data)
            return True
        except Exception as e:
            self.logger.error(f"重新加载映射数据失败: {e}")
            return False
    
    def _load_mapping(self) -> None:
        """从存储加载映射逻辑"""
        try:
            data = self.storage.load()
            self._load_mapping_from_data(data)
        except Exception as e:
            self.logger.error(f"初始化加载映射失败: {e}")
            self._mappings = {}

    def _load_mapping_from_data(self, data: Optional[Dict[str, Any]]) -> None:
        """从字典对象加载映射数据"""
        self._mappings = {}
        if not data:
            return

        for stock_code, item in data.items():
            try:
                # 兼容不同格式 (orgId vs org_id, name vs stock_name)
                org_id = item.get('orgId') or item.get('org_id')
                stock_name = item.get('name') or item.get('stock_name') or "Unknown"
                
                if org_id:
                    mapping = OrgIdMapping(
                        stock_code=stock_code,
                        org_id=org_id,
                        stock_name=stock_name,
                        source=item.get('source', 'auto'),
                        confidence=float(item.get('confidence', 0.8))
                    )
                    # 处理时间戳兼容性
                    if 'timestamp' in item:
                        mapping.last_updated = datetime.fromtimestamp(item['timestamp'])
                    elif 'last_updated' in item:
                        try:
                            mapping.last_updated = datetime.fromisoformat(item['last_updated'])
                        except:
                            pass
                            
                    self._mappings[stock_code] = mapping
            except Exception as e:
                self.logger.warning(f"跳过无效映射项 {stock_code}: {e}")

        self.logger.info(f"已加载 {len(self._mappings)} 个映射")

    def _save_mappings(self) -> None:
        """保存映射到文件"""
        data = {}
        for stock_code, m in self._mappings.items():
            data[stock_code] = {
                'orgId': m.org_id,
                'name': m.stock_name,
                'source': m.source,
                'timestamp': m.last_updated.timestamp(),
                'confidence': m.confidence
            }
        if not self.storage.save(data):
            raise OrgIdError("无法保存映射数据到存储")

    def get_org_id(self, stock_code: str, force_refresh: bool = False) -> Optional[str]:
        """获取组织ID"""
        stock_code = standardize_stock_code(stock_code)
        if not stock_code: return None
        
        if not force_refresh and stock_code in self._mappings:
            return self._mappings[stock_code].org_id
        return None

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """获取股票名称"""
        stock_code = standardize_stock_code(stock_code)
        if not stock_code: return None
        if stock_code in self._mappings:
            return self._mappings[stock_code].stock_name
        return None

    def add_mapping(self, stock_code: str, org_id: str, stock_name: str, 
                    source: str = "auto", confidence: float = 0.8) -> bool:
        """添加新映射。如果已存在或保存失败则返回 False。"""
        stock_code = standardize_stock_code(stock_code)
        if not stock_code or stock_code in self._mappings:
            return False
            
        self._mappings[stock_code] = OrgIdMapping(
            stock_code=stock_code,
            org_id=org_id,
            stock_name=stock_name,
            source=source,
            confidence=confidence
        )
        try:
            self._save_mappings()
            return True
        except:
            return False

    def remove_mapping(self, stock_code: str) -> bool:
        """移除映射"""
        stock_code = standardize_stock_code(stock_code)
        if stock_code in self._mappings:
            del self._mappings[stock_code]
            try:
                self._save_mappings()
                return True
            except:
                return False
        return False

    def get_all_stock_codes(self) -> List[str]:
        """获取所有股票代码"""
        return list(self._mappings.keys())

    def get_org_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取组织信息字典"""
        stock_code = standardize_stock_code(stock_code)
        if stock_code in self._mappings:
            m = self._mappings[stock_code]
            return {
                'org_id': m.org_id,
                'stock_name': m.stock_name,
                'source': m.source,
                'confidence': m.confidence,
                'last_updated': m.last_updated.isoformat()
            }
        return None

    def _validate_mapping_data(self, data: Any) -> bool:
        """验证数据格式"""
        if not isinstance(data, dict): return False
        for v in data.values():
            if not isinstance(v, dict): return False
            # 严格校验键名
            org_id = v.get('org_id') or v.get('orgId')
            name = v.get('name') or v.get('stock_name')
            if not org_id or not name: return False
            if org_id == 'invalid' or name == 'invalid': return False
        return True
