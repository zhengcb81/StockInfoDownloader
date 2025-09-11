"""
结构化错误日志模块
提供统一的错误记录、分析和监控功能
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from .logger import get_logger
from .exceptions import (
    StockInfoError, ErrorCode, ErrorSeverity, RecoveryStrategy,
    error_handler, ErrorContext
)

logger = get_logger(__name__)

# 错误日志级别枚举
class ErrorLogLevel(Enum):
    """错误日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class ErrorLogEntry:
    """错误日志条目"""
    timestamp: datetime
    error_code: ErrorCode
    severity: ErrorSeverity
    message: str
    module: str
    function: str
    line_number: int
    file_path: str
    recovery_strategy: RecoveryStrategy
    recovery_attempted: bool
    recovery_successful: bool
    context: Dict[str, Any]
    stack_trace: str
    original_exception: Optional[str]
    user_action: Optional[str]
    system_state: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['error_code'] = self.error_code.value
        data['severity'] = self.severity.value
        data['recovery_strategy'] = self.recovery_strategy.value
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

class ErrorLogger:
    """结构化错误日志记录器"""
    
    def __init__(self, 
                 log_dir: str = "logs/errors",
                 max_file_size: int = 50 * 1024 * 1024,  # 50MB
                 max_backup_count: int = 10,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_json: bool = True):
        """
        初始化错误日志记录器
        
        Args:
            log_dir: 日志目录
            max_file_size: 最大文件大小
            max_backup_count: 最大备份文件数量
            enable_console: 是否启用控制台输出
            enable_file: 是否启用文件输出
            enable_json: 是否启用JSON格式输出
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_file_size = max_file_size
        self.max_backup_count = max_backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        
        # 日志文件路径
        self.text_log_path = self.log_dir / "errors.log"
        self.json_log_path = self.log_dir / "errors.json"
        
        # 错误统计
        self.error_counts: Dict[str, int] = {}
        self.recovery_stats: Dict[str, Dict[str, int]] = {}
        
        # 错误模式识别
        self.error_patterns: Dict[str, List[ErrorLogEntry]] = {}
        
        # 初始化
        self._initialize_logger()
    
    def _initialize_logger(self):
        """初始化日志记录器"""
        # 创建基础日志文件
        if self.enable_file and not self.text_log_path.exists():
            self.text_log_path.touch()
            self._write_log_header(self.text_log_path)
        
        if self.enable_json and not self.json_log_path.exists():
            self.json_log_path.touch()
            self._write_json_header()
    
    def _write_log_header(self, file_path: Path):
        """写入日志文件头"""
        header = f"""# StockInfoDownloader 错误日志
