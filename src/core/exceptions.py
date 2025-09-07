"""
自定义异常类
"""

class StockInfoError(Exception):
    """基础异常类"""
    pass

class WebDriverError(StockInfoError):
    """WebDriver相关异常"""
    pass

class ConfigError(StockInfoError):
    """配置相关异常"""
    pass

class DownloadError(StockInfoError):
    """下载相关异常"""
    pass

class OrgIdError(StockInfoError):
    """组织ID获取异常"""
    pass