"""
股票信息服务模块
提供股票名称查询和基础信息获取功能
"""

import csv
from pathlib import Path
from typing import Any, Dict, Optional, cast

import requests

from ..core.logger import get_logger
from ..data.models import StockInfo
from ..utils.string_optimizer import standardize_stock_code

logger = get_logger(__name__)


class StockService:
    """股票信息服务"""

    def __init__(self):
        """初始化股票服务"""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        self.base_url = "https://www.cninfo.com.cn"

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """
        根据股票代码获取股票名称

        优先使用腾讯财经接口，如果失败则尝试巨潮API

        Args:
            stock_code: 股票代码

        Returns:
            Optional[str]: 股票名称，获取失败返回None
        """
        try:
            standardized_code = standardize_stock_code(stock_code)
            if not standardized_code:
                return None

            # 方法1: 使用腾讯财经接口（更稳定）
            stock_name = self._get_name_from_tencent(standardized_code)
            if stock_name:
                return stock_name

            # 方法2: 使用巨潮资讯网的API
            stock_name = self._get_name_from_cninfo(standardized_code)
            if stock_name:
                return stock_name

            logger.warning(f"未找到股票名称: {standardized_code}")
            return None

        except Exception as e:
            logger.error(f"获取股票名称失败: {e}")
            return None

    def _get_name_from_tencent(self, stock_code: str) -> Optional[str]:
        """
        从腾讯财经接口获取股票名称

        Args:
            stock_code: 6位股票代码

        Returns:
            Optional[str]: 股票名称
        """
        try:
            # 判断交易所
            exchange = "sh" if stock_code.startswith(("6", "5", "9")) else "sz"

            # 腾讯财经接口
            url = f"https://qt.gtimg.cn/q={exchange}{stock_code}"

            response = self.session.get(url, timeout=5)
            response.encoding = "gbk"

            # 解析返回数据
            data = response.text
            parts = data.split("~")

            if len(parts) > 1 and parts[1]:
                stock_name = parts[1]
                logger.info(f"从腾讯获取股票名称成功: {stock_code} -> {stock_name}")
                return stock_name

            return None

        except Exception as e:
            logger.debug(f"从腾讯获取股票名称失败: {e}")
            return None

    def _get_name_from_cninfo(self, stock_code: str) -> Optional[str]:
        """
        从巨潮资讯网API获取股票名称

        Args:
            stock_code: 6位股票代码

        Returns:
            Optional[str]: 股票名称
        """
        try:
            url = f"{self.base_url}/new/information/topSearch/query"
            params = {"keyWord": stock_code, "maxNum": 10}

            response = self.session.get(url, params=params, timeout=10)  # type: ignore[arg-type]
            response.raise_for_status()

            data = response.json()

            # 查找匹配的股票
            for item in data:
                if item.get("code") == stock_code:
                    value = item.get("value", "")
                    if isinstance(value, str):
                        stock_name = value.split("-")[0].strip()
                        if stock_name:
                            logger.info(
                                f"从巨潮获取股票名称成功: {stock_code} -> {stock_name}"
                            )
                            return stock_name

            return None

        except Exception as e:
            logger.debug(f"从巨潮获取股票名称失败: {e}")
            return None

    def get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        """
        获取股票详细信息

        Args:
            stock_code: 股票代码

        Returns:
            Optional[StockInfo]: 股票信息，获取失败返回None
        """
        try:
            stock_name = self.get_stock_name(stock_code)
            if not stock_name:
                return None

            # 获取市场信息
            market = self._get_market_info(stock_code)

            return StockInfo(
                stock_code=stock_code, stock_name=stock_name, market=market
            )

        except Exception as e:
            logger.error(f"获取股票信息失败: {e}")
            return None

    def _get_market_info(self, stock_code: str) -> Optional[str]:
        """
        获取市场信息

        Args:
            stock_code: 股票代码

        Returns:
            Optional[str]: 市场代码（SH/SZ/BJ）
        """
        try:
            stock_code = stock_code.strip()

            # 根据代码前缀判断市场
            if stock_code.startswith(("6", "5")):
                return "SH"  # 上海证券交易所
            elif stock_code.startswith(("0", "3", "2")):
                return "SZ"  # 深圳证券交易所
            elif stock_code.startswith(("4", "8")):
                return "BJ"  # 北京证券交易所
            else:
                return None

        except Exception as e:
            logger.error(f"获取市场信息失败: {e}")
            return None

    def validate_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码格式

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否有效
        """
        try:
            stock_code = stock_code.strip()

            # 检查是否为6位数字
            if not stock_code.isdigit():
                return False

            if len(stock_code) != 6:
                return False

            # 检查是否在有效范围内
            valid_prefixes = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
            if stock_code[0] not in valid_prefixes:
                return False

            return True

        except Exception as e:
            logger.error(f"验证股票代码失败: {e}")
            return False

    def get_stock_list_from_file(self, file_path: str) -> list:
        """
        从CSV文件获取股票列表

        Args:
            file_path: CSV文件路径

        Returns:
            list: 股票代码列表
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                logger.error(f"文件不存在: {file_path}")
                return []

            stock_codes = []
            with open(path_obj, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # 跳过表头
                for row in reader:
                    if row and row[0].strip().isdigit():
                        standardized_code = standardize_stock_code(row[0])
                        if standardized_code:
                            stock_codes.append(standardized_code)

            logger.info(f"从文件加载 {len(stock_codes)} 个股票代码")
            return stock_codes

        except Exception as e:
            logger.error(f"读取股票列表文件失败: {e}")
            return []

    def batch_get_stock_names(self, stock_codes: list) -> Dict[str, Optional[str]]:
        """
        批量获取股票名称

        Args:
            stock_codes: 股票代码列表

        Returns:
            Dict[str, Optional[str]]: 股票代码到名称的映射
        """
        results = {}

        for code in stock_codes:
            name = self.get_stock_name(code)
            results[code] = name

            # 添加延迟避免频繁请求
            import time

            time.sleep(0.5)

        return results
