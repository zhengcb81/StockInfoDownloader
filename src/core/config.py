"""
配置管理模块
提供统一的配置加载和管理功能
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from .exceptions import (
    ConfigError, ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)
from .config_constants import ConfigConstants


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _config = {}
    
    def __new__(cls, config_file=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file=None, environment='production'):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config_path = None
            self._environment = environment
            self._test_config = None
            if config_file:
                self.load_config(config_file)
    
    @with_error_handling(
        error_code=ErrorCode.CONFIG_FILE_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.TERMINATE
    )
    def load_config(self, config_path: str = "config.json") -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict[str, Any]: 配置字典
            
        Raises:
            ConfigError: 配置文件加载失败
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                raise ConfigError(
                    f"配置文件不存在: {config_path}",
                    error_code=ErrorCode.CONFIG_FILE_NOT_FOUND,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.TERMINATE,
                    context={"config_path": str(config_path)}
                )
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                self._config_path = str(config_path)
            
            return self._config
            
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"配置文件格式错误: {e}",
                error_code=ErrorCode.CONFIG_FORMAT_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.TERMINATE,
                context={"config_path": str(config_path), "parse_error": str(e)},
                original_exception=e
            )
        except Exception as e:
            raise ConfigError(
                f"加载配置文件失败: {e}",
                error_code=ErrorCode.CONFIG_LOAD_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.TERMINATE,
                context={"config_path": str(config_path)},
                original_exception=e
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名，支持点分路径如 'pages.0.name'
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        if not self._config:
            self.load_config()
        
        # 简化点分路径访问
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            elif isinstance(value, list) and k.isdigit() and int(k) < len(value):
                value = value[int(k)]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键名
            value: 配置值
        """
        if not self._config:
            self.load_config()
        
        keys = key.split('.')
        target = self._config
        
        # 简化嵌套字典创建
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        
        target[keys[-1]] = value
    
    @with_error_handling(
        error_code=ErrorCode.CONFIG_SAVE_ERROR,
        severity=ErrorSeverity.ERROR,
        recovery_strategy=RecoveryStrategy.FALLBACK
    )
    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，如果为None则使用原路径
        """
        if config_path is None:
            config_path = self._config_path
        
        if config_path is None:
            raise ConfigError(
                "未指定配置文件路径",
                error_code=ErrorCode.CONFIG_PATH_NOT_SET,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.TERMINATE,
                context={"operation": "save_config"}
            )
        
        try:
            config_path = Path(config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            raise ConfigError(
                f"保存配置文件失败: {e}",
                error_code=ErrorCode.CONFIG_SAVE_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                context={"config_path": str(config_path)},
                original_exception=e
            )
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置框架（无具体股票代码）"""
        return {
            # 基础配置
            "save_dir": "downloads",
            "headless": True,
            "max_retries": 3,
            "use_dynamic_delay": True,
            
            # 网络配置
            "base_url": "https://www.cninfo.com.cn",
            "page_load_strategy": "eager",  # 性能优化：eager模式仅等待DOM加载
            "timeout": {
                "page_load": 30,  # 减少页面加载超时时间
                "element_wait": 30,
                "download": 180,
                "script": 30
            },
            
            # 选择器配置
            "selectors": {
                "detail_links": "//a[contains(@href, '/new/disclosure/detail')]",
                "download_button": "//button[contains(., '公告下载')]",
                "next_page_button": "//button[contains(@class, 'el-pagination__next')]",
                "table_element": "//table[contains(@class, 'el-table__body')]"
            },
            
            # 文件配置
            "files": {
                "allowed_extensions": [".pdf", ".doc", ".docx", ".xls", ".xlsx"],
                "mapping_file": "stock_orgid_mapping.json",
                "log_dir": "logs"
            },
            
            # 下载配置
            "download": {
                "max_downloads_per_session": 5,
                "pagination_wait": 2,
                "human_behavior_delay": 3
            },
            
            # 页面配置
            "pages": [
                {
                    "name": "调研",
                    "suffix": "research",
                    "allowed_keywords": None
                },
                {
                    "name": "定期公告", 
                    "suffix": "periodicReports",
                    "allowed_keywords": None
                },
                {
                    "name": "最新公告",
                    "suffix": "latestAnnouncement", 
                    "allowed_keywords": ["招股说明书"]
                }
            ]
        }
    
    def reset_config(self) -> None:
        """重置为默认配置"""
        self._config = self.get_default_config()
        if self._config_path:
            self.save_config()
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取完整配置"""
        if not self._config:
            self.load_config()
        return self._config.copy()
    
    @property
    def config_path(self) -> Optional[str]:
        """获取配置文件路径"""
        return self._config_path
    
    def get_base_url(self) -> str:
        """获取基础URL"""
        return self.get('base_url', 'https://www.cninfo.com.cn')
    
    def get_timeout(self, timeout_type: str = 'page_load') -> int:
        """获取超时时间"""
        return self.get(f'timeout.{timeout_type}', 60)
    
    def get_selector(self, selector_name: str) -> str:
        """获取选择器"""
        return self.get(f'selectors.{selector_name}', '')
    
    def get_user_agents(self) -> list:
        """获取用户代理列表"""
        return self.get('webdriver.user_agents', [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ])
    
    def get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.get('retries.max_attempts', 3)
    
    def is_headless(self) -> bool:
        """是否使用无头模式"""
        return self.get('webdriver.headless', True)
    
    def get_window_size(self) -> str:
        """获取窗口大小"""
        return self.get('webdriver.window_size', '1920,1080')
    
    def get_page_load_strategy(self) -> str:
        """获取页面加载策略"""
        return self.get('page_load_strategy', 'eager')

    def load_test_config(self, config_path: str = "configs/test_config.json") -> Dict[str, Any]:
        """
        加载测试配置文件

        Args:
            config_path: 测试配置文件路径

        Returns:
            Dict[str, Any]: 测试配置字典
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                # 尝试相对于项目根目录的路径
                project_root = Path(__file__).parent.parent.parent
                config_path = project_root / config_path

            if not config_path.exists():
                raise ConfigError(
                    f"测试配置文件不存在: {config_path}",
                    error_code=ErrorCode.CONFIG_FILE_NOT_FOUND,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.FALLBACK,
                    context={"config_path": str(config_path)}
                )

            with open(config_path, 'r', encoding='utf-8') as f:
                self._test_config = json.load(f)

            return self._test_config

        except Exception as e:
            raise ConfigError(
                f"加载测试配置文件失败: {e}",
                error_code=ErrorCode.CONFIG_LOAD_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.FALLBACK,
                context={"config_path": str(config_path)},
                original_exception=e
            )

    def get_test_config(self, key: str = None, default: Any = None) -> Any:
        """
        获取测试配置值

        Args:
            key: 配置键名，支持点分路径
            default: 默认值

        Returns:
            Any: 配置值
        """
        if self._test_config is None:
            self.load_test_config()

        if key is None:
            return self._test_config.copy()

        # 支持点分路径
        keys = key.split('.')
        value = self._test_config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            elif isinstance(value, list) and k.isdigit() and int(k) < len(value):
                value = value[int(k)]
            else:
                return default

        return value

    def get_test_stock(self, stock_code: str) -> Dict[str, str]:
        """
        获取测试股票信息

        Args:
            stock_code: 股票代码

        Returns:
            Dict[str, str]: 股票信息字典
        """
        test_stocks = self.get_test_config('test_data.stocks', [])
        for stock in test_stocks:
            if stock.get('code') == stock_code:
                return stock
        return {}

    def get_test_timeout(self, timeout_type: str = 'validation') -> int:
        """
        获取测试超时时间

        Args:
            timeout_type: 超时类型

        Returns:
            int: 超时时间
        """
        return self.get_test_config(f'test_environment.{timeout_type}',
                                   ConfigConstants.get_timeout(timeout_type))

    def is_test_environment(self) -> bool:
        """是否为测试环境"""
        return self._environment == 'test'

    def get_test_directory(self, dir_name: str) -> str:
        """
        获取测试目录路径

        Args:
            dir_name: 目录名称

        Returns:
            str: 目录路径
        """
        return self.get_test_config(f'test_directories.{dir_name}', '')

    def use_constants(self, key: str) -> Any:
        """
        使用配置常量

        Args:
            key: 常量键名

        Returns:
            Any: 常量值
        """
        constant_map = {
            'base_url': ConfigConstants.get_base_url(),
            'timeouts': ConfigConstants.DEFAULT_TIMEOUTS,
            'selectors': ConfigConstants.SELECTORS,
            'test_data': ConfigConstants.TEST_DATA,
            'user_agents': ConfigConstants.USER_AGENTS
        }

        if '.' in key:
            parent, child = key.split('.', 1)
            if parent in constant_map and isinstance(constant_map[parent], dict):
                return constant_map[parent].get(child)
            return None
        else:
            return constant_map.get(key)