"""
Enhanced Data Validation Module
Provides comprehensive data validation and cleaning functionality
"""

import re
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse

from .security import validate_stock_code, validate_org_id, sanitize_filename
from .string_optimizer import get_string_optimizer
from ..core.exceptions import (
    ValidationError, ErrorCode, ErrorSeverity, RecoveryStrategy,
    with_error_handling, handle_error
)


class DataValidator:
    """Enhanced Data Validator"""
    
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
        Generic validation method
        
        Args:
            data: Data to validate
            validation_type: Type of validation
            **kwargs: Validation parameters
            
        Returns:
            Tuple[bool, Any]: (is_valid, validated_data or error_info)
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
        """Enhanced stock code validation"""
        if allow_empty and not stock_code:
            return ""
        
        if not stock_code:
            raise ValidationError(
                "Stock code cannot be empty",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_EMPTY,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"validation_type": "stock_code", "allow_empty": allow_empty}
            )
        
        # Basic format validation
        if not validate_stock_code(stock_code):
            raise ValidationError(
                "Invalid stock code format, must be 6 digits",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_FORMAT,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "validation_type": "stock_code"}
            )
        
        # Check if valid A-share range
        try:
            code_int = int(stock_code)
        except ValueError:
            raise ValidationError(
                "Stock code must be numeric",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_FORMAT,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "validation_type": "stock_code"}
            )
        
        valid_ranges = [
            (600000, 601999),  # Shanghai Main Board
            (688000, 688999),  # Star Market
            (0, 2999),        # Shenzhen Main Board
            (300000, 300999),  # ChiNext
        ]
        
        if not any(start <= code_int <= end for start, end in valid_ranges):
            raise ValidationError(
                "Stock code out of valid A-share ranges",
                error_code=ErrorCode.VALIDATION_STOCK_CODE_RANGE,
                severity=ErrorSeverity.WARNING,
                recovery_strategy=RecoveryStrategy.SKIP,
                context={"stock_code": stock_code, "code_int": code_int, "valid_ranges": valid_ranges}
            )
        
        # Check existence if requested
        if check_existence:
            # Basic existence check: ensure 6 digits
            if not (stock_code.isdigit() and len(stock_code) == 6):
                raise ValidationError(
                    f"Stock code not found or invalid: {stock_code}",
                    error_code=ErrorCode.VALIDATION_STOCK_CODE_NOT_FOUND,
                    severity=ErrorSeverity.WARNING,
                    recovery_strategy=RecoveryStrategy.SKIP
                )
        
        return stock_code.strip()
    
    def _validate_org_id_enhanced(self, org_id: str, 
                                allow_empty: bool = False,
                                check_format: bool = True) -> str:
        """Enhanced org ID validation"""
        if allow_empty and not org_id:
            return ""
        
        if not org_id:
            raise ValidationError("Org ID cannot be empty")
        
        # Basic format validation
        if check_format and not validate_org_id(org_id):
            raise ValidationError("Invalid org ID format, must be 10 digits starting with 99")
        
        # Length validation
        if len(org_id.strip()) != 10:
            raise ValidationError("Org ID length must be 10")
        
        # Numeric validation
        if not org_id.strip().isdigit():
            raise ValidationError("Org ID must be numeric")
        
        return org_id.strip()
    
    def _validate_company_name(self, name: str, 
                             min_length: int = 2,
                             max_length: int = 50,
                             allow_empty: bool = False) -> str:
        """Company name validation"""
        if allow_empty and not name:
            return ""
        
        if not name:
            raise ValidationError("Company name cannot be empty")
        
        name = name.strip()
        
        # Length validation
        if len(name) < min_length:
            raise ValidationError(f"Company name length cannot be less than {min_length}")
        if len(name) > max_length:
            raise ValidationError(f"Company name length cannot exceed {max_length}")
        
        # Special character validation
        forbidden_chars = ['<', '>', '"', "'", '&', 'script', 'javascript']
        name_lower = name.lower()
        for char in forbidden_chars:
            if char in name_lower:
                raise ValidationError(f"Company name contains forbidden character: {char}")
        
        # Basic format validation
        if not get_string_optimizer().validate_company_name(name):
            raise ValidationError("Invalid company name format")
        
        return name
    
    def _validate_url(self, url: str, 
                    allowed_schemes: List[str] = None,
                    require_https: bool = False,
                    allow_empty: bool = False) -> str:
        """URL validation"""
        if allow_empty and not url:
            return ""
        
        if not url:
            raise ValidationError("URL cannot be empty")
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValidationError("Invalid URL format")
        
        # Scheme validation
        if not parsed.scheme:
            raise ValidationError("URL must contain a scheme")
        
        # Check dangerous schemes
        dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
        if parsed.scheme.lower() in dangerous_schemes:
            raise ValidationError(f"Unsafe URL scheme: {parsed.scheme}")
        
        if allowed_schemes and parsed.scheme not in allowed_schemes:
            raise ValidationError(f"URL scheme not allowed: {allowed_schemes}")
        
        if require_https and parsed.scheme != 'https':
            raise ValidationError("URL must use HTTPS")
        
        # Basic structure validation
        if not parsed.netloc:
            raise ValidationError("URL missing hostname")
        
        return url
    
    def _validate_date(self, date_value: Union[str, date, datetime],
                     format_pattern: str = "%Y-%m-%d",
                     allow_future: bool = False,
                     allow_past: bool = True,
                     allow_empty: bool = False) -> Union[str, date]:
        """Date validation"""
        if allow_empty and not date_value:
            return ""
        
        if not date_value:
            raise ValidationError("Date cannot be empty")
        
        # Convert string to date object
        if isinstance(date_value, str):
            try:
                if format_pattern:
                    parsed_date = datetime.strptime(date_value.strip(), format_pattern).date()
                else:
                    # Try common formats
                    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]
                    parsed_date = None
                    for fmt in formats:
                        try:
                            parsed_date = datetime.strptime(date_value.strip(), fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if not parsed_date:
                        raise ValidationError("Invalid date format")
            except ValueError:
                raise ValidationError("Invalid date format")
        elif isinstance(date_value, datetime):
            parsed_date = date_value.date()
        elif isinstance(date_value, date):
            parsed_date = date_value
        else:
            raise ValidationError("Invalid date type")
        
        # Range validation
        today = date.today()
        if not allow_future and parsed_date > today:
            raise ValidationError("Date cannot be in the future")
        if not allow_past and parsed_date < today:
            raise ValidationError("Date cannot be in the past")
        
        return parsed_date
    
    def _validate_email(self, email: str, allow_empty: bool = False) -> str:
        """Email validation"""
        if allow_empty and not email:
            return ""
        
        if not email:
            raise ValidationError("Email cannot be empty")
        
        email = email.strip()
        
        if not get_string_optimizer().patterns['email'].match(email):
            raise ValidationError("Invalid email format")
        
        return email
    
    def _validate_phone(self, phone: str, 
                       allow_empty: bool = False,
                       country_code: str = "CN") -> str:
        """Phone number validation"""
        if allow_empty and not phone:
            return ""
        
        if not phone:
            raise ValidationError("Phone number cannot be empty")
        
        phone = phone.strip()
        
        if country_code == "CN":
            if not get_string_optimizer().patterns['phone'].match(phone):
                raise ValidationError("Invalid Chinese phone number format")
        else:
            if not get_string_optimizer().patterns['phone_with_dash'].match(phone):
                raise ValidationError("Invalid phone number format")
        
        return phone
    
    def _validate_file_path(self, file_path: str, 
                          must_exist: bool = False,
                          allowed_extensions: List[str] = None,
                          max_size_mb: int = None,
                          allow_empty: bool = False) -> str:
        """File path validation"""
        if allow_empty and not file_path:
            return ""
        
        if not file_path:
            raise ValidationError("File path cannot be empty")
        
        # Sanitize path
        sanitized_path = sanitize_filename(file_path)
        
        # Existence validation
        if must_exist:
            path_obj = Path(sanitized_path)
            if not path_obj.exists():
                raise ValidationError("File does not exist")
            if not path_obj.is_file():
                raise ValidationError("Path is not a file")
        
        # Extension validation
        if allowed_extensions:
            path_obj = Path(sanitized_path)
            if path_obj.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                raise ValidationError(f"File extension not allowed: {allowed_extensions}")
        
        # Size validation
        if max_size_mb and must_exist:
            path_obj = Path(sanitized_path)
            size_mb = path_obj.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                raise ValidationError(f"File size exceeds limit: {max_size_mb}MB")
        
        return sanitized_path
    
    def _validate_directory_path(self, dir_path: str, 
                               must_exist: bool = False,
                               create_if_not_exist: bool = False,
                               allow_empty: bool = False) -> str:
        """Directory path validation"""
        if allow_empty and not dir_path:
            return ""
        
        if not dir_path:
            raise ValidationError("Directory path cannot be empty")
        
        dir_path = dir_path.strip()
        
        try:
            path_obj = Path(dir_path)
            
            # Existence validation
            if must_exist:
                if not path_obj.exists():
                    raise ValidationError("Directory does not exist")
                if not path_obj.is_dir():
                    raise ValidationError("Path is not a directory")
            
            # Create directory
            if create_if_not_exist and not path_obj.exists():
                path_obj.mkdir(parents=True, exist_ok=True)
            
            return str(path_obj.resolve())
            
        except Exception as e:
            raise ValidationError(f"Directory validation failed: {e}")
    
    def _validate_json_data(self, json_data: Union[str, dict], 
                          required_fields: List[str] = None,
                          optional_fields: List[str] = None,
                          allow_empty: bool = False) -> dict:
        """JSON data validation"""
        if allow_empty and not json_data:
            return {}
        
        if not json_data:
            raise ValidationError("JSON data cannot be empty")
        
        # Parse JSON string
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data.strip())
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON format")
        else:
            data = json_data
        
        if not isinstance(data, dict):
            raise ValidationError("JSON data must be a dictionary")
        
        # Required fields validation
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(f"Missing required fields: {missing_fields}")
        
        # Optional fields validation
        if optional_fields:
            for field in optional_fields:
                if field in data and data[field] is None:
                    raise ValidationError(f"Optional field {field} cannot be null")
        
        return data
    
    def _validate_numeric_range(self, value: Union[int, float], 
                              min_val: Union[int, float] = None,
                              max_val: Union[int, float] = None,
                              allow_empty: bool = False) -> Union[int, float]:
        """Numeric range validation"""
        if allow_empty and value is None:
            return None
        
        if value is None:
            raise ValidationError("Value cannot be empty")
        
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Invalid numeric format")
        
        if min_val is not None and num_value < min_val:
            raise ValidationError(f"Value cannot be less than {min_val}")
        
        if max_val is not None and num_value > max_val:
            raise ValidationError(f"Value cannot exceed {max_val}")
        
        return num_value
    
    def _validate_string_length(self, text: str, 
                              min_length: int = 0,
                              max_length: int = None,
                              allow_empty: bool = False,
                              trim_whitespace: bool = True) -> str:
        """String length validation"""
        if allow_empty and not text:
            return ""
        
        if not text:
            raise ValidationError("String cannot be empty")
        
        if trim_whitespace:
            text = text.strip()
        
        if len(text) < min_length:
            raise ValidationError(f"String length cannot be less than {min_length}")
        
        if max_length is not None and len(text) > max_length:
            raise ValidationError(f"String length cannot exceed {max_length}")
        
        return text
    
    def _validate_enum_value(self, value: str, 
                           allowed_values: List[str],
                           case_sensitive: bool = False,
                           allow_empty: bool = False) -> str:
        """Enum value validation"""
        if allow_empty and not value:
            return ""
        
        if not value:
            raise ValidationError("Enum value cannot be empty")
        
        value = str(value).strip()
        
        if not case_sensitive:
            value = value.lower()
            allowed_values = [str(v).lower() for v in allowed_values]
        
        if value not in allowed_values:
            raise ValidationError(f"Value not in allowed range: {allowed_values}")
        
        return value
    
    def validate_batch(self, data_dict: Dict[str, Any], 
                      validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Batch validate data dictionary
        
        Args:
            data_dict: Data dictionary
            validation_rules: Validation rules dictionary
            
        Returns:
            Dict[str, Any]: Validation results dictionary
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


# Global validator instance
data_validator = DataValidator()


def validate_data(data: Any, validation_type: str, **kwargs) -> Tuple[bool, Any]:
    """Helper validation function"""
    return data_validator.validate(data, validation_type, **kwargs)


def validate_batch_data(data_dict: Dict[str, Any], 
                       validation_rules: Dict[str, Dict]) -> Dict[str, Any]:
    """Helper batch validation function"""
    return data_validator.validate_batch(data_dict, validation_rules)