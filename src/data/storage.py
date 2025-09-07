"""
数据存储模块
提供数据持久化功能
"""

import json
import csv
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

from .models import DownloadRecord, OrgIdMapping, StockInfo, DownloadStatus
from ..core.logger import get_logger

logger = get_logger(__name__)


class StorageManager:
    """数据存储管理器"""
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化存储管理器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # 数据库文件
        self.db_path = self.data_dir / "stockinfo.db"
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS download_records (
                        id TEXT PRIMARY KEY,
                        stock_code TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER DEFAULT 0,
                        download_url TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS orgid_mappings (
                        stock_code TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        stock_name TEXT NOT NULL,
                        source TEXT DEFAULT 'auto',
                        last_updated TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0
                    )
                ''')
                
                conn.commit()
                logger.info("数据库初始化成功")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def save_download_record(self, record: DownloadRecord) -> None:
        """保存下载记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO download_records 
                    (id, stock_code, file_name, file_path, file_size, download_url, 
                     status, created_at, updated_at, error_message, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.id, record.stock_code, record.file_name, record.file_path,
                    record.file_size, record.download_url, record.status.value,
                    record.created_at.isoformat(), record.updated_at.isoformat(),
                    record.error_message, record.retry_count
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存下载记录失败: {e}")
            raise
    
    def get_download_records(self, stock_code: Optional[str] = None) -> List[DownloadRecord]:
        """获取下载记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if stock_code:
                    cursor = conn.execute(
                        'SELECT * FROM download_records WHERE stock_code = ? ORDER BY created_at DESC',
                        (stock_code,)
                    )
                else:
                    cursor = conn.execute(
                        'SELECT * FROM download_records ORDER BY created_at DESC'
                    )
                
                records = []
                for row in cursor.fetchall():
                    record = DownloadRecord(
                        id=row[0],
                        stock_code=row[1],
                        file_name=row[2],
                        file_path=row[3],
                        file_size=row[4],
                        download_url=row[5],
                        status=DownloadStatus(row[6]),
                        created_at=datetime.fromisoformat(row[7]),
                        updated_at=datetime.fromisoformat(row[8]),
                        error_message=row[9],
                        retry_count=row[10]
                    )
                    records.append(record)
                
                return records
                
        except Exception as e:
            logger.error(f"获取下载记录失败: {e}")
            return []
    
    def save_orgid_mapping(self, mapping: OrgIdMapping) -> None:
        """保存组织ID映射"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO orgid_mappings 
                    (stock_code, org_id, stock_name, source, last_updated, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    mapping.stock_code, mapping.org_id, mapping.stock_name,
                    mapping.source, mapping.last_updated.isoformat(), mapping.confidence
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存组织ID映射失败: {e}")
            raise
    
    def get_orgid_mappings(self) -> List[OrgIdMapping]:
        """获取所有组织ID映射"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT * FROM orgid_mappings ORDER BY last_updated DESC'
                )
                
                mappings = []
                for row in cursor.fetchall():
                    mapping = OrgIdMapping(
                        stock_code=row[0],
                        org_id=row[1],
                        stock_name=row[2],
                        source=row[3],
                        last_updated=datetime.fromisoformat(row[4]),
                        confidence=row[5]
                    )
                    mappings.append(mapping)
                
                return mappings
                
        except Exception as e:
            logger.error(f"获取组织ID映射失败: {e}")
            return []
    
    def get_orgid_mapping(self, stock_code: str) -> Optional[OrgIdMapping]:
        """获取单个组织ID映射"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT * FROM orgid_mappings WHERE stock_code = ?',
                    (stock_code,)
                )
                
                row = cursor.fetchone()
                if row:
                    return OrgIdMapping(
                        stock_code=row[0],
                        org_id=row[1],
                        stock_name=row[2],
                        source=row[3],
                        last_updated=datetime.fromisoformat(row[4]),
                        confidence=row[5]
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"获取组织ID映射失败: {e}")
            return None
    
    def export_to_json(self, file_path: str, data_type: str = "mappings") -> None:
        """导出数据到JSON文件"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if data_type == "mappings":
                mappings = self.get_orgid_mappings()
                data = [mapping.to_dict() for mapping in mappings]
            elif data_type == "records":
                records = self.get_download_records()
                data = [record.to_dict() for record in records]
            else:
                raise ValueError(f"不支持的数据类型: {data_type}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"数据已导出到: {file_path}")
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            raise
    
    def export_to_csv(self, file_path: str, data_type: str = "mappings") -> None:
        """导出数据到CSV文件"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if data_type == "mappings":
                mappings = self.get_orgid_mappings()
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['股票代码', '组织ID', '股票名称', '来源', '更新时间', '置信度'])
                    
                    for mapping in mappings:
                        writer.writerow([
                            mapping.stock_code,
                            mapping.org_id,
                            mapping.stock_name,
                            mapping.source,
                            mapping.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
                            mapping.confidence
                        ])
            
            elif data_type == "records":
                records = self.get_download_records()
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        '股票代码', '文件名', '文件路径', '文件大小',
                        '下载URL', '状态', '创建时间', '更新时间', '错误信息', '重试次数'
                    ])
                    
                    for record in records:
                        writer.writerow([
                            record.stock_code,
                            record.file_name,
                            record.file_path,
                            record.file_size,
                            record.download_url or '',
                            record.status.value,
                            record.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            record.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                            record.error_message or '',
                            record.retry_count
                        ])
            
            logger.info(f"数据已导出到: {file_path}")
            
        except Exception as e:
            logger.error(f"导出数据失败: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, int]:
        """获取存储统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT COUNT(*), status FROM download_records GROUP BY status'
                )
                
                stats = {
                    'total_downloads': 0,
                    'completed': 0,
                    'failed': 0,
                    'pending': 0,
                    'skipped': 0,
                    'total_mappings': 0
                }
                
                for count, status in cursor.fetchall():
                    stats['total_downloads'] += count
                    if status in stats:
                        stats[status] = count
                
                cursor = conn.execute('SELECT COUNT(*) FROM orgid_mappings')
                stats['total_mappings'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 90) -> int:
        """
        清理旧数据
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的记录数量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'DELETE FROM download_records WHERE updated_at < ?',
                    (cutoff_date.isoformat(),)
                )
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"清理 {deleted_count} 条旧记录")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return 0