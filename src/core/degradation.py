"""
优雅降级策略模块
提供网络和文件系统错误的优雅降级处理机制
"""

import os
import time
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from .exceptions import (
    NetworkError, NetworkTimeoutError, FileSystemError, FilePermissionError,
    ErrorCode, ErrorSeverity, RecoveryStrategy, StockInfoError,
    with_error_handling, handle_error
)
from .logger import get_logger

logger = get_logger(__name__)

@dataclass
class DegradationLevel:
    """降级级别"""
    name: str
    priority: int  # 优先级，数字越小优先级越高
    description: str
    is_available: bool = True
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 3
    cooldown_period: timedelta = timedelta(minutes=5)

# 定义降级级别
DEGRADATION_LEVELS = {
    'full': DegradationLevel(
        name='full',
        priority=1,
        description='完整功能',
        is_available=True,
        max_consecutive_failures=5,
        cooldown_period=timedelta(minutes=1)
    ),
    'cache_only': DegradationLevel(
        name='cache_only',
        priority=2,
        description='仅使用缓存',
        is_available=True,
        max_consecutive_failures=3,
        cooldown_period=timedelta(minutes=2)
    ),
    'offline_mode': DegradationLevel(
        name='offline_mode',
        priority=3,
        description='离线模式',
        is_available=True,
        max_consecutive_failures=5,
        cooldown_period=timedelta(minutes=5)
    ),
    'minimal': DegradationLevel(
        name='minimal',
        priority=4,
        description='最小功能',
        is_available=True,
        max_consecutive_failures=10,
        cooldown_period=timedelta(minutes=10)
    ),
    'emergency': DegradationLevel(
        name='emergency',
        priority=5,
        description='紧急模式',
        is_available=True,
        max_consecutive_failures=20,
        cooldown_period=timedelta(minutes=30)
    )
}

