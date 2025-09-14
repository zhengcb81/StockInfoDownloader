"""
字符串操作性能优化模块
提供高效的字符串处理功能，替代低效的正则表达式和多次replace操作
"""

import re
from typing import Optional, List, Dict, Any
from functools import lru_cache

from src.core.logger import get_logger


class StringOptimizer:
    """字符串操作优化器"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # 预编译常用的正则表达式模式
        self._compile_patterns()

        # 创建字符转换表
        self._create_translation_tables()

        self.logger.info("字符串优化器初始化完成")

    def _compile_patterns(self):
        """预编译正则表达式模式"""
        # 文件名和路径相关模式
        self.patterns = {
            # 文件名非法字符
            'filename_chars': re.compile(r'[\\/:*?"<>|]'),
            'path_separator': re.compile(r'[\\\/]+'),

            # 股票代码验证
            'stock_code': re.compile(r'^\d{6}$'),
            'org_id': re.compile(r'^99\d{8}$'),

            # 公司名称验证
            'company_name': re.compile(r'^[\u4e00-\u9fa5a-zA-Z0-9\s\(\)（）\-\.·]+$'),

            # 分页信息提取
            'pagination_current': re.compile(r'(\d+)\s*/\s*(\d+)'),
            'pagination_total': re.compile(r'共\s*(\d+)\s*页'),

            # 邮箱和电话验证
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'phone': re.compile(r'^1[3-9]\d{9}$'),
            'phone_with_dash': re.compile(r'^\d{3}-\d{4}-\d{4}$'),

            # URL和路径处理
            'windows_path': re.compile(r'[A-Za-z]:\\[^\\]+\\'),
            'unix_path': re.compile(r'/[^/\s]+/[^/\s]+/'),

            # 文本清理
            'whitespace': re.compile(r'\s+'),
            'control_chars': re.compile(r'[\x00-\x1f\x7f-\x9f]'),

            # 日期时间模式
            'date_cn': re.compile(r'\d{4}年\d{1,2}月\d{1,2}日'),
            'date_std': re.compile(r'\d{4}-\d{1,2}-\d{1,2}'),
            'time_std': re.compile(r'\d{1,2}:\d{2}:\d{2}'),
        }

        self.logger.debug(f"预编译了 {len(self.patterns)} 个正则表达式模式")

    def _create_translation_tables(self):
        """创建字符转换表"""
        # 文件名安全字符转换表
        translation_map = {
            ord('/'): ord('_'), ord('\\'): ord('_'), ord(':'): ord('_'),
            ord('*'): ord('_'), ord('?'): ord('_'), ord('"'): ord('_'),
            ord('<'): ord('_'), ord('>'): ord('_'), ord('|'): ord('_')
        }
        self.filename_translation = translation_map

        # 路径分隔符统一转换表
        path_translation = {ord('\\'): ord('/')}
        self.path_separator_translation = path_translation

        # 控制字符移除表
        control_chars = ''.join(chr(i) for i in range(32))
        self.control_char_translation = str.maketrans('', '', control_chars)

        # 危险路径字符转换表
        self.dangerous_path_translation = str.maketrans('', '', '')

        self.logger.debug("创建了字符转换表")

    def sanitize_filename(self, filename: str, replacement: str = '_') -> str:
        """
        高效的文件名清理函数

        Args:
            filename: 原始文件名
            replacement: 替换字符，默认为'_'

        Returns:
            str: 清理后的安全文件名
        """
        if not filename:
            return "unnamed"

        # 使用转换表快速替换字符
        sanitized = filename.translate(self.filename_translation)

        # 处理连续的下划线
        if replacement == '_':
            sanitized = self.patterns['path_separator'].sub('_', sanitized)

        # 移除首尾的特殊字符
        sanitized = sanitized.strip('._- ')

        # 限制长度
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip('._- ')

        # 确保不为空
        if not sanitized:
            return "unnamed"

        return sanitized

    def standardize_stock_code(self, stock_code: str) -> Optional[str]:
        """
        标准化股票代码

        Args:
            stock_code: 原始股票代码

        Returns:
            Optional[str]: 标准化后的6位股票代码，无效则返回None
        """
        if not stock_code:
            return None

        # 快速清理
        cleaned = stock_code.strip().upper()

        # 移除非数字字符
        cleaned = ''.join(c for c in cleaned if c.isdigit())

        # 补零到6位
        if len(cleaned) == 6:
            return cleaned
        elif len(cleaned) < 6:
            return cleaned.zfill(6)
        else:
            return None

    def normalize_whitespace(self, text: str) -> str:
        """
        标准化空白字符

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        if not text:
            return ""

        # 使用预编译模式
        return self.patterns['whitespace'].sub(' ', text).strip()

    def clean_text_content(self, text: str) -> str:
        """
        清理文本内容，移除控制字符和多余空白

        Args:
            text: 原始文本

        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""

        # 移除控制字符
        cleaned = text.translate(self.control_char_translation)

        # 标准化空白字符
        cleaned = self.normalize_whitespace(cleaned)

        return cleaned

    def extract_pagination_info(self, text: str) -> Dict[str, Optional[int]]:
        """
        提取分页信息

        Args:
            text: 包含分页信息的文本

        Returns:
            Dict[str, Optional[int]]: 分页信息字典
        """
        result = {'current': None, 'total': None}

        if not text:
            return result

        # 提取当前页/总页
        current_match = self.patterns['pagination_current'].search(text)
        if current_match:
            result['current'] = int(current_match.group(1))
            result['total'] = int(current_match.group(2))

        # 如果没找到，尝试提取总页数
        if result['total'] is None:
            total_match = self.patterns['pagination_total'].search(text)
            if total_match:
                result['total'] = int(total_match.group(1))

        return result

    def validate_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码格式

        Args:
            stock_code: 股票代码

        Returns:
            bool: 是否有效
        """
        if not stock_code:
            return False

        standardized = self.standardize_stock_code(stock_code)
        return standardized is not None and self.patterns['stock_code'].match(standardized) is not None

    def validate_org_id(self, org_id: str) -> bool:
        """
        验证机构ID格式

        Args:
            org_id: 机构ID

        Returns:
            bool: 是否有效
        """
        if not org_id:
            return False

        cleaned = org_id.strip()
        return self.patterns['org_id'].match(cleaned) is not None

    def validate_company_name(self, name: str) -> bool:
        """
        验证公司名称格式

        Args:
            name: 公司名称

        Returns:
            bool: 是否有效
        """
        if not name:
            return False

        cleaned = name.strip()
        return bool(self.patterns['company_name'].match(cleaned))

    def redact_sensitive_paths(self, message: str) -> str:
        """
        脱敏敏感路径信息

        Args:
            message: 原始消息

        Returns:
            str: 脱敏后的消息
        """
        if not message:
            return ""

        # 使用预编译模式进行路径脱敏
        redacted = self.patterns['windows_path'].sub('[REDACTED_PATH]\\', message)
        redacted = self.patterns['unix_path'].sub('[REDACTED_PATH]/', redacted)

        return redacted

    def extract_date_info(self, text: str) -> Dict[str, Optional[str]]:
        """
        提取日期信息

        Args:
            text: 包含日期的文本

        Returns:
            Dict[str, Optional[str]]: 日期信息字典
        """
        result = {'date_cn': None, 'date_std': None, 'time': None}

        if not text:
            return result

        # 提取中文日期
        cn_date_match = self.patterns['date_cn'].search(text)
        if cn_date_match:
            result['date_cn'] = cn_date_match.group()

        # 提取标准日期
        std_date_match = self.patterns['date_std'].search(text)
        if std_date_match:
            result['date_std'] = std_date_match.group()

        # 提取时间
        time_match = self.patterns['time_std'].search(text)
        if time_match:
            result['time'] = time_match.group()

        return result

    def join_text_parts(self, *parts: str) -> str:
        """
        高效的文本部分连接函数

        Args:
            *parts: 文本部分

        Returns:
            str: 连接后的文本
        """
        # 过滤空值
        non_empty_parts = [part.strip() for part in parts if part and part.strip()]

        if not non_empty_parts:
            return ""

        # 直接连接，比多次join调用更高效
        return " ".join(non_empty_parts)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取优化器统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            'compiled_patterns': len(self.patterns),
            'translation_tables': 4,  # filename, path_separator, control_char, dangerous_path
            'available_patterns': list(self.patterns.keys())
        }


