"""
文件服务模块
负责文件处理、保存和验证
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..core.config_constants import ConfigConstants


class FileService:
    """文件服务类，负责文件处理和验证"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化文件服务

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)

    def clean_filename(self, filename: str) -> str:
        """
        清理文件名中的非法字符

        Args:
            filename: 原始文件名

        Returns:
            str: 清理后的文件名
        """
        invalid_chars = self.config_manager.use_constants('INVALID_FILENAME_CHARS')
        return re.sub(invalid_chars, '_', filename)

    def get_stock_directory(self, stock_code: str, stock_name: str) -> Path:
        """
        获取股票保存目录

        Args:
            stock_code: 股票代码
            stock_name: 股票名称

        Returns:
            Path: 股票目录路径
        """
        base_dir = self.config_manager.get('save_dir', 'downloads')
        stock_dir_name = f"{stock_code}_{self.clean_filename(stock_name)}"
        stock_dir = Path(base_dir) / stock_dir_name

        # 创建目录
        stock_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"创建股票目录: {stock_dir}")

        return stock_dir

    def save_downloaded_file(self, source_path: str, target_directory: Path,
                           stock_code: str, document_info: Dict[str, Any]) -> Optional[str]:
        """
        保存下载的文件

        Args:
            source_path: 源文件路径
            target_directory: 目标目录
            stock_code: 股票代码
            document_info: 文档信息字典

        Returns:
            Optional[str]: 保存后的文件路径，失败返回None
        """
        try:
            if not os.path.exists(source_path):
                self.logger.error(f"源文件不存在: {source_path}")
                return None

            # 构建目标文件名
            file_name = self._generate_filename(stock_code, document_info)
            target_path = target_directory / file_name

            # 移动文件
            shutil.move(source_path, target_path)
            self.logger.info(f"文件保存成功: {target_path}")

            return str(target_path)

        except Exception as e:
            self.logger.error(f"文件保存失败: {e}")
            return None

    def _generate_filename(self, stock_code: str, document_info: Dict[str, Any]) -> str:
        """
        生成文件名

        Args:
            stock_code: 股票代码
            document_info: 文档信息

        Returns:
            str: 生成的文件名
        """
        # 获取文件基本信息
        title = document_info.get('title', '未知文档')
        date = document_info.get('date', '')
        file_type = document_info.get('file_type', 'pdf')

        # 清理标题
        clean_title = self.clean_filename(title)

        # 构建文件名
        if date:
            filename = f"{stock_code}_{clean_title}_{date}.{file_type}"
        else:
            filename = f"{stock_code}_{clean_title}.{file_type}"

        return filename

    def validate_downloaded_file(self, file_path: str, expected_size: Optional[int] = None) -> bool:
        """
        验证下载的文件

        Args:
            file_path: 文件路径
            expected_size: 预期文件大小（可选）

        Returns:
            bool: 文件是否有效
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"文件不存在: {file_path}")
                return False

            file_size = os.path.getsize(file_path)

            # 检查文件大小
            if expected_size and file_size != expected_size:
                self.logger.warning(f"文件大小不匹配: 期望 {expected_size}, 实际 {file_size}")
                return False

            # 检查文件是否为空
            if file_size == 0:
                self.logger.error("下载的文件为空")
                return False

            # 检查文件扩展名
            allowed_extensions = self.config_manager.get('files.allowed_extensions',
                                                          ConfigConstants.FILE_CONFIG['allowed_extensions'])
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in allowed_extensions:
                self.logger.warning(f"不支持的文件类型: {file_ext}")
                return False

            self.logger.info(f"文件验证通过: {file_path} (大小: {file_size} bytes)")
            return True

        except Exception as e:
            self.logger.error(f"文件验证失败: {e}")
            return False

    def cleanup_temp_files(self, download_dir: str, max_age_hours: int = 24) -> int:
        """
        清理临时文件

        Args:
            download_dir: 下载目录
            max_age_hours: 最大文件年龄（小时）

        Returns:
            int: 清理的文件数量
        """
        try:
            download_path = Path(download_dir)
            if not download_path.exists():
                return 0

            current_time = datetime.now()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0

            for file_path in download_path.glob('*'):
                if file_path.is_file():
                    file_age = (current_time - datetime.fromtimestamp(file_path.stat().st_mtime)).total_seconds()
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"清理临时文件: {file_path}")

            self.logger.info(f"清理完成，共清理 {cleaned_count} 个临时文件")
            return cleaned_count

        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")
            return 0

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 文件信息字典
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {}

            stat = path.stat()
            return {
                'name': path.name,
                'size': stat.st_size,
                'extension': path.suffix.lower(),
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'path': str(path.absolute())
            }

        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            return {}

    def backup_file(self, source_path: str, backup_dir: str) -> Optional[str]:
        """
        备份文件

        Args:
            source_path: 源文件路径
            backup_dir: 备份目录

        Returns:
            Optional[str]: 备份文件路径，失败返回None
        """
        try:
            source = Path(source_path)
            if not source.exists():
                self.logger.error(f"源文件不存在: {source_path}")
                return None

            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)

            # 生成备份文件名（添加时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{source.stem}_{timestamp}{source.suffix}"
            backup_file_path = backup_path / backup_filename

            # 复制文件
            shutil.copy2(source_path, backup_file_path)
            self.logger.info(f"文件备份成功: {backup_file_path}")

            return str(backup_file_path)

        except Exception as e:
            self.logger.error(f"文件备份失败: {e}")
            return None