class NetworkDegradationManager:
    """网络降级管理器"""
    
    def __init__(self):
        self.current_level = DEGRADATION_LEVELS['full']
        self.connection_history: List[Dict[str, Any]] = []
        self.fallback_strategies: Dict[str, Callable] = {}
        self.circuit_breaker_open = False
        self.circuit_breaker_timeout = None
        self.max_history_size = 100
        
        # 注册默认的降级策略
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认降级策略"""
        self.fallback_strategies = {
            'timeout_increase': self._increase_timeout,
            'cache_fallback': self._use_cache_data,
            'retry_with_backoff': self._retry_with_exponential_backoff,
            'alternative_endpoint': self._use_alternative_endpoint,
            'offline_mode': self._switch_to_offline_mode
        }
    
    def check_network_health(self) -> bool:
        """
        检查网络健康状态
        
        Returns:
            bool: 网络是否健康
        """
        try:
            import requests
            
            # 测试基本连接
            test_urls = [
                'https://www.cninfo.com.cn',
                'https://www.baidu.com',
                'https://www.google.com'  # 作为连通性测试
            ]
            
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        self._record_success()
                        return True
                except:
                    continue
            
            self._record_failure()
            return False
            
        except Exception as e:
            logger.warning(f"网络健康检查失败: {e}")
            self._record_failure()
            return False
    
    def _record_success(self):
        """记录成功连接"""
        self.connection_history.append({
            'timestamp': datetime.now(),
            'success': True,
            'response_time': 0.0
        })
        
        # 重置熔断器
        if self.circuit_breaker_open:
            self.circuit_breaker_open = False
            self.circuit_breaker_timeout = None
            logger.info("熔断器已重置")
        
        # 清理历史记录
        self._cleanup_history()
    
    def _record_failure(self):
        """记录连接失败"""
        self.connection_history.append({
            'timestamp': datetime.now(),
            'success': False,
            'error': 'Connection failed'
        })
        
        # 检查是否需要打开熔断器
        self._check_circuit_breaker()
        
        # 调整降级级别
        self._adjust_degradation_level()
        
        # 清理历史记录
        self._cleanup_history()
    
    def _check_circuit_breaker(self):
        """检查熔断器状态"""
        recent_failures = [
            entry for entry in self.connection_history[-10:]
            if not entry['success'] and 
            (datetime.now() - entry['timestamp']).total_seconds() < 300
        ]
        
        if len(recent_failures) >= 5:
            self.circuit_breaker_open = True
            self.circuit_breaker_timeout = datetime.now() + timedelta(minutes=5)
            logger.warning("网络熔断器已打开，将在5分钟后重试")
    
    def _adjust_degradation_level(self):
        """调整降级级别"""
        recent_failures = [
            entry for entry in self.connection_history[-20:]
            if not entry['success']
        ]
        
        failure_rate = len(recent_failures) / min(len(self.connection_history), 20)
        
        # 根据失败率调整降级级别
        if failure_rate >= 0.8:
            self._set_degradation_level('emergency')
        elif failure_rate >= 0.6:
            self._set_degradation_level('minimal')
        elif failure_rate >= 0.4:
            self._set_degradation_level('offline_mode')
        elif failure_rate >= 0.2:
            self._set_degradation_level('cache_only')
        else:
            self._set_degradation_level('full')
    
    def _set_degradation_level(self, level_name: str):
        """设置降级级别"""
        if level_name in DEGRADATION_LEVELS:
            new_level = DEGRADATION_LEVELS[level_name]
            if new_level.priority > self.current_level.priority:
                logger.info(f"网络降级级别已调整为: {level_name}")
                self.current_level = new_level
    
    def _cleanup_history(self):
        """清理历史记录"""
        if len(self.connection_history) > self.max_history_size:
            self.connection_history = self.connection_history[-self.max_history_size:]
    
    def execute_with_fallback(self, 
                            primary_operation: Callable,
                            fallback_strategies: List[str],
                            context: Optional[Dict[str, Any]] = None) -> Any:
        """
        使用降级策略执行操作
        
        Args:
            primary_operation: 主要操作
            fallback_strategies: 降级策略列表
            context: 操作上下文
            
        Returns:
            操作结果
        """
        context = context or {}
        
        # 检查熔断器状态
        if self.circuit_breaker_open:
            if datetime.now() < self.circuit_breaker_timeout:
                raise NetworkError(
                    "网络熔断器已打开，暂时无法执行操作",
                    error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                    severity=ErrorSeverity.WARNING,
                    recovery_strategy=RecoveryStrategy.NONE,
                    context={"circuit_breaker": "open", "timeout": self.circuit_breaker_timeout.isoformat()}
                )
            else:
                # 尝试重置熔断器
                if self.check_network_health():
                    logger.info("熔断器重置成功")
                else:
                    raise NetworkError(
                        "熔断器重置失败，网络仍不可用",
                        error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                        severity=ErrorSeverity.WARNING,
                        recovery_strategy=RecoveryStrategy.NONE,
                        context={"circuit_breaker": "reset_failed"}
                    )
        
        # 尝试主要操作
        try:
            result = primary_operation()
            self._record_success()
            return result
            
        except Exception as e:
            logger.warning(f"主要操作失败: {e}")
            self._record_failure()
            
            # 尝试降级策略
            for strategy_name in fallback_strategies:
                if strategy_name in self.fallback_strategies:
                    try:
                        logger.info(f"尝试降级策略: {strategy_name}")
                        fallback_result = self.fallback_strategies[strategy_name](context)
                        
                        if fallback_result is not None:
                            logger.info(f"降级策略 {strategy_name} 执行成功")
                            return fallback_result
                            
                    except Exception as fallback_error:
                        logger.warning(f"降级策略 {strategy_name} 失败: {fallback_error}")
                        continue
            
            # 所有策略都失败
            raise NetworkError(
                f"所有操作策略都失败，最后错误: {e}",
                error_code=ErrorCode.NETWORK_CONNECTION_ERROR,
                severity=ErrorSeverity.ERROR,
                recovery_strategy=RecoveryStrategy.NONE,
                context={"attempted_strategies": fallback_strategies, "original_error": str(e)}
            )
    
    def _increase_timeout(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """增加超时时间"""
        base_timeout = context.get('timeout', 30)
        new_timeout = min(base_timeout * 2, 300)  # 最大5分钟
        
        logger.info(f"增加超时时间: {base_timeout}s -> {new_timeout}s")
        context['timeout'] = new_timeout
        context['strategy_used'] = 'timeout_increase'
        
        return context
    
    def _use_cache_data(self, context: Dict[str, Any]) -> Optional[Any]:
        """使用缓存数据"""
        cache_key = context.get('cache_key')
        if not cache_key:
            return None
        
        # 这里应该集成缓存系统
        logger.info(f"尝试使用缓存数据: {cache_key}")
        context['strategy_used'] = 'cache_fallback'
        
        # 返回缓存数据或None
        return context.get('cached_data')
    
    def _retry_with_exponential_backoff(self, context: Dict[str, Any]) -> Optional[Any]:
        """指数退避重试"""
        retry_count = context.get('retry_count', 0)
        max_retries = context.get('max_retries', 3)
        
        if retry_count >= max_retries:
            return None
        
        # 计算退避时间
        backoff_time = min(2 ** retry_count, 60)  # 最大60秒
        logger.info(f"指数退避重试: 等待 {backoff_time}s")
        
        time.sleep(backoff_time)
        context['retry_count'] = retry_count + 1
        context['strategy_used'] = 'retry_with_backoff'
        
        return context
    
    def _use_alternative_endpoint(self, context: Dict[str, Any]) -> Optional[Any]:
        """使用备用端点"""
        original_url = context.get('url')
        if not original_url:
            return None
        
        # 这里应该有备用端点的配置
        alternative_endpoints = {
            'https://www.cninfo.com.cn': [
                'https://backup1.cninfo.com.cn',
                'https://backup2.cninfo.com.cn'
            ]
        }
        
        for domain, alternatives in alternative_endpoints.items():
            if domain in original_url:
                for alt_domain in alternatives:
                    alt_url = original_url.replace(domain, alt_domain)
                    logger.info(f"尝试备用端点: {alt_url}")
                    
                    context['url'] = alt_url
                    context['strategy_used'] = 'alternative_endpoint'
                    return context
        
        return None
    
    def _switch_to_offline_mode(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """切换到离线模式"""
        logger.info("切换到离线模式")
        context['strategy_used'] = 'offline_mode'
        context['offline_mode'] = True
        
        return context
    
    def get_network_status(self) -> Dict[str, Any]:
        """获取网络状态"""
        recent_history = self.connection_history[-20:]
        
        if not recent_history:
            return {"status": "unknown", "message": "无历史数据"}
        
        success_count = sum(1 for entry in recent_history if entry['success'])
        success_rate = success_count / len(recent_history)
        
        return {
            "status": "healthy" if success_rate > 0.8 else "degraded" if success_rate > 0.5 else "unhealthy",
            "success_rate": success_rate,
            "current_level": self.current_level.name,
            "circuit_breaker": "open" if self.circuit_breaker_open else "closed",
            "recent_attempts": len(recent_history),
            "successful_attempts": success_count
        }

class FileSystemDegradationManager:
    """文件系统降级管理器"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "stockinfo_downloader"
        self.temp_dir.mkdir(exist_ok=True)
        self.fallback_directories = []
        self.space_thresholds = {
            'minimal': 100 * 1024 * 1024,  # 100MB
            'warning': 500 * 1024 * 1024,   # 500MB
            'critical': 1 * 1024 * 1024 * 1024  # 1GB
        }
        
        # 注册备用目录
        self._register_fallback_directories()
    
    def _register_fallback_directories(self):
        """注册备用目录"""
        # 系统临时目录
        self.fallback_directories.append(Path(tempfile.gettempdir()))
        
        # 用户目录
        import os
        user_dir = Path.home()
        self.fallback_directories.extend([
            user_dir / "Downloads",
            user_dir / "Documents",
            user_dir / "Desktop"
        ])
        
        # 程序目录
        program_dir = Path.cwd()
        self.fallback_directories.append(program_dir / "temp")
    
    def check_disk_space(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        检查磁盘空间
        
        Args:
            path: 检查路径
            
        Returns:
            磁盘空间信息
        """
        try:
            path = Path(path)
            if not path.exists():
                path = path.parent
            
            disk_usage = shutil.disk_usage(path)
            
            space_info = {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent_used': (disk_usage.used / disk_usage.total) * 100,
                'status': 'healthy'
            }
            
            # 根据可用空间设置状态
            if disk_usage.free < self.space_thresholds['minimal']:
                space_info['status'] = 'critical'
            elif disk_usage.free < self.space_thresholds['warning']:
                space_info['status'] = 'warning'
            
            return space_info
            
        except Exception as e:
            logger.error(f"检查磁盘空间失败: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def ensure_directory_exists(self, path: Union[str, Path], 
                               create_fallback: bool = True) -> Path:
        """
        确保目录存在，如果失败则使用备用目录
        
        Args:
            path: 目标路径
            create_fallback: 是否创建备用目录
            
        Returns:
            实际使用的目录路径
        """
        original_path = Path(path)
        
        try:
            # 首先尝试原始路径
            if not original_path.exists():
                original_path.mkdir(parents=True, exist_ok=True)
            
            # 检查写入权限
            test_file = original_path / "test_write.tmp"
            test_file.touch()
            test_file.unlink()
            
            return original_path
            
        except Exception as e:
            logger.warning(f"无法访问原始目录 {original_path}: {e}")
            
            if not create_fallback:
                raise FileSystemError(
                    f"无法访问目录: {original_path}",
                    error_code=ErrorCode.FILE_PERMISSION_ERROR,
                    severity=ErrorSeverity.ERROR,
                    recovery_strategy=RecoveryStrategy.FALLBACK,
                    context={"original_path": str(original_path), "error": str(e)}
                )
            
            # 尝试备用目录
            for fallback_dir in self.fallback_directories:
                try:
                    fallback_path = fallback_dir / original_path.name
                    fallback_path.mkdir(parents=True, exist_ok=True)
                    
                    # 检查写入权限
                    test_file = fallback_path / "test_write.tmp"
                    test_file.touch()
                    test_file.unlink()
                    
                    logger.info(f"使用备用目录: {fallback_path}")
                    return fallback_path
                    
                except Exception as fallback_error:
                    logger.warning(f"备用目录 {fallback_dir} 也不可用: {fallback_error}")
                    continue
            
            # 所有备用目录都失败
            raise FileSystemError(
                f"所有目录都不可用，原始路径: {original_path}",
                error_code=ErrorCode.FILE_PERMISSION_ERROR,
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.NONE,
                context={"original_path": str(original_path), "attempted_fallbacks": [str(d) for d in self.fallback_directories]}
            )
    
    def safe_write_file(self, file_path: Union[str, Path], 
                       content: Union[str, bytes],
                       encoding: str = 'utf-8') -> bool:
        """
        安全写入文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 编码格式
            
        Returns:
            是否成功
        """
        try:
            file_path = Path(file_path)
            
            # 确保目录存在
            directory = self.ensure_directory_exists(file_path.parent)
            actual_path = directory / file_path.name
            
            # 检查磁盘空间
            space_info = self.check_disk_space(directory)
            if space_info['status'] == 'critical':
                logger.warning("磁盘空间严重不足")
                return False
            
            # 原子写入：先写入临时文件，然后重命名
            temp_path = actual_path.with_suffix(actual_path.suffix + '.tmp')
            
            if isinstance(content, str):
                with open(temp_path, 'w', encoding=encoding) as f:
                    f.write(content)
            else:
                with open(temp_path, 'wb') as f:
                    f.write(content)
            
            # 重命名到目标位置
            temp_path.replace(actual_path)
            
            logger.info(f"文件写入成功: {actual_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件写入失败: {e}")
            return False
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        清理临时文件
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # 清理主临时目录
            self._cleanup_directory(self.temp_dir, cutoff_time)
            
            # 清理备用目录中的临时文件
            for fallback_dir in self.fallback_directories:
                if fallback_dir.exists():
                    temp_files = fallback_dir.glob("*.tmp")
                    for temp_file in temp_files:
                        try:
                            if temp_file.stat().st_mtime < cutoff_time.timestamp():
                                temp_file.unlink()
                                logger.info(f"清理临时文件: {temp_file}")
                        except Exception as e:
                            logger.warning(f"清理临时文件失败 {temp_file}: {e}")
                            
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")
    
    def _cleanup_directory(self, directory: Path, cutoff_time: datetime):
        """清理指定目录"""
        if not directory.exists():
            return
        
        for file_path in directory.glob("*"):
            try:
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.info(f"清理文件: {file_path}")
                elif file_path.is_dir():
                    # 递归清理子目录
                    self._cleanup_directory(file_path, cutoff_time)
                    # 如果目录为空，删除目录
                    try:
                        if not any(file_path.iterdir()):
                            file_path.rmdir()
                            logger.info(f"清理空目录: {file_path}")
                    except:
                        pass
            except Exception as e:
                logger.warning(f"清理失败 {file_path}: {e}")

# 全局实例
network_degradation_manager = NetworkDegradationManager()
file_system_degradation_manager = FileSystemDegradationManager()

# 便捷函数
def execute_with_network_fallback(primary_operation: Callable,
                                 fallback_strategies: List[str],
                                 context: Optional[Dict[str, Any]] = None) -> Any:
    """便捷的网络降级执行函数"""
    return network_degradation_manager.execute_with_fallback(
        primary_operation, fallback_strategies, context
    )

def ensure_directory_exists(path: Union[str, Path], 
                          create_fallback: bool = True) -> Path:
    """便捷的目录确保函数"""
    return file_system_degradation_manager.ensure_directory_exists(path, create_fallback)

def safe_write_file(file_path: Union[str, Path], 
                   content: Union[str, bytes],
                   encoding: str = 'utf-8') -> bool:
    """便捷的安全文件写入函数"""
    return file_system_degradation_manager.safe_write_file(file_path, content, encoding)

def get_network_status() -> Dict[str, Any]:
    """便捷的网络状态获取函数"""
    return network_degradation_manager.get_network_status()

def check_disk_space(path: Union[str, Path]) -> Dict[str, Any]:
    """便捷的磁盘空间检查函数"""
    return file_system_degradation_manager.check_disk_space(path)