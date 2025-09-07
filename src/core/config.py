"""
配置管理模块
提供统一的配置加载和管理功能
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from .exceptions import ConfigError


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _config = {}
    
    def __new__(cls, config_file=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file=None):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config_path = None
            if config_file:
                self.load_config(config_file)
    
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
                raise ConfigError(f"配置文件不存在: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
                self._config_path = str(config_path)
            
            return self._config
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise ConfigError(f"加载配置文件失败: {e}")
    
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
        
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                elif isinstance(value, list) and k.isdigit():
                    value = value[int(k)]
                else:
                    return default
            return value
        except (KeyError, IndexError, TypeError):
            return default
    
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
        
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        target[keys[-1]] = value
    
    def save_config(self, config_path: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，如果为None则使用原路径
        """
        if config_path is None:
            config_path = self._config_path
        
        if config_path is None:
            raise ConfigError("未指定配置文件路径")
        
        try:
            config_path = Path(config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            raise ConfigError(f"保存配置文件失败: {e}")
    
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
        """
        获取超时时间
        
        Args:
            timeout_type: 超时类型
            
        Returns:
            超时时间（秒）
        """
        return self.get(f'timeout.{timeout_type}', 60)
    
    def get_selector(self, selector_name: str) -> str:
        """
        获取选择器
        
        Args:
            selector_name: 选择器名称
            
        Returns:
            选择器字符串
        """
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