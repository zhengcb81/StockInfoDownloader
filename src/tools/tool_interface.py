"""
工具接口模块
统一管理所有工具功能，避免重复代码
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger
from src.core.config import ConfigManager


class BaseTool(ABC):
    """工具基类"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化工具基类

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行工具主要功能

        Args:
            **kwargs: 执行参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        pass

    def validate_params(self, **kwargs) -> bool:
        """
        验证执行参数

        Args:
            **kwargs: 执行参数

        Returns:
            bool: 参数是否有效
        """
        return True

    def get_help(self) -> str:
        """
        获取工具帮助信息

        Returns:
            str: 帮助信息
        """
        return self.__class__.__doc__ or "无帮助信息"


class ValidationTool(BaseTool):
    """验证工具基类"""

    def validate_page_content(self, stock_code: str, **kwargs) -> Dict[str, Any]:
        """
        验证页面内容

        Args:
            stock_code: 股票代码
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 验证结果
        """
        # 统一的页面内容验证逻辑
        org_id = kwargs.get('org_id')
        if not org_id:
            test_stock = self.config_manager.get_test_stock(stock_code)
            org_id = test_stock.get('org_id')

        if not org_id:
            return {'success': False, 'error': '无法获取组织ID'}

        return self._perform_validation(stock_code, org_id, **kwargs)

    @abstractmethod
    def _perform_validation(self, stock_code: str, org_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行具体的验证操作

        Args:
            stock_code: 股票代码
            org_id: 组织ID
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 验证结果
        """
        pass


class MonitoringTool(BaseTool):
    """监控工具基类"""

    def monitor_page_content(self, stock_code: str, **kwargs) -> Dict[str, Any]:
        """
        监控页面内容

        Args:
            stock_code: 股票代码
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 监控结果
        """
        org_id = kwargs.get('org_id')
        if not org_id:
            test_stock = self.config_manager.get_test_stock(stock_code)
            org_id = test_stock.get('org_id')

        if not org_id:
            return {'success': False, 'error': '无法获取组织ID'}

        return self._perform_monitoring(stock_code, org_id, **kwargs)

    @abstractmethod
    def _perform_monitoring(self, stock_code: str, org_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行具体的监控操作

        Args:
            stock_code: 股票代码
            org_id: 组织ID
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 监控结果
        """
        pass


class DebugTool(BaseTool):
    """调试工具基类"""

    def debug_download(self, **kwargs) -> Dict[str, Any]:
        """
        调试下载功能

        Args:
            **kwargs: 调试参数

        Returns:
            Dict[str, Any]: 调试结果
        """
        return self._perform_debug(**kwargs)

    @abstractmethod
    def _perform_debug(self, **kwargs) -> Dict[str, Any]:
        """
        执行具体的调试操作

        Args:
            **kwargs: 调试参数

        Returns:
            Dict[str, Any]: 调试结果
        """
        pass


class ToolRegistry:
    """工具注册表"""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, name: str, tool_class: type) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            tool_class: 工具类
        """
        cls._tools[name] = tool_class

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """
        获取工具实例

        Args:
            name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例
        """
        tool_class = cls._tools.get(name)
        if tool_class:
            return tool_class()
        return None

    @classmethod
    def list_tools(cls) -> List[str]:
        """
        列出所有注册的工具

        Returns:
            List[str]: 工具名称列表
        """
        return list(cls._tools.keys())

    @classmethod
    def execute_tool(cls, name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 执行参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        tool = cls.get_tool(name)
        if not tool:
            return {'success': False, 'error': f'工具 {name} 不存在'}

        try:
            if not tool.validate_params(**kwargs):
                return {'success': False, 'error': '参数验证失败'}

            return tool.execute(**kwargs)

        except Exception as e:
            return {'success': False, 'error': str(e)}


class ToolManager:
    """工具管理器"""

    def __init__(self):
        """初始化工具管理器"""
        self.registry = ToolRegistry()
        self.logger = get_logger(self.__class__.__name__)

    def register_tool(self, name: str, tool_class: type) -> None:
        """
        注册工具

        Args:
            name: 工具名称
            tool_class: 工具类
        """
        self.registry.register(name, tool_class)
        self.logger.info(f"注册工具: {name}")

    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具

        Args:
            name: 工具名称
            **kwargs: 执行参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        result = self.registry.execute_tool(name, **kwargs)
        self.logger.info(f"工具 {name} 执行结果: {result.get('success', False)}")
        return result

    def get_tool_help(self, name: str) -> str:
        """
        获取工具帮助信息

        Args:
            name: 工具名称

        Returns:
            str: 帮助信息
        """
        tool = self.registry.get_tool(name)
        if tool:
            return tool.get_help()
        return f"工具 {name} 不存在"

    def list_available_tools(self) -> List[str]:
        """
        列出可用工具

        Returns:
            List[str]: 可用工具列表
        """
        return self.registry.list_tools()


# 全局工具管理器实例
tool_manager = ToolManager()