# 全局字符串优化器实例
_string_optimizer: Optional[StringOptimizer] = None
_optimizer_lock = None

# 延迟导入锁
try:
    import threading
    _optimizer_lock = threading.Lock()
except ImportError:
    _optimizer_lock = None


def get_string_optimizer() -> StringOptimizer:
    """获取全局字符串优化器实例"""
    global _string_optimizer
    if _string_optimizer is None:
        if _optimizer_lock:
            with _optimizer_lock:
                if _string_optimizer is None:
                    _string_optimizer = StringOptimizer()
        else:
            _string_optimizer = StringOptimizer()
    return _string_optimizer


# 便捷函数
def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """便捷函数：清理文件名"""
    return get_string_optimizer().sanitize_filename(filename, replacement)


def standardize_stock_code(stock_code: str) -> Optional[str]:
    """便捷函数：标准化股票代码"""
    return get_string_optimizer().standardize_stock_code(stock_code)


def normalize_whitespace(text: str) -> str:
    """便捷函数：标准化空白字符"""
    return get_string_optimizer().normalize_whitespace(text)


def clean_text_content(text: str) -> str:
    """便捷函数：清理文本内容"""
    return get_string_optimizer().clean_text_content(text)


def validate_stock_code(stock_code: str) -> bool:
    """便捷函数：验证股票代码"""
    return get_string_optimizer().validate_stock_code(stock_code)


def validate_org_id(org_id: str) -> bool:
    """便捷函数：验证机构ID"""
    return get_string_optimizer().validate_org_id(org_id)