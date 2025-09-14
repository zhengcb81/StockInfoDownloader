"""
配置管理模块
提供统一的配置加载和管理功能
"""

import os
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from .exceptions import (
    ConfigError, ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)
from .config_constants import ConfigConstants
from .logger import get_logger


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _config = {}
    
    def __new__(cls, config_file=None):
        # 对于不同的配置文件路径，创建不同的实例
        # 这允许在测试中使用不同的配置文件而不相互影响
        if config_file:
            # 为测试文件创建新的实例
            instance = super().__new__(cls)
            instance._is_test_instance = True
            return instance
        else:
            # 对于默认配置文件，使用单例模式
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._is_test_instance = False
            return cls._instance
    
    def __init__(self, config_file=None, environment='production'):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._config_path = None
            self._environment = environment
            self._test_config = None
            self.logger = get_logger(self.__class__.__name__)
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

    # 多公司配置支持方法
    def get_companies(self) -> List[Dict[str, Any]]:
        """
        获取配置的公司列表

        Returns:
            List[Dict[str, Any]]: 公司配置列表
        """
        companies = self.get('companies', [])

        # 如果没有配置companies，尝试从旧的stock_code配置创建
        if not companies and self.get('stock_code'):
            stock_code = self.get('stock_code')
            # 尝试获取公司名称
            from src.data.mapping import MappingManager
            try:
                mapping_manager = MappingManager()
                company_name = mapping_manager.get_stock_name(stock_code)
            except:
                company_name = f"股票{stock_code}"

            companies = [{
                'stock_code': stock_code,
                'company_name': company_name,
                'enabled': True,
                'priority': 1,
                'custom_pages': None
            }]

        # 过滤出启用的公司并按优先级排序
        enabled_companies = [c for c in companies if c.get('enabled', True)]
        enabled_companies.sort(key=lambda x: x.get('priority', 1))

        return enabled_companies

    def get_company_config(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取特定公司的配置

        Args:
            stock_code: 股票代码

        Returns:
            Optional[Dict[str, Any]]: 公司配置，如果不存在则返回None
        """
        companies = self.get_companies()
        for company in companies:
            if company.get('stock_code') == stock_code:
                return company
        return None

    def add_company(self, stock_code: str, company_name: str = None, priority: int = 1,
                   enabled: bool = True, custom_pages: List[Dict] = None) -> bool:
        """
        添加公司配置

        Args:
            stock_code: 股票代码
            company_name: 公司名称（可选）
            priority: 优先级（数字越小优先级越高）
            enabled: 是否启用
            custom_pages: 自定义页面配置

        Returns:
            bool: 是否添加成功
        """
        try:
            # 获取现有公司列表
            companies = self.get('companies', [])

            # 检查是否已存在
            for company in companies:
                if company.get('stock_code') == stock_code:
                    self.logger.warning(f"公司 {stock_code} 已存在，将更新配置")
                    # 更新现有配置
                    company.update({
                        'company_name': company_name or company.get('company_name', f"股票{stock_code}"),
                        'priority': priority,
                        'enabled': enabled,
                        'custom_pages': custom_pages
                    })
                    break
            else:
                # 添加新公司
                if not company_name:
                    # 尝试获取公司名称
                    from src.data.mapping import MappingManager
                    try:
                        mapping_manager = MappingManager()
                        company_name = mapping_manager.get_stock_name(stock_code)
                    except:
                        company_name = f"股票{stock_code}"

                companies.append({
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'enabled': enabled,
                    'priority': priority,
                    'custom_pages': custom_pages
                })

            # 保存配置
            self.set('companies', companies)
            self.save_config()

            return True

        except Exception as e:
            self.logger.error(f"添加公司配置失败: {e}")
            return False

    def remove_company(self, stock_code: str) -> bool:
        """
        移除公司配置

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否移除成功
        """
        try:
            companies = self.get('companies', [])
            original_count = len(companies)

            # 过滤掉指定公司
            companies = [c for c in companies if c.get('stock_code') != stock_code]

            if len(companies) == original_count:
                # 没有找到要移除的公司
                self.logger.warning(f"未找到公司 {stock_code}")
                return False

            # 保存配置
            self.set('companies', companies)
            self.save_config()

            return True

        except Exception as e:
            self.logger.error(f"移除公司配置失败: {e}")
            return False

    def enable_company(self, stock_code: str) -> bool:
        """
        启用公司

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否启用成功
        """
        return self._update_company_status(stock_code, True)

    def disable_company(self, stock_code: str) -> bool:
        """
        禁用公司

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否禁用成功
        """
        return self._update_company_status(stock_code, False)

    def _update_company_status(self, stock_code: str, enabled: bool) -> bool:
        """
        更新公司状态

        Args:
            stock_code: 股票代码
            enabled: 是否启用

        Returns:
            bool: 是否更新成功
        """
        try:
            companies = self.get('companies', [])
            updated = False

            for company in companies:
                if company.get('stock_code') == stock_code:
                    company['enabled'] = enabled
                    updated = True
                    break

            if updated:
                self.set('companies', companies)
                self.save_config()

            return updated

        except Exception as e:
            self.logger.error(f"更新公司状态失败: {e}")
            return False

    def get_parallel_download_config(self) -> Dict[str, Any]:
        """
        获取并行下载配置

        Returns:
            Dict[str, Any]: 并行下载配置
        """
        return self.get('parallel_download', {
            'enabled': False,
            'max_workers': 3,
            'batch_size': 50,
            'task_timeout': 300
        })

    def get_proxy_config(self) -> Dict[str, Any]:
        """
        获取代理配置

        Returns:
            Dict[str, Any]: 代理配置
        """
        return self.get('proxy_management', {
            'enabled': False,
            'pools': {}
        })

    def get_anti_crawler_config(self) -> Dict[str, Any]:
        """
        获取反爬虫配置

        Returns:
            Dict[str, Any]: 反爬虫配置
        """
        return self.get('enhanced_anti_crawler', {
            'enabled': True,
            'level': 'high'
        })

    def is_parallel_download_enabled(self) -> bool:
        """
        检查是否启用并行下载

        Returns:
            bool: 是否启用并行下载
        """
        config = self.get_parallel_download_config()
        return config.get('enabled', False)

    def is_proxy_enabled(self) -> bool:
        """
        检查是否启用代理

        Returns:
            bool: 是否启用代理
        """
        config = self.get_proxy_config()
        return config.get('enabled', False)

    def get_max_workers(self) -> int:
        """
        获取最大工作线程数

        Returns:
            int: 最大工作线程数
        """
        config = self.get_parallel_download_config()
        return config.get('max_workers', 3)

    def validate_companies_config(self) -> Tuple[bool, List[str]]:
        """
        验证公司配置

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        companies = self.get_companies()

        if not companies:
            errors.append("没有配置任何公司")
            return False, errors

        stock_codes = set()
        for i, company in enumerate(companies):
            stock_code = company.get('stock_code')

            # 验证股票代码格式
            if not stock_code or not str(stock_code).isdigit() or len(str(stock_code)) != 6:
                errors.append(f"第{i+1}个公司的股票代码格式错误: {stock_code}")

            # 检查重复
            if stock_code in stock_codes:
                errors.append(f"股票代码 {stock_code} 重复配置")
            stock_codes.add(stock_code)

            # 验证优先级
            priority = company.get('priority', 1)
            if not isinstance(priority, int) or priority < 1:
                errors.append(f"公司 {stock_code} 的优先级设置错误: {priority}")

            # 验证自定义页面配置
            custom_pages = company.get('custom_pages')
            if custom_pages is not None:
                if not isinstance(custom_pages, list):
                    errors.append(f"公司 {stock_code} 的custom_pages必须是数组")
                else:
                    for j, page in enumerate(custom_pages):
                        if not isinstance(page, dict):
                            errors.append(f"公司 {stock_code} 的第{j+1}个页面配置格式错误")
                        elif 'suffix' not in page:
                            errors.append(f"公司 {stock_code} 的第{j+1}个页面配置缺少suffix字段")

        return len(errors) == 0, errors

    def get_companies_summary(self) -> Dict[str, Any]:
        """
        获取公司配置摘要

        Returns:
            Dict[str, Any]: 公司配置摘要
        """
        # 获取所有公司（包括禁用的）
        all_companies = self.get('companies', [])
        enabled_companies = self.get_companies()  # 这个方法返回启用的公司

        enabled_count = len(enabled_companies)
        disabled_count = len(all_companies) - enabled_count

        priorities = set()
        for company in all_companies:
            priorities.add(company.get('priority', 1))

        return {
            'total_companies': len(all_companies),
            'enabled_companies': enabled_count,
            'disabled_companies': disabled_count,
            'priority_levels': sorted(priorities),
            'stock_codes': [c.get('stock_code') for c in all_companies],
            'parallel_download_enabled': self.is_parallel_download_enabled(),
            'proxy_enabled': self.is_proxy_enabled(),
            'max_workers': self.get_max_workers()
        }