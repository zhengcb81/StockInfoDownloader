"""
数据模型模块
定义项目中使用的数据模型
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from ..utils.string_optimizer import standardize_stock_code


class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StockInfo:
    """股票信息数据模型"""
    stock_code: str
    stock_name: str
    org_id: Optional[str] = None
    market: Optional[str] = None
    industry: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.stock_code:
            raise ValueError("股票代码不能为空")

        # 标准化股票代码
        standardized = standardize_stock_code(self.stock_code)
        if not standardized:
            raise ValueError("无效的股票代码格式")
        self.stock_code = standardized
    
    @property
    def is_valid(self) -> bool:
        """检查股票信息是否有效"""
        return bool(self.stock_code and self.stock_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'org_id': self.org_id,
            'market': self.market,
            'industry': self.industry
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockInfo':
        """从字典创建实例"""
        return cls(
            stock_code=data.get('stock_code', ''),
            stock_name=data.get('stock_name', ''),
            org_id=data.get('org_id'),
            market=data.get('market'),
            industry=data.get('industry')
        )


@dataclass
class DownloadRecord:
    """下载记录数据模型"""
    id: str
    stock_code: str
    file_name: str
    file_path: str
    file_size: int = 0
    download_url: Optional[str] = None
    status: DownloadStatus = DownloadStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def update_status(self, status: DownloadStatus, error_msg: Optional[str] = None) -> None:
        """更新下载状态"""
        self.status = status
        self.error_message = error_msg
        self.updated_at = datetime.now()
        
        if status == DownloadStatus.FAILED:
            self.retry_count += 1
    
    def mark_completed(self, file_size: int = 0) -> None:
        """标记为完成"""
        self.file_size = file_size
        self.update_status(DownloadStatus.COMPLETED)
    
    def mark_failed(self, error_msg: str) -> None:
        """标记为失败"""
        self.update_status(DownloadStatus.FAILED, error_msg)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'download_url': self.download_url,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadRecord':
        """从字典创建实例"""
        return cls(
            id=data['id'],
            stock_code=data['stock_code'],
            file_name=data['file_name'],
            file_path=data['file_path'],
            file_size=data.get('file_size', 0),
            download_url=data.get('download_url'),
            status=DownloadStatus(data.get('status', 'pending')),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0)
        )


@dataclass
class OrgIdMapping:
    """组织ID映射数据模型"""
    stock_code: str
    org_id: str
    stock_name: str
    source: str = "auto"  # auto, preset, manual
    last_updated: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0  # 置信度 0-1
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.stock_code or not self.org_id:
            raise ValueError("股票代码和组织ID不能为空")

        # 标准化股票代码
        standardized = standardize_stock_code(self.stock_code)
        if not standardized:
            raise ValueError("无效的股票代码格式")
        self.stock_code = standardized
    
    @property
    def is_valid(self) -> bool:
        """检查映射是否有效"""
        return bool(self.stock_code and self.org_id and self.stock_name)
    
    def update_confidence(self, confidence: float) -> None:
        """更新置信度"""
        self.confidence = max(0.0, min(1.0, confidence))
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'org_id': self.org_id,
            'stock_name': self.stock_name,
            'source': self.source,
            'last_updated': self.last_updated.isoformat(),
            'confidence': self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrgIdMapping':
        """从字典创建实例"""
        return cls(
            stock_code=data['stock_code'],
            org_id=data['org_id'],
            stock_name=data['stock_name'],
            source=data.get('source', 'auto'),
            last_updated=datetime.fromisoformat(data['last_updated']),
            confidence=data.get('confidence', 1.0)
        )


@dataclass
class DownloadTask:
    """下载任务数据模型"""
    task_id: str
    stock_info: StockInfo
    target_pages: List[str] = field(default_factory=list)
    save_directory: str = "downloads"
    max_retries: int = 3
    use_anti_crawler: bool = True
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.target_pages:
            self.target_pages = ["research", "periodicReports"]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'stock_info': self.stock_info.to_dict(),
            'target_pages': self.target_pages,
            'save_directory': self.save_directory,
            'max_retries': self.max_retries,
            'use_anti_crawler': self.use_anti_crawler
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadTask':
        """从字典创建实例"""
        stock_info = StockInfo.from_dict(data['stock_info'])
        return cls(
            task_id=data['task_id'],
            stock_info=stock_info,
            target_pages=data.get('target_pages', ["research", "periodicReports"]),
            save_directory=data.get('save_directory', 'downloads'),
            max_retries=data.get('max_retries', 3),
            use_anti_crawler=data.get('use_anti_crawler', True)
        )