"""
数据模块
提供数据模型、映射管理和存储功能
"""

from .mapping import MappingManager
from .models import DownloadRecord, OrgIdMapping, StockInfo
from .storage import StorageManager

__all__ = [
    "StockInfo",
    "DownloadRecord",
    "OrgIdMapping",
    "MappingManager",
    "StorageManager",
]