# 创建时间: {datetime.now().isoformat()}
# 格式: [时间戳] [错误代码] [严重级别] 模块:函数(行号) 消息
# 
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def _write_json_header(self):
        """写入JSON日志文件头"""
        header_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "description": "StockInfoDownloader 结构化错误日志",
            "entries": []
        }
        with open(self.json_log_path, 'w', encoding='utf-8') as f:
            json.dump(header_data, f, ensure_ascii=False, indent=2)
    
    def log_error(self, error: StockInfoError, 
                  additional_context: Optional[Dict[str, Any]] = None):
        """
        记录错误日志
        
        Args:
            error: 错误对象
            additional_context: 额外上下文信息
        """
        try:
            # 创建错误日志条目
            log_entry = self._create_log_entry(error, additional_context)
            
            # 更新统计信息
            self._update_statistics(log_entry)
            
            # 记录到不同目标
            if self.enable_console:
                self._log_to_console(log_entry)
            
            if self.enable_file:
                self._log_to_text_file(log_entry)
            
            if self.enable_json:
                self._log_to_json_file(log_entry)
            
            # 分析错误模式
            self._analyze_error_pattern(log_entry)
            
        except Exception as e:
            logger.error(f"记录错误日志失败: {e}")
    
    def _create_log_entry(self, error: StockInfoError, 
                         additional_context: Optional[Dict[str, Any]] = None) -> ErrorLogEntry:
        """创建错误日志条目"""
        context = error.context.copy()
        if additional_context:
            context.update(additional_context)
        
        return ErrorLogEntry(
            timestamp=error.timestamp,
            error_code=error.error_code,
            severity=error.severity,
            message=error.message,
            module=error.caller_info.get('module', 'unknown'),
            function=error.caller_info.get('function', 'unknown'),
            line_number=error.caller_info.get('line_number', 0),
            file_path=error.caller_info.get('file_path', 'unknown'),
            recovery_strategy=error.recovery_strategy,
            recovery_attempted=error.error_context.recovery_attempted,
            recovery_successful=error.error_context.recovery_successful,
            context=context,
            stack_trace=error.stack_trace,
            original_exception=str(error.original_exception) if error.original_exception else None,
            user_action=error.context.get('user_action'),
            system_state=error.context.get('system_state')
        )
    
    def _update_statistics(self, log_entry: ErrorLogEntry):
        """更新错误统计信息"""
        error_key = log_entry.error_code.value
        
        # 更新错误计数
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # 更新恢复统计
        if error_key not in self.recovery_stats:
            self.recovery_stats[error_key] = {'attempted': 0, 'successful': 0}
        
        if log_entry.recovery_attempted:
            self.recovery_stats[error_key]['attempted'] += 1
            if log_entry.recovery_successful:
                self.recovery_stats[error_key]['successful'] += 1
    
    def _log_to_console(self, log_entry: ErrorLogEntry):
        """记录到控制台"""
        timestamp = log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        recovery_status = "✓" if log_entry.recovery_successful else "✗"
        
        console_msg = (
            f"[{timestamp}] [{log_entry.error_code.value}] "
            f"[{log_entry.severity.value}] "
            f"{log_entry.module}:{log_entry.function}({log_entry.line_number}) "
            f"{log_entry.message} {recovery_status}"
        )
        
        # 根据严重级别选择输出方式
        if log_entry.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            logger.error(console_msg)
        elif log_entry.severity == ErrorSeverity.ERROR:
            logger.error(console_msg)
        elif log_entry.severity == ErrorSeverity.WARNING:
            logger.warning(console_msg)
        else:
            logger.info(console_msg)
    
    def _log_to_text_file(self, log_entry: ErrorLogEntry):
        """记录到文本文件"""
        timestamp = log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        recovery_status = "SUCCESS" if log_entry.recovery_successful else "FAILED"
        
        log_line = (
            f"[{timestamp}] [{log_entry.error_code.value}] "
            f"[{log_entry.severity.value}] "
            f"{log_entry.module}:{log_entry.function}({log_entry.line_number}) "
            f"{log_entry.message} | Recovery: {recovery_status}"
        )
        
        # 检查文件大小，进行轮转
        self._rotate_log_file(self.text_log_path)
        
        with open(self.text_log_path, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
            
            # 如果有堆栈跟踪，也写入文件
            if log_entry.stack_trace:
                f.write("Stack Trace:\n")
                f.write(log_entry.stack_trace + '\n')
                f.write("-" * 80 + '\n')
    
    def _log_to_json_file(self, log_entry: ErrorLogEntry):
        """记录到JSON文件"""
        # 检查文件大小，进行轮转
        self._rotate_log_file(self.json_log_path)
        
        # 读取现有数据
        try:
            with open(self.json_log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {"entries": []}
        
        # 添加新条目
        data['entries'].append(log_entry.to_dict())
        
        # 写回文件
        with open(self.json_log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _rotate_log_file(self, file_path: Path):
        """轮转日志文件"""
        if not file_path.exists():
            return
        
        try:
            file_size = file_path.stat().st_size
            if file_size >= self.max_file_size:
                # 创建备份文件
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = file_path.with_name(f"{file_path.stem}_{timestamp}{file_path.suffix}")
                
                # 移动当前文件到备份
                file_path.rename(backup_path)
                
                # 创建新文件
                if file_path.suffix == '.json':
                    self._write_json_header()
                else:
                    self._write_log_header(file_path)
                
                # 清理旧备份文件
                self._cleanup_old_backups(file_path)
                
        except Exception as e:
            logger.error(f"轮转日志文件失败: {e}")
    
    def _cleanup_old_backups(self, file_path: Path):
        """清理旧备份文件"""
        try:
            pattern = f"{file_path.stem}_*{file_path.suffix}"
            backup_files = list(file_path.parent.glob(pattern))
            
            # 按修改时间排序
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 删除超出保留数量的文件
            for backup_file in backup_files[self.max_backup_count:]:
                backup_file.unlink()
                
        except Exception as e:
            logger.error(f"清理备份文件失败: {e}")
    
    def _analyze_error_pattern(self, log_entry: ErrorLogEntry):
        """分析错误模式"""
        error_key = f"{log_entry.module}:{log_entry.function}"
        
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = []
        
        # 保持最近100个错误记录
        self.error_patterns[error_key].append(log_entry)
        if len(self.error_patterns[error_key]) > 100:
            self.error_patterns[error_key] = self.error_patterns[error_key][-100:]
    
    def get_error_summary(self, 
                         hours: int = 24,
                         module: Optional[str] = None) -> Dict[str, Any]:
        """
        获取错误摘要
        
        Args:
            hours: 统计时间范围（小时）
            module: 指定模块
            
        Returns:
            错误摘要信息
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 从日志文件读取数据
        recent_errors = self._load_recent_errors(cutoff_time, module)
        
        if not recent_errors:
            return {"total_errors": 0, "time_range": f"Last {hours} hours"}
        
        # 统计信息
        total_errors = len(recent_errors)
        error_codes = {}
        severities = {}
        modules = {}
        recovery_rate = 0
        
        for entry in recent_errors:
            # 错误代码统计
            code = entry['error_code']
            error_codes[code] = error_codes.get(code, 0) + 1
            
            # 严重级别统计
            severity = entry['severity']
            severities[severity] = severities.get(severity, 0) + 1
            
            # 模块统计
            mod = entry['module']
            modules[mod] = modules.get(mod, 0) + 1
            
            # 恢复率统计
            if entry['recovery_attempted']:
                recovery_rate += 1 if entry['recovery_successful'] else 0
        
        total_attempted = sum(1 for e in recent_errors if e['recovery_attempted'])
        recovery_rate = recovery_rate / total_attempted if total_attempted > 0 else 0
        
        return {
            "total_errors": total_errors,
            "time_range": f"Last {hours} hours",
            "error_codes": error_codes,
            "severities": severities,
            "modules": modules,
            "recovery_rate": recovery_rate,
            "most_common_error": max(error_codes.items(), key=lambda x: x[1])[0] if error_codes else None,
            "error_frequency": total_errors / hours if hours > 0 else 0
        }
    
    def _load_recent_errors(self, cutoff_time: datetime, 
                           module: Optional[str] = None) -> List[Dict[str, Any]]:
        """加载最近的错误记录"""
        try:
            if not self.json_log_path.exists():
                return []
            
            with open(self.json_log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = data.get('entries', [])
            recent_errors = []
            
            for entry in entries:
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if entry_time >= cutoff_time:
                    if module is None or entry['module'] == module:
                        recent_errors.append(entry)
            
            return recent_errors
            
        except Exception as e:
            logger.error(f"加载错误记录失败: {e}")
            return []
    
    def get_error_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        获取错误趋势
        
        Args:
            days: 统计天数
            
        Returns:
            错误趋势数据
        """
        trends = {}
        current_date = datetime.now().date()
        
        for i in range(days):
            date = current_date - timedelta(days=i)
            date_str = date.isoformat()
            
            # 计算该日期的错误数量
            day_start = datetime.combine(date, datetime.min.time())
            day_end = datetime.combine(date, datetime.max.time())
            
            day_errors = self._load_recent_errors(day_start)
            day_errors = [e for e in day_errors 
                         if day_start <= datetime.fromisoformat(e['timestamp']) <= day_end]
            
            trends[date_str] = {
                'total_errors': len(day_errors),
                'critical_errors': len([e for e in day_errors if e['severity'] in ['CRITICAL', 'FATAL']]),
                'recovery_rate': self._calculate_recovery_rate(day_errors)
            }
        
        return trends
    
    def _calculate_recovery_rate(self, errors: List[Dict[str, Any]]) -> float:
        """计算恢复率"""
        attempted = [e for e in errors if e['recovery_attempted']]
        if not attempted:
            return 0.0
        
        successful = len([e for e in attempted if e['recovery_successful']])
        return successful / len(attempted)
    
    def get_error_patterns(self, min_occurrences: int = 3) -> Dict[str, Any]:
        """
        获取错误模式
        
        Args:
            min_occurrences: 最小出现次数
            
        Returns:
            错误模式分析结果
        """
        patterns = {}
        
        for location, entries in self.error_patterns.items():
            if len(entries) >= min_occurrences:
                # 分析模式特征
                error_codes = {}
                severities = {}
                
                for entry in entries:
                    code = entry.error_code.value
                    severity = entry.severity.value
                    
                    error_codes[code] = error_codes.get(code, 0) + 1
                    severities[severity] = severities.get(severity, 0) + 1
                
                patterns[location] = {
                    'total_occurrences': len(entries),
                    'most_common_error': max(error_codes.items(), key=lambda x: x[1])[0],
                    'error_distribution': error_codes,
                    'severity_distribution': severities,
                    'recovery_rate': sum(1 for e in entries if e.recovery_successful) / len(entries),
                    'first_occurrence': min(e.timestamp for e in entries).isoformat(),
                    'last_occurrence': max(e.timestamp for e in entries).isoformat()
                }
        
        return patterns
    
    def cleanup_old_logs(self, days: int = 30):
        """
        清理旧日志文件
        
        Args:
            days: 保留天数
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 清理日志文件
            for log_file in self.log_dir.glob("*"):
                if log_file.is_file() and log_file.stat().st_mtime < cutoff_time.timestamp():
                    log_file.unlink()
                    logger.info(f"清理旧日志文件: {log_file.name}")
            
        except Exception as e:
            logger.error(f"清理旧日志文件失败: {e}")
    
    def export_error_report(self, output_path: str, 
                          hours: int = 24,
                          format_type: str = 'json') -> bool:
        """
        导出错误报告
        
        Args:
            output_path: 输出路径
            hours: 统计时间范围
            format_type: 输出格式 ('json' 或 'html')
            
        Returns:
            是否成功
        """
        try:
            summary = self.get_error_summary(hours=hours)
            trends = self.get_error_trends(days=min(7, hours // 24 + 1))
            patterns = self.get_error_patterns()
            
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'summary': summary,
                'trends': trends,
                'patterns': patterns,
                'recommendations': self._generate_recommendations(summary, patterns)
            }
            
            if format_type.lower() == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
            elif format_type.lower() == 'html':
                self._generate_html_report(report_data, output_path)
            
            logger.info(f"错误报告已导出到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出错误报告失败: {e}")
            return False
    
    def _generate_recommendations(self, summary: Dict[str, Any], 
                                 patterns: Dict[str, Any]) -> List[str]:
        """生成错误处理建议"""
        recommendations = []
        
        # 基于错误频率的建议
        if summary.get('error_frequency', 0) > 10:
            recommendations.append("错误频率较高，建议检查系统稳定性和错误处理机制")
        
        # 基于恢复率的建议
        recovery_rate = summary.get('recovery_rate', 0)
        if recovery_rate < 0.5:
            recommendations.append("错误恢复率较低，建议优化错误恢复策略")
        
        # 基于错误模式的建议
        for location, pattern in patterns.items():
            if pattern['recovery_rate'] < 0.3:
                recommendations.append(f"{location} 的错误恢复率较低，需要重点关注")
        
        return recommendations
    
    def _generate_html_report(self, report_data: Dict[str, Any], output_path: str):
        """生成HTML格式报告"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>StockInfoDownloader 错误报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .error-critical {{ color: #d32f2f; }}
                .error-warning {{ color: #f57c00; }}
                .error-info {{ color: #1976d2; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>StockInfoDownloader 错误报告</h1>
                <p>生成时间: {report_data['generated_at']}</p>
            </div>
            
            <div class="section">
                <h2>错误摘要</h2>
                <p>总错误数: {report_data['summary']['total_errors']}</p>
                <p>错误频率: {report_data['summary']['error_frequency']:.2f} 错误/小时</p>
                <p>恢复率: {report_data['summary']['recovery_rate']:.2%}</p>
            </div>
            
            <div class="section">
                <h2>建议</h2>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in report_data['recommendations'])}
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

# 全局错误日志记录器实例
error_logger = ErrorLogger()

# 便捷函数
def log_error(error: StockInfoError, additional_context: Optional[Dict[str, Any]] = None):
    """便捷的错误记录函数"""
    error_logger.log_error(error, additional_context)

def get_error_summary(hours: int = 24, module: Optional[str] = None) -> Dict[str, Any]:
    """便捷的错误摘要函数"""
    return error_logger.get_error_summary(hours, module)

def get_error_trends(days: int = 7) -> Dict[str, Any]:
    """便捷的错误趋势函数"""
    return error_logger.get_error_trends(days)

def export_error_report(output_path: str, hours: int = 24, format_type: str = 'json') -> bool:
    """便捷的错误报告导出函数"""
    return error_logger.export_error_report(output_path, hours, format_type)

# 集成到全局错误处理器
def _integrate_with_error_handler():
    """集成到全局错误处理器"""
    original_log_error = error_handler._log_error
    
    def enhanced_log_error(error: StockInfoError):
        # 调用原始日志记录
        original_log_error(error)
        
        # 记录到结构化错误日志
        log_error(error)
    
    error_handler._log_error = enhanced_log_error

# 自动集成
_integrate_with_error_handler()