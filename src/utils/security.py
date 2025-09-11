#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
安全工具模块
提供路径净化、输入验证和其他安全功能
"""

import os
import re
import string
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

def sanitize_filename(filename: str) -> str:
    """
    净化文件名，移除危险字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 安全的文件名
    """
    # 移除路径分隔符
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # 移除其他危险字符
    dangerous_chars = ['..', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(c for c in filename if ord(c) >= 32)
    
    # 确保文件名不为空
    if not filename.strip():
        filename = "unnamed_file"
    
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename.strip()

def safe_join_path(base_path: str, *path_parts: str) -> str:
    """
    安全地连接路径，防止目录遍历攻击
    
    Args:
        base_path: 基础路径
        path_parts: 要连接的路径部分
        
    Returns:
        str: 安全的完整路径
    """
    # 确保基础路径是绝对路径
    base_path = os.path.abspath(base_path)
    
    # 净化每个路径部分
    safe_parts = []
    for part in path_parts:
        # 移除危险字符
        safe_part = sanitize_filename(part)
        safe_parts.append(safe_part)
    
    # 构建完整路径
    full_path = os.path.join(base_path, *safe_parts)
    
    # 规范化路径并检查是否仍在基础路径内
    full_path = os.path.abspath(full_path)
    
    # 检查路径遍历攻击
    if not full_path.startswith(os.path.abspath(base_path)):
        raise ValueError(f"Path traversal attempt detected: {full_path}")
    
    return full_path

def validate_stock_code(stock_code: str) -> bool:
    """
    验证股票代码格式
    
    Args:
        stock_code: 股票代码
        
    Returns:
        bool: 是否为有效的股票代码格式
    """
    if not stock_code:
        return False
    
    # 移除空格
    stock_code = stock_code.strip()
    
    # 检查是否为6位数字
    return re.match(r'^\d{6}$', stock_code) is not None

def validate_org_id(org_id: str) -> bool:
    """
    验证组织ID格式
    
    Args:
        org_id: 组织ID
        
    Returns:
        bool: 是否为有效的组织ID格式
    """
    if not org_id:
        return False
    
    # 移除空格
    org_id = org_id.strip()
    
    # 检查是否为数字且以99开头（CNInfo模式）
    return re.match(r'^99\d{8}$', org_id) is not None

def sanitize_url(url: str) -> str:
    """
    净化URL，移除危险参数
    
    Args:
        url: 原始URL
        
    Returns:
        str: 安全的URL
    """
    try:
        parsed = urlparse(url)
        
        # 只允许http和https协议
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
        
        # 移除潜在的敏感参数
        safe_query = []
        if parsed.query:
            for param in parsed.query.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    # 跳过可能敏感的参数
                    if key.lower() in ['password', 'token', 'secret', 'key']:
                        continue
                    safe_query.append(f"{key}={value}")
        
        # 重建URL
        safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if safe_query:
            safe_url += "?" + "&".join(safe_query)
        if parsed.fragment:
            safe_url += "#" + parsed.fragment
            
        return safe_url
        
    except Exception as e:
        raise ValueError(f"Invalid URL: {url}") from e

def is_safe_file_content(content: bytes, max_size: int = 10 * 1024 * 1024) -> bool:
    """
    检查文件内容是否安全
    
    Args:
        content: 文件内容
        max_size: 最大允许大小（字节）
        
    Returns:
        bool: 文件内容是否安全
    """
    # 检查文件大小
    if len(content) > max_size:
        return False
    
    # 检查文件签名（魔法数字）
    if len(content) >= 4:
        # 检查常见的危险文件类型
        dangerous_signatures = [
            b'\x4D\x5A',  # PE文件 (EXE/DLL)
            b'\x7F\x45\x4C\x46',  # ELF文件
            b'\x25\x50\x44\x46',  # PDF文件头（可能包含恶意代码）
        ]
        
        for signature in dangerous_signatures:
            if content.startswith(signature):
                return False
    
    return True

def sanitize_log_message(message: str) -> str:
    """
    净化日志消息，移除敏感信息
    
    Args:
        message: 原始日志消息
        
    Returns:
        str: 安全的日志消息
    """
    # 移除文件路径
    message = re.sub(r'[A-Za-z]:\\[^\\]+\\', '[REDACTED_PATH]\\', message)
    message = re.sub(r'/[^/\s]+/[^/\s]+/', '[REDACTED_PATH]/', message)
    
    # 移除潜在的敏感信息
    sensitive_patterns = [
        (r'password=[^&\s]+', 'password=***'),
        (r'token=[^&\s]+', 'token=***'),
        (r'secret=[^&\s]+', 'secret=***'),
        (r'key=[^&\s]+', 'key=***'),
        (r'api_key=[^&\s]+', 'api_key=***'),
    ]
    
    for pattern, replacement in sensitive_patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
    
    return message

def validate_directory_path(path: str, must_exist: bool = True) -> bool:
    """
    验证目录路径是否安全
    
    Args:
        path: 目录路径
        must_exist: 目录是否必须存在
        
    Returns:
        bool: 路径是否安全有效
    """
    try:
        path_obj = Path(path)
        
        # 检查路径遍历
        if '..' in str(path_obj):
            return False
        
        # 检查是否为绝对路径
        if not path_obj.is_absolute():
            return False
        
        # 检查目录是否存在（如果要求）
        if must_exist and not path_obj.exists():
            return False
        
        # 检查是否为目录
        if must_exist and not path_obj.is_dir():
            return False
        
        return True
        
    except Exception:
        return False

class SecurityValidator:
    """安全验证器类"""
    
    def __init__(self):
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'api_key',
            'access_token', 'refresh_token', 'auth_token'
        }
    
    def sanitize_dict(self, data: dict, sensitive_keys: Optional[set] = None) -> dict:
        """
        净化字典，移除敏感字段
        
        Args:
            data: 原始字典
            sensitive_keys: 敏感字段集合
            
        Returns:
            dict: 净化后的字典
        """
        if sensitive_keys is None:
            sensitive_keys = self.sensitive_fields
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        
        return sanitized
    
    def validate_input(self, input_data: str, input_type: str = 'general') -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            input_type: 输入类型 ('general', 'stock_code', 'org_id', 'filename')
            
        Returns:
            bool: 输入是否有效
        """
        if not input_data or not isinstance(input_data, str):
            return False
        
        input_data = input_data.strip()
        
        if input_type == 'stock_code':
            return validate_stock_code(input_data)
        elif input_type == 'org_id':
            return validate_org_id(input_data)
        elif input_type == 'filename':
            return len(input_data) > 0 and len(input_data) <= 255
        else:  # general
            # 基本的安全检查
            dangerous_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
            return not any(danger in input_data.lower() for danger in dangerous_chars)
    
    def is_safe_path_operation(self, path: str, operation: str = 'read') -> bool:
        """
        检查路径操作是否安全
        
        Args:
            path: 文件路径
            operation: 操作类型 ('read', 'write', 'delete')
            
        Returns:
            bool: 操作是否安全
        """
        try:
            path_obj = Path(path)
            
            # 检查路径遍历
            if '..' in str(path_obj):
                return False
            
            # 检查危险扩展名
            dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif']
            if operation == 'write' and path_obj.suffix.lower() in dangerous_extensions:
                return False
            
            # 检查系统目录
            system_dirs = ['C:\\Windows', 'C:\\System', '/etc', '/bin', '/usr/bin']
            if any(str(path_obj).startswith(sys_dir) for sys_dir in system_dirs):
                return False
            
            return True
            
        except Exception:
            return False