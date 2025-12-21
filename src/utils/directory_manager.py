"""
目录管理模块 - 负责文件目录的创建和组织
与浏览器策略解耦，专注于业务逻辑层的目录管理
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple
from ..data.mapping import MappingManager

logger = logging.getLogger(__name__)


class DirectoryManager:
    """统一的目录管理服务"""

    def __init__(self, mapping_manager: Optional[MappingManager] = None):
        """初始化目录管理器"""
        self.mapping_manager = mapping_manager

    def get_company_directory(self, stock_code: str, base_save_dir: Path) -> Path:
        """
        获取公司对应的目录路径

        Args:
            stock_code: 股票代码
            base_save_dir: 基础保存目录

        Returns:
            Path: 公司目录路径
        """
        company_name = self._get_company_name(stock_code)
        company_dir = base_save_dir / company_name
        return company_dir

    def create_company_directory(self, stock_code: str, base_save_dir: Path) -> Path:
        """
        创建公司目录

        Args:
            stock_code: 股票代码
            base_save_dir: 基础保存目录

        Returns:
            Path: 创建的公司目录路径
        """
        company_dir = self.get_company_directory(stock_code, base_save_dir)
        company_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"创建公司目录: {company_dir}")
        return company_dir

    def organize_downloaded_file(self, temp_file_path: Path, stock_code: str,
                               filename: str, base_save_dir: Path) -> Path:
        """
        组织下载的文件到正确的目录

        Args:
            temp_file_path: 临时文件路径
            stock_code: 股票代码
            filename: 目标文件名
            base_save_dir: 基础保存目录

        Returns:
            Path: 最终保存的文件路径
        """
        if not temp_file_path.exists():
            raise FileNotFoundError(f"临时文件不存在: {temp_file_path}")

        # 创建公司目录
        company_dir = self.create_company_directory(stock_code, base_save_dir)

        # 确定最终保存路径
        final_path = company_dir / filename

        # 移动文件
        try:
            shutil.move(str(temp_file_path), str(final_path))
            logger.info(f"文件已组织到: {final_path}")
            return final_path
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            raise

    def ensure_save_directory(self, save_path: Path) -> None:
        """
        确保保存目录存在

        Args:
            save_path: 文件保存路径
        """
        save_dir = save_path.parent
        save_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"确保目录存在: {save_dir}")

    def _get_company_name(self, stock_code: str) -> str:
        """
        获取公司名称

        Args:
            stock_code: 股票代码

        Returns:
            str: 公司名称
        """
        if self.mapping_manager:
            company_name = self.mapping_manager.get_stock_name(stock_code)
            if company_name:
                return company_name

        # 备用方案：使用股票代码（不加前缀）
        return stock_code

    def validate_directory_structure(self, base_save_dir: Path,
                                  expected_companies: list) -> Tuple[bool, list]:
        """
        验证目录结构是否符合预期（严格模式）

        Args:
            base_save_dir: 基础保存目录
            expected_companies: 预期的公司列表

        Returns:
            Tuple[bool, list]: (是否有效, 问题列表)
        """
        if not base_save_dir.exists():
            return False, [f"基础目录不存在: {base_save_dir}"]

        issues = []

        # 检查所有项目都应该是目录（严格模式，不允许任何临时文件）
        for item in base_save_dir.iterdir():
            if item.is_file():
                issues.append(f"根目录中存在文件: {item.name}")
            elif item.is_dir():
                # 检查是否是预期的公司目录
                if item.name not in expected_companies:
                    issues.append(f"根目录中存在非预期的目录: {item.name}")

        # 检查预期的公司目录
        for company in expected_companies:
            company_dir = base_save_dir / company
            if not company_dir.exists():
                issues.append(f"公司目录不存在: {company}")
            elif not company_dir.is_dir():
                issues.append(f"公司路径不是目录: {company}")

        return len(issues) == 0, issues


def create_directory_manager(mapping_file: str = "stock_orgid_mapping.json") -> DirectoryManager:
    """
    创建目录管理器实例

    Args:
        mapping_file: 映射文件路径

    Returns:
        DirectoryManager: 目录管理器实例
    """
    mapping_manager = MappingManager(mapping_file)
    return DirectoryManager(mapping_manager)