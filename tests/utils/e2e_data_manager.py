#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
端到端测试数据管理器
提供端到端测试数据的统一管理，包括生成、清理、验证和版本控制
"""

import hashlib
import json
import logging
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
      # 可选，如果可用

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TestDataVersion:
    """测试数据版本信息"""

    version: str
    timestamp: str
    description: str
    data_hash: str
    source: str
    metadata: Dict[str, Any]


@dataclass
class StockTestData:
    """股票测试数据"""

    code: str
    name: str
    market: str
    description: str
    expected_files: List[str] = None
    validation_rules: Dict[str, Any] = None

    def __post_init__(self):
        if self.expected_files is None:
            self.expected_files = []
        if self.validation_rules is None:
            self.validation_rules = {}


class E2ETestDataManager:
    """端到端测试数据管理器"""

    def __init__(self, base_dir: Optional[str] = None):
        """
        初始化测试数据管理器

        Args:
            base_dir: 基础目录，如果为None则使用临时目录
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).parent.parent / "e2e" / "test_data"

        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 子目录结构
        self.raw_data_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.temp_dir = self.base_dir / "temp"
        self.version_dir = self.base_dir / "versions"

        for dir_path in [
            self.raw_data_dir,
            self.processed_dir,
            self.temp_dir,
            self.version_dir,
        ]:
            dir_path.mkdir(exist_ok=True)

        self.version_file = self.base_dir / "versions.json"
        self.current_version = self._load_current_version()

    def _load_current_version(self) -> Optional[TestDataVersion]:
        """加载当前版本信息"""
        if self.version_file.exists():
            try:
                with open(self.version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return TestDataVersion(**data)
            except Exception as e:
                logger.warning(f"加载版本信息失败: {e}")
        return None

    def create_temp_directory(self, prefix: str = "e2e_test_") -> Path:
        """创建临时目录"""
        temp_path = self.temp_dir / f"{prefix}_{int(time.time())}"
        temp_path.mkdir(exist_ok=True)
        logger.info(f"创建临时目录: {temp_path}")
        return temp_path

    def cleanup_temp_directories(self, older_than_hours: int = 24):
        """清理旧的临时目录"""
        current_time = time.time()
        for temp_dir in self.temp_dir.iterdir():
            if temp_dir.is_dir():
                try:
                    dir_time = temp_dir.stat().st_mtime
                    if current_time - dir_time > older_than_hours * 3600:
                        shutil.rmtree(temp_dir)
                        logger.info(f"清理旧临时目录: {temp_dir}")
                except Exception as e:
                    logger.warning(f"清理目录失败 {temp_dir}: {e}")

    def load_stock_test_data(
        self, config_file: str = "real_stock_codes.json"
    ) -> List[StockTestData]:
        """加载股票测试数据"""
        config_path = Path(__file__).parent.parent / "e2e" / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stocks = []
        for stock_data in data.get("stocks", []):
            stock = StockTestData(
                code=stock_data.get("code"),
                name=stock_data.get("name"),
                market=stock_data.get("market", ""),
                description=stock_data.get("description", ""),
            )
            stocks.append(stock)

        logger.info(f"加载了 {len(stocks)} 个股票测试数据")
        return stocks

    def validate_test_data(
        self, stock_data: StockTestData, actual_files: List[str]
    ) -> Tuple[bool, List[str]]:
        """验证测试数据"""
        errors = []

        # 验证股票代码格式
        if (
            not stock_data.code
            or not stock_data.code.isdigit()
            or len(stock_data.code) != 6
        ):
            errors.append(f"股票代码格式无效: {stock_data.code}")

        # 验证股票名称
        if not stock_data.name or len(stock_data.name.strip()) == 0:
            errors.append(f"股票名称为空: {stock_data.code}")

        # 验证实际文件
        if not actual_files:
            errors.append(f"没有下载的文件: {stock_data.code}")
        else:
            # 检查文件是否可读
            for file_path in actual_files:
                path = Path(file_path)
                if not path.exists():
                    errors.append(f"文件不存在: {file_path}")
                elif path.stat().st_size == 0:
                    errors.append(f"文件为空: {file_path}")

        return len(errors) == 0, errors

    def create_data_version(
        self, description: str, source: str = "manual"
    ) -> TestDataVersion:
        """创建新的数据版本"""
        # 计算当前数据的哈希值
        data_files = list(self.raw_data_dir.glob("*.json")) + list(
            self.processed_dir.glob("*.json")
        )
        data_content = ""

        for file_path in sorted(data_files):
            if file_path.is_file():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data_content += f.read()
                except Exception as e:
                    logger.warning(f"读取文件失败 {file_path}: {e}")

        data_hash = hashlib.sha256(data_content.encode("utf-8")).hexdigest()[:16]

        version = TestDataVersion(
            version=f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            description=description,
            data_hash=data_hash,
            source=source,
            metadata={"file_count": len(data_files), "manager_version": "1.0.0"},
        )

        # 保存版本信息
        version_path = self.version_dir / f"{version.version}.json"
        with open(version_path, "w", encoding="utf-8") as f:
            json.dump(asdict(version), f, ensure_ascii=False, indent=2)

        # 更新当前版本
        with open(self.version_file, "w", encoding="utf-8") as f:
            json.dump(asdict(version), f, ensure_ascii=False, indent=2)

        self.current_version = version
        logger.info(f"创建数据版本: {version.version} - {description}")

        return version

    def get_version_history(self) -> List[TestDataVersion]:
        """获取版本历史"""
        versions = []
        for version_file in sorted(self.version_dir.glob("*.json")):
            try:
                with open(version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                versions.append(TestDataVersion(**data))
            except Exception as e:
                logger.warning(f"加载版本文件失败 {version_file}: {e}")

        return sorted(versions, key=lambda v: v.timestamp, reverse=True)

    def cleanup_all(self, keep_versions: int = 5):
        """清理所有临时数据和旧版本"""
        # 清理临时目录
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir()
            logger.info("清理临时目录")

        # 保留最近的几个版本
        versions = self.get_version_history()
        if len(versions) > keep_versions:
            for version in versions[keep_versions:]:
                version_file = self.version_dir / f"{version.version}.json"
                if version_file.exists():
                    version_file.unlink()
                    logger.info(f"删除旧版本: {version.version}")


# 便捷函数
def create_test_data_manager() -> E2ETestDataManager:
    """创建测试数据管理器实例"""
    return E2ETestDataManager()


def get_stock_test_data() -> List[StockTestData]:
    """获取股票测试数据（便捷函数）"""
    manager = E2ETestDataManager()
    return manager.load_stock_test_data()


if __name__ == "__main__":
    # 测试数据管理器
    manager = E2ETestDataManager()
    print(f"测试数据管理器初始化完成，基础目录: {manager.base_dir}")

    stocks = manager.load_stock_test_data()
    print(f"加载了 {len(stocks)} 个股票测试数据")

    for stock in stocks[:3]:
        print(f"  - {stock.code}: {stock.name}")

    version = manager.create_data_version("初始测试数据版本", source="auto")
    print(f"创建数据版本: {version.version}")

    manager.cleanup_temp_directories()
    print("临时目录清理完成")
