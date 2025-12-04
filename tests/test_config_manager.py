"""
测试配置管理模块
统一管理测试配置，消除测试用例中的硬编码
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径，确保可以导入src模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import ConfigManager
from src.core.logger import get_logger


class ConfigManagerTool:
    """测试配置管理器工具"""

    def __init__(self, test_config_path: Optional[str] = None):
        """
        初始化测试配置管理器

        Args:
            test_config_path: 测试配置文件路径
        """
        # 先创建实例，再设置环境
        self.config_manager = ConfigManager()
        self.config_manager._environment = 'test'
        self.test_config_path = test_config_path or "configs/test_config.json"
        self.logger = get_logger(self.__class__.__name__)

        # 加载测试配置
        self._load_test_config()

    def _load_test_config(self) -> None:
        """加载测试配置"""
        try:
            self.test_config = self.config_manager.load_test_config(self.test_config_path)
        except Exception as e:
            self.logger.warning(f"加载测试配置失败: {e}")
            self.test_config = self._get_default_test_config()

    def _get_default_test_config(self) -> Dict[str, Any]:
        """获取默认测试配置"""
        return {
            "test_data": {
                "stocks": [
                    {"code": "300470", "name": "中密控股", "org_id": "9900023856"},
                    {"code": "301611", "name": "珂玛科技", "org_id": "9900047115"}
                ]
            },
            "test_environment": {
                "headless": False,
                "page_load_timeout": 30,
                "element_wait_timeout": 10,
                "download_timeout": 60
            }
        }

    def get_test_stock(self, stock_code: str) -> Dict[str, str]:
        """
        获取测试股票信息

        Args:
            stock_code: 股票代码

        Returns:
            Dict[str, str]: 股票信息字典
        """
        stocks = self.test_config.get('test_data', {}).get('stocks', [])
        for stock in stocks:
            if stock.get('code') == stock_code:
                return stock
        return {}

    def get_test_stocks(self) -> List[Dict[str, str]]:
        """
        获取所有测试股票

        Returns:
            List[Dict[str, str]]: 测试股票列表
        """
        return self.test_config.get('test_data', {}).get('stocks', [])

    def get_test_timeout(self, timeout_type: str) -> int:
        """
        获取测试超时时间

        Args:
            timeout_type: 超时类型

        Returns:
            int: 超时时间
        """
        return self.test_config.get('test_environment', {}).get(timeout_type, 30)

    def get_test_directory(self, dir_type: str) -> str:
        """
        获取测试目录路径

        Args:
            dir_type: 目录类型

        Returns:
            str: 目录路径
        """
        directories = self.test_config.get('test_directories', {})
        return directories.get(dir_type, '')

    def is_headless(self) -> bool:
        """
        是否使用无头模式

        Returns:
            bool: 是否使用无头模式
        """
        return self.test_config.get('test_environment', {}).get('headless', False)

    def get_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        获取测试场景配置

        Args:
            scenario_name: 场景名称

        Returns:
            Dict[str, Any]: 场景配置
        """
        scenarios = self.test_config.get('test_scenarios', {})
        return scenarios.get(scenario_name, {})

    def get_browser_test_config(self) -> Dict[str, Any]:
        """
        获取浏览器测试配置

        Returns:
            Dict[str, Any]: 浏览器测试配置
        """
        scenario = self.get_test_scenario('browser_test')
        if scenario:
            return scenario
        return {
            "strategies": ["selenium", "playwright"],
            "test_pages": ["research", "periodicReports", "latestAnnouncement"]
        }

    def get_e2e_test_config(self) -> Dict[str, Any]:
        """
        获取端到端测试配置

        Returns:
            Dict[str, Any]: 端到端测试配置
        """
        scenario = self.get_test_scenario('e2e_test')
        if scenario:
            return scenario
        return {
            "target_stocks": ["300470"],
            "expected_files": [
                "中密控股：2023年1月31日投资者关系活动记录表.pdf"
            ]
        }

    def get_validation_keywords(self, file_type: str) -> List[str]:
        """
        获取验证关键词

        Args:
            file_type: 文件类型

        Returns:
            List[str]: 关键词列表
        """
        return self.test_config.get('test_data', {}).get('validation_keywords', {}).get(file_type, [])

    def setup_test_environment(self) -> Dict[str, Any]:
        """
        设置测试环境

        Returns:
            Dict[str, Any]: 测试环境配置
        """
        env_config = self.test_config.get('test_environment', {})

        # 创建必要的测试目录
        for dir_name in ['base', 'results', 'expected', 'temp_config']:
            dir_path = self.get_test_directory(dir_name)
            if dir_path:
                Path(dir_path).mkdir(parents=True, exist_ok=True)

        return env_config

    def cleanup_test_environment(self) -> None:
        """清理测试环境"""
        # 清理临时文件
        temp_dirs = [
            self.get_test_directory('results'),
            self.get_test_directory('temp_config')
        ]

        for dir_path in temp_dirs:
            if dir_path and os.path.exists(dir_path):
                import shutil
                try:
                    shutil.rmtree(dir_path)
                    self.logger.info(f"清理测试目录: {dir_path}")
                except Exception as e:
                    self.logger.warning(f"清理目录失败: {e}")

    def get_download_test_paths(self) -> Dict[str, str]:
        """
        获取下载测试路径

        Returns:
            Dict[str, str]: 下载测试路径
        """
        download_test = self.test_config.get('test_data', {}).get('download_test', {})
        return download_test.get('test_files', {})

    def get_validation_config(self) -> Dict[str, Any]:
        """
        获取验证配置

        Returns:
            Dict[str, Any]: 验证配置
        """
        return self.test_config.get('test_data', {}).get('validation', {})


# 全局测试配置管理器实例
test_config_manager = ConfigManagerTool()