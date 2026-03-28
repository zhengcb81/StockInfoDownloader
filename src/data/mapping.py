"""
映射管理模块
管理股票代码与组织ID的映射关系
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import OrgIdError
from ..core.logger import get_logger
from ..utils.string_optimizer import standardize_stock_code
from .models import OrgIdMapping
from .storage import JsonStorage

logger = get_logger(__name__)


class MappingManager:
    """映射管理器，管理股票代码与组织ID的映射"""

    def __init__(self, mapping_file: Optional[str] = None, auto_fetch: bool = True):
        """
        初始化映射管理器

        Args:
            mapping_file: 映射文件路径，如果为 None 则使用默认路径
            auto_fetch: 是否允许从网络自动获取（默认True，单元测试可设为False）
        """
        self.logger = logger
        self._mappings: Dict[str, OrgIdMapping] = {}
        self._auto_fetch = auto_fetch  # 是否允许从网络获取

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
            if data is None:  # 表示解析失败 (取决于 JsonStorage 实现)
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
                org_id = item.get("orgId") or item.get("org_id")
                stock_name = item.get("name") or item.get("stock_name") or "Unknown"

                if org_id:
                    mapping = OrgIdMapping(
                        stock_code=stock_code,
                        org_id=org_id,
                        stock_name=stock_name,
                        source=item.get("source", "auto"),
                        confidence=float(item.get("confidence", 0.8)),
                    )
                    # 处理时间戳兼容性
                    if "timestamp" in item:
                        mapping.last_updated = datetime.fromtimestamp(item["timestamp"])
                    elif "last_updated" in item:
                        try:
                            mapping.last_updated = datetime.fromisoformat(
                                item["last_updated"]
                            )
                        except (ValueError, TypeError):
                            # Invalid date format, keep default datetime
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
                "orgId": m.org_id,
                "name": m.stock_name,
                "source": m.source,
                "timestamp": m.last_updated.timestamp(),
                "confidence": m.confidence,
            }
        if not self.storage.save(data):
            raise OrgIdError("无法保存映射数据到存储")

    def get_org_id(self, stock_code: str, force_refresh: bool = False) -> Optional[str]:
        """
        获取组织ID，如果本地没有则尝试从网络爬取

        Args:
            stock_code: 股票代码
            force_refresh: 是否强制刷新（从网络重新获取）

        Returns:
            Optional[str]: 组织ID，获取失败返回None
        """
        standardized_code = standardize_stock_code(stock_code)
        if not standardized_code:
            return None

        # 1. 先查本地缓存
        if not force_refresh and standardized_code in self._mappings:
            result = self._mappings[standardized_code].org_id
            return result or None

        # 2. 本地没有，且允许从网络获取
        if self._auto_fetch and (
            force_refresh or standardized_code not in self._mappings
        ):
            self.logger.info(f"本地映射未找到 {standardized_code}，尝试从网络获取...")
            org_id = self._crawl_org_id_from_web(standardized_code)
            if org_id:
                return org_id

        return None

    def _crawl_org_id_from_web(self, stock_code: str) -> Optional[str]:
        """
        从网络爬取 org_id 并保存到本地映射

        Args:
            stock_code: 股票代码

        Returns:
            Optional[str]: 组织ID，爬取失败返回None
        """
        try:
            from ..services.orgid_service import OrgIdService

            org_id_service = OrgIdService()
            org_id = org_id_service.get_org_id(stock_code, headless=True)

            if org_id:
                self.logger.info(f"从网络获取到 org_id: {stock_code} -> {org_id}")

                # 尝试获取股票名称
                stock_name = self._get_stock_name_from_web(stock_code)

                # 保存到本地映射
                self.add_mapping(
                    stock_code=stock_code,
                    org_id=org_id,
                    stock_name=stock_name or f"Stock_{stock_code}",
                    source="auto",
                    confidence=0.7,
                )
                return org_id
            else:
                self.logger.warning(f"从网络获取 org_id 失败: {stock_code}")
                return None

        except Exception as e:
            self.logger.error(f"爬取 org_id 异常: {e}")
            return None

    def _get_stock_name_from_web(self, stock_code: str) -> Optional[str]:
        """
        从网络获取股票名称

        Args:
            stock_code: 股票代码

        Returns:
            Optional[str]: 股票名称，获取失败返回None
        """
        try:
            from ..services.stock_service import StockService

            stock_service = StockService()
            return stock_service.get_stock_name(stock_code)
        except Exception as e:
            self.logger.debug(f"从网络获取股票名称失败: {e}")
            return None

    def get_stock_name(
        self, stock_code: str, auto_crawl: Optional[bool] = None
    ) -> Optional[str]:
        """
        获取股票名称，如果本地没有则尝试从网络获取

        Args:
            stock_code: 股票代码
            auto_crawl: 是否自动从网络获取（None时使用实例的_auto_fetch设置）

        Returns:
            Optional[str]: 股票名称，获取失败返回None
        """
        standardized_code = standardize_stock_code(stock_code)
        if not standardized_code:
            return None

        # 1. 先查本地缓存
        if standardized_code in self._mappings:
            result = self._mappings[standardized_code].stock_name
            if result and result != f"Stock_{standardized_code}":
                return result

        # 2. 确定是否从网络获取
        should_crawl = auto_crawl if auto_crawl is not None else self._auto_fetch

        # 3. 本地没有或名称不完整，尝试从网络获取
        if should_crawl:
            stock_name = self._get_stock_name_from_web(standardized_code)
            if stock_name:
                # 如果已有映射，更新名称
                if standardized_code in self._mappings:
                    self._mappings[standardized_code].stock_name = stock_name
                    self._save_mappings()
                return stock_name

        return None

    def add_mapping(
        self,
        stock_code: str,
        org_id: str,
        stock_name: str,
        source: str = "auto",
        confidence: float = 0.8,
    ) -> bool:
        """添加新映射。如果已存在或保存失败则返回 False。"""
        standardized_code = standardize_stock_code(stock_code)
        if not standardized_code or standardized_code in self._mappings:
            return False

        self._mappings[stock_code] = OrgIdMapping(
            stock_code=stock_code,
            org_id=org_id,
            stock_name=stock_name,
            source=source,
            confidence=confidence,
        )
        try:
            self._save_mappings()
            return True
        except (OSError, IOError, OrgIdError) as e:
            self.logger.warning(f"保存映射失败: {e}")
            return False

    def remove_mapping(self, stock_code: str) -> bool:
        """移除映射"""
        standardized_code = standardize_stock_code(stock_code)
        if standardized_code and standardized_code in self._mappings:
            del self._mappings[standardized_code]
            try:
                self._save_mappings()
                return True
            except (OSError, IOError, OrgIdError) as e:
                self.logger.warning(f"保存映射失败: {e}")
                return False
        return False

    def get_all_stock_codes(self) -> List[str]:
        """获取所有股票代码"""
        return list(self._mappings.keys())

    def get_org_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取组织信息字典"""
        standardized_code = standardize_stock_code(stock_code)
        if stock_code in self._mappings:
            m = self._mappings[stock_code]
            return {
                "org_id": m.org_id or "",
                "stock_name": m.stock_name or "",
                "source": m.source or "",
                "confidence": m.confidence,
                "last_updated": m.last_updated.isoformat(),
            }
        return None

    def validate_org_id(self, org_id: str) -> bool:
        """
        验证组织 ID 是否有效（格式校验及是否存在于映射中）

        Args:
            org_id: 组织 ID

        Returns:
            bool: 是否有效
        """
        if not org_id or not isinstance(org_id, str):
            return False
        # 简单校验：长度应在 4-20 之间
        if not (4 <= len(org_id) <= 20):
            return False
        # 检查是否在当前映射列表中（作为反向查询）
        for m in self._mappings.values():
            if m.org_id == org_id:
                return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取映射统计信息

        Returns:
            Dict: 统计信息
        """
        sources: Dict[str, int] = {}
        for m in self._mappings.values():
            sources[m.source] = sources.get(m.source, 0) + 1

        return {
            "total": len(self._mappings),
            "total_count": len(self._mappings),
            "source_distribution": sources,
            "last_updated": datetime.now().isoformat(),
        }

    def _validate_mapping_data(self, data: Any) -> bool:
        """验证数据格式"""
        if not isinstance(data, dict):
            return False
        for v in data.values():
            if not isinstance(v, dict):
                return False
            # 严格校验键名
            org_id = v.get("org_id") or v.get("orgId")
            name = v.get("name") or v.get("stock_name")
            if not org_id or not name:
                return False
            if org_id == "invalid" or name == "invalid":
                return False
        return True
