#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强数据验证模块
提供全面的数据验证和清洗功能
"""

import re
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse

from .security import validate_stock_code, validate_org_id, sanitize_filename
from ..core.exceptions import (
    ValidationError, ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)


class DataValidator:
    """增强数据验证器"""
    
    def __init__(self):
        self.validation_rules = {
            'stock_code': self._validate_stock_code_enhanced,
            'org_id': self._validate_org_id_enhanced,
            'company_name': self._validate_company_name,
            'url': self._validate_url,
            'date': self._validate_date,
            'email': self._validate_email,
            'phone': self._validate_phone,
            'file_path': self._validate_file_path,
            'directory_path': self._validate_directory_path,
            'json_data': self._validate_json_data,
            'numeric_range': self._validate_numeric_range,
            'string_length': self._validate_string_length,
            'enum_value': self._validate_enum_value
        }
    
    @with_error_handling(
        error_code=ErrorCode.VALIDATION_INPUT_ERROR,
        severity=ErrorSeverity.WARNING,
        recovery_strategy=RecoveryStrategy.SKIP
    )
    def validate(self, data: Any, validation_type: str, **kwargs) -> Tuple[bool, Any]:
        """
        通用验证方法
        
        Args:
            data: 要验证的数据
            validation_type: 验证类型
            **kwargs: 验证参数
            
        Returns:
            Tuple[bool, Any]: (是否有效, 验证后的数据或错误信息)
        """
        if validation_type not in self.validation_rules:
            return False, ValidationError(
                f"Unsupported validation type: {validation_type}",
                error_code=ErrorCode.VALIDATION_TYPE_NOT_SUPPORTED,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"validation_type": validation_type, "available_types": list(self.validation_rules.keys())}
            )
        
        try:
            validator = self.validation_rules[validation_type]
            validated_data = validator(data, **kwargs)
            return True, validated_data
        except ValidationError as e:
            return False, e
        except Exception as e:
            return False, ValidationError(
                f"Validation error: {e}",
                error_code=ErrorCode.VALIDATION_PROCESSING_ERROR,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"validation_type": validation_type, "data": str(data)[:100]},
                original_exception=e
            )
    
    @with_error_handling(
        error_code=ErrorCode.VALIDATION_STOCK_CODE_ERROR,
        severity=ErrorSeverity.WARNING,
        recovery_strategy=RecoveryStrategy.SKIP
    )
    def _validate_stock_code_enhanced(self, stock_code: str, 
                                    allow_empty: bool = False,
                                    check_existence: bool = False) -> str:
        """增强股票代码验证"""
        if allow_empty and not stock_code:
            return ""
        
        if not stock_code:
            raise ValidationError(
                "股票代码不能为空",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_EMPTY,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"validation_type": "stock_code", "allow_empty": allow_empty}
            )
        
        # 基础格式验证
        if not validate_stock_code(stock_code):
            raise ValidationError(
                "股票代码格式错误，必须为6位数字",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_FORMAT,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "validation_type": "stock_code"}
            )
        
        # 检查是否为有效的A股代码范围
        try:
            code_int = int(stock_code)
        except ValueError:
            raise ValidationError(
                "股票代码必须为数字",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_FORMAT,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "validation_type": "stock_code"}
            )
        
        valid_ranges = [
            (600000, 601999),  # 上海主板
            (688000, 688999),  # 科创板
            (0, 2999),        # 深圳主板 (000000-002999)
            (300000, 300999),  # 创业板
        ]
        
        if not any(start <= code_int <= end for start, end in valid_ranges):
            raise ValidationError(
                "股票代码不在有效的A股代码范围内",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_RANGE,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "code_int": code_int, "valid_ranges": valid_ranges}
            )
        
        # 如果需要检查存在性，这里可以添加数据库或API检查
        if check_existence:
            # TODO: 实现股票代码存在性检查
            pass
        
        return stock_code.strip()
    
    def _validate_org_id_enhanced(self, org_id: str, 
                                allow_empty: bool = False,
                                check_format: bool = True) -> str:
        """增强组织ID验证"""
        if allow_empty and not org_id:
            return ""
        
        if not org_id:
            raise ValidationError("组织ID不能为空")
        
        # 基础格式验证
        if check_format and not validate_org_id(org_id):
            raise ValidationError("组织ID格式错误，必须为10位数字且以99开头")
        
        # 长度验证
        if len(org_id.strip()) != 10:
            raise ValidationError("组织ID长度必须为10位")
        
        # 全数字验证
        if not org_id.strip().isdigit():
            raise ValidationError("组织ID必须全为数字")
        
        return org_id.strip()
    
    def _validate_company_name(self, name: str, 
                             min_length: int = 2,
                             max_length: int = 50,
                             allow_empty: bool = False) -> str:
        """公司名称验证"""
        if allow_empty and not name:
            return ""
        
        if not name:
            raise ValidationError("公司名称不能为空")
        
        name = name.strip()
        
        # 长度验证
        if len(name) < min_length:
            raise ValidationError(f"公司名称长度不能少于{min_length}个字符")
        if len(name) > max_length:
            raise ValidationError(f"公司名称长度不能超过{max_length}个字符")
        
        # 特殊字符验证
        forbidden_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
        name_lower = name.lower()
        for char in forbidden_chars:
            if char in name_lower:
                raise ValidationError(f"公司名称包含非法字符: {char}")
        
        # 基本格式验证（中文、英文、数字、括号等）
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9\s\(\)（）\-\.·]+$', name):
            raise ValidationError("公司名称格式不正确，只能包含中文、英文、数字、括号和常见符号")
        
        return name
    
    def _validate_url(self, url: str, 
                    allowed_schemes: List[str] = None,
                    require_https: bool = False,
                    allow_empty: bool = False) -> str:
        """URL验证"""
        if allow_empty and not url:
            return ""
        
        if not url:
            raise ValidationError("URL不能为空")
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("URL格式错误")
        
        # 协议验证
        if not parsed.scheme:
            raise ValidationError("URL必须包含协议")
        
        # 检查危险协议
        dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
        if parsed.scheme.lower() in dangerous_schemes:
            raise ValidationError(f"URL协议不安全: {parsed.scheme}")
        
        if allowed_schemes and parsed.scheme not in allowed_schemes:
            raise ValidationError(f"URL协议不在允许范围内: {allowed_schemes}")
        
        if require_https and parsed.scheme != 'https':
            raise ValidationError("URL必须使用HTTPS协议")
        
        # 基本结构验证
        if not parsed.netloc:
            raise ValidationError("URL缺少域名")
        
        # 检查URL完整性
        if parsed.scheme and parsed.netloc:
            # 重新构建URL以确保格式正确
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        return url
    
    def _validate_date(self, date_value: Union[str, date, datetime],
                     format_pattern: str = "%Y-%m-%d",
                     allow_future: bool = False,
                     allow_past: bool = True,
                     allow_empty: bool = False) -> Union[str, date]:
        """日期验证"""
        if allow_empty and not date_value:
            return ""
        
        if not date_value:
            raise ValidationError("日期不能为空")
        
        # 转换字符串为日期对象
        if isinstance(date_value, str):
            try:
                if format_pattern:
                    parsed_date = datetime.strptime(date_value.strip(), format_pattern).date()
                else:
                    # 尝试多种常见格式
                    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]
                    parsed_date = None
                    for fmt in formats:
                        try:
                            parsed_date = datetime.strptime(date_value.strip(), fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if not parsed_date:
                        raise ValidationError("日期格式不正确")
            except ValueError as e:
                raise ValidationError("日期格式不正确")
        elif isinstance(date_value, datetime):
            parsed_date = date_value.date()
        elif isinstance(date_value, date):
            parsed_date = date_value
        else:
            raise ValidationError("日期类型不正确")
        
        # 时间范围验证
        today = date.today()
        if not allow_future and parsed_date > today:
            raise ValidationError("日期不能为未来时间")
        if not allow_past and parsed_date < today:
            raise ValidationError("日期不能为过去时间")
        
        return parsed_date
    
    def _validate_email(self, email: str, allow_empty: bool = False) -> str:
        """邮箱验证"""
        if allow_empty and not email:
            return ""
        
        if not email:
            raise ValidationError("邮箱不能为空")
        
        email = email.strip()
        
        # 基本格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError("邮箱格式不正确")
        
        return email
    
    def _validate_phone(self, phone: str, 
                       allow_empty: bool = False,
                       country_code: str = "CN") -> str:
        """电话号码验证"""
        if allow_empty and not phone:
            return ""
        
        if not phone:
            raise ValidationError("电话号码不能为空")
        
        phone = phone.strip()
        
        if country_code == "CN":
            # 中国手机号验证
            pattern = r'^1[3-9]\d{9}$'
            if not re.match(pattern, phone):
                raise ValidationError("手机号码格式不正确")
        else:
            # 国际通用电话号码验证
            pattern = r'^\+?[\d\s\-\(\)]+$'
            if not re.match(pattern, phone):
                raise ValidationError("电话号码格式不正确")
        
        return phone
    
    def _validate_file_path(self, file_path: str, 
                          must_exist: bool = False,
                          allowed_extensions: List[str] = None,
                          max_size_mb: int = None,
                          allow_empty: bool = False) -> str:
        """文件路径验证"""
        if allow_empty and not file_path:
            return ""
        
        if not file_path:
            raise ValidationError("文件路径不能为空")
        
        # 使用安全模块的文件名净化
        sanitized_path = sanitize_filename(file_path)
        
        # 路径存在性验证
        if must_exist:
            path_obj = Path(sanitized_path)
            if not path_obj.exists():
                raise ValidationError("文件不存在")
            if not path_obj.is_file():
                raise ValidationError("路径不是文件")
        
        # 文件扩展名验证
        if allowed_extensions:
            path_obj = Path(sanitized_path)
            if path_obj.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                raise ValidationError(f"文件扩展名不在允许范围内: {allowed_extensions}")
        
        # 文件大小验证
        if max_size_mb and must_exist:
            path_obj = Path(sanitized_path)
            size_mb = path_obj.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                raise ValidationError(f"文件大小超过限制: {max_size_mb}MB")
        
        return sanitized_path
    
    def _validate_directory_path(self, dir_path: str, 
                               must_exist: bool = False,
                               create_if_not_exist: bool = False,
                               allow_empty: bool = False) -> str:
        """目录路径验证"""
        if allow_empty and not dir_path:
            return ""
        
        if not dir_path:
            raise ValidationError("目录路径不能为空")
        
        dir_path = dir_path.strip()
        
        try:
            path_obj = Path(dir_path)
            
            # 路径存在性验证
            if must_exist:
                if not path_obj.exists():
                    raise ValidationError("目录不存在")
                if not path_obj.is_dir():
                    raise ValidationError("路径不是目录")
            
            # 创建目录
            if create_if_not_exist and not path_obj.exists():
                path_obj.mkdir(parents=True, exist_ok=True)
            
            return str(path_obj.resolve())
            
        except Exception as e:
            raise ValidationError(f"目录路径验证失败: {e}")
    
    def _validate_json_data(self, json_data: Union[str, dict], 
                          required_fields: List[str] = None,
                          optional_fields: List[str] = None,
                          allow_empty: bool = False) -> dict:
        """JSON数据验证"""
        if allow_empty and not json_data:
            return {}
        
        if not json_data:
            raise ValidationError("JSON数据不能为空")
        
        # 解析JSON字符串
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data.strip())
            except json.JSONDecodeError:
                raise ValidationError("JSON格式错误")
        else:
            data = json_data
        
        if not isinstance(data, dict):
            raise ValidationError("JSON数据必须是对象格式")
        
        # 必填字段验证
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(f"缺少必填字段: {missing_fields}")
        
        # 可选字段类型验证
        if optional_fields:
            for field in optional_fields:
                if field in data and data[field] is None:
                    raise ValidationError(f"可选字段 {field} 不能为null")
        
        return data
    
    def _validate_numeric_range(self, value: Union[int, float], 
                              min_val: Union[int, float] = None,
                              max_val: Union[int, float] = None,
                              allow_empty: bool = False) -> Union[int, float]:
        """数值范围验证"""
        if allow_empty and value is None:
            return None
        
        if value is None:
            raise ValidationError("数值不能为空")
        
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("数值格式错误")
        
        if min_val is not None and num_value < min_val:
            raise ValidationError(f"数值不能小于 {min_val}")
        
        if max_val is not None and num_value > max_val:
            raise ValidationError(f"数值不能大于 {max_val}")
        
        return num_value
    
    def _validate_string_length(self, text: str, 
                              min_length: int = 0,
                              max_length: int = None,
                              allow_empty: bool = False,
                              trim_whitespace: bool = True) -> str:
        """字符串长度验证"""
        if allow_empty and not text:
            return ""
        
        if not text:
            raise ValidationError("字符串不能为空")
        
        if trim_whitespace:
            text = text.strip()
        
        if len(text) < min_length:
            raise ValidationError(f"字符串长度不能少于 {min_length} 个字符")
        
        if max_length is not None and len(text) > max_length:
            raise ValidationError(f"字符串长度不能超过 {max_length} 个字符")
        
        return text
    
    def _validate_enum_value(self, value: str, 
                           allowed_values: List[str],
                           case_sensitive: bool = False,
                           allow_empty: bool = False) -> str:
        """枚举值验证"""
        if allow_empty and not value:
            return ""
        
        if not value:
            raise ValidationError("枚举值不能为空")
        
        value = str(value).strip()
        
        if not case_sensitive:
            value = value.lower()
            allowed_values = [str(v).lower() for v in allowed_values]
        
        if value not in allowed_values:
            raise ValidationError(f"值不在允许范围内: {allowed_values}")
        
        return value
    
    def validate_batch(self, data_dict: Dict[str, Any], 
                      validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
        """
        批量验证数据字典
        
        Args:
            data_dict: 数据字典
            validation_rules: 验证规则字典
                格式: {
                    'field_name': {
                        'type': 'validation_type',
                        'params': {'param1': 'value1'}
                    }
                }
            
        Returns:
            Dict[str, Any]: 验证结果字典
                格式: {
                    'field_name': {
                        'valid': bool,
                        'value': Any,
                        'error': str or None
                    }
                }
        """
        results = {}
        
        for field_name, rule in validation_rules.items():
            field_value = data_dict.get(field_name)
            validation_type = rule.get('type')
            params = rule.get('params', {})
            
            if validation_type:
                is_valid, result = self.validate(field_value, validation_type, **params)
                results[field_name] = {
                    'valid': is_valid,
                    'value': result if is_valid else field_value,
                    'error': None if is_valid else result
                }
            else:
                results[field_name] = {
                    'valid': True,
                    'value': field_value,
                    'error': None
                }
        
        return results


# 全局验证器实例
data_validator = DataValidator()


def validate_data(data: Any, validation_type: str, **kwargs) -> Tuple[bool, Any]:
    """
    便捷的数据验证函数
    
    Args:
        data: 要验证的数据
        validation_type: 验证类型
        **kwargs: 验证参数
        
    Returns:
        Tuple[bool, Any]: (是否有效, 验证后的数据或错误信息)
    """
    return data_validator.validate(data, validation_type, **kwargs)


def validate_batch_data(data_dict: Dict[str, Any], 
                       validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
    """
    便捷的批量数据验证函数
    
    Args:
        data_dict: 数据字典
        validation_rules: 验证规则字典
        
    Returns:
        Dict[str, Any]: 验证结果字典
    """
    return data_validator.validate_batch(data_dict, validation_rules)