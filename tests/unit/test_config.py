"""
配置管理单元测试 (Enhanced)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import ConfigError, ConfigManager
from src.core.config_definitions import BrowserConfig, GlobalConfig


class TestConfigManager:
    """测试配置管理器"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"
        # Create empty config file
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({}, f)
        
        # Reset singleton for each test to ensure isolation
        ConfigManager._instance = None
        ConfigManager._config = {}
        ConfigManager._global_config = GlobalConfig()

    def teardown_method(self):
        """每个测试方法后的清理"""
        self.temp_dir.cleanup()

    def test_singleton_pattern(self):
        """测试单例模式"""
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2

    def test_new_instance_with_file(self):
        """测试带文件路径会创建新实例"""
        config1 = ConfigManager()
        config2 = ConfigManager(config_file=str(self.config_path))
        assert config1 is not config2
        assert getattr(config2, "_is_test_instance", False)

    def test_load_valid_config(self):
        """测试加载有效配置"""
        test_config = {
            "browser": {"strategy": "selenium", "headless": False},
            "save_dir": "downloads",
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        config = ConfigManager()
        loaded_config = config.load_config(str(self.config_path))

        assert loaded_config["save_dir"] == "downloads"
        # Test dataclass sync
        assert config.browser_config.strategy == "selenium"
        assert config.browser_config.headless is False

    def test_load_nonexistent_config(self):
        """测试加载不存在的配置文件"""
        config = ConfigManager()

        with pytest.raises(ConfigError) as exc_info:
            config.load_config("nonexistent.json")

        assert "配置文件不存在" in str(exc_info.value)

    def test_load_invalid_json(self):
        """测试加载无效JSON"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("invalid json")

        config = ConfigManager()

        with pytest.raises(ConfigError) as exc_info:
            config.load_config(str(self.config_path))

        assert "配置文件格式错误" in str(exc_info.value)

    def test_get_config_value(self):
        """测试获取配置值"""
        test_config = {
            "browser": {"strategy": "playwright"},
            "pages": [{"name": "调研", "suffix": "research"}],
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(test_config, f)

        config = ConfigManager()
        config.load_config(str(self.config_path))

        assert config.get("browser.strategy") == "playwright"
        assert config.get("pages.0.name") == "调研"
        assert config.get("nonexistent", "default") == "default"

    def test_set_config_value(self):
        """测试设置配置值"""
        config = ConfigManager()
        config.set("test.key", "test_value")
        assert config.get("test.key") == "test_value"
        
        # Test syncing to dataclass
        config.set("browser.timeout", 999)
        assert config.browser_config.timeout == 999

    def test_save_config(self):
        """测试保存配置"""
        config = ConfigManager(config_file=str(self.config_path))
        print(f"DEBUG: Before set: {config._config}")
        config.set("test", "value")
        print(f"DEBUG: After set: {config._config}")
        config.save_config()

        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"DEBUG: File content: {content}")
            f.seek(0)
            saved_config = json.load(f)

        assert saved_config["test"] == "value"

    def test_reset_config(self):
        """测试重置配置"""
        config = ConfigManager()
        config.set("custom", "value")
        config.reset_config()

        # 检查重置后自定义值被清除
        assert config.get("custom") is None
        # 检查默认配置的基本字段存在
        assert config.get("save_dir") == "downloads"

    def test_company_management(self):
        """测试多公司管理功能"""
        config = ConfigManager(config_file=str(self.config_path))
        
        # Add company
        config.add_company("000001", "平安银行", priority=1)
        companies = config.get_companies()
        assert len(companies) == 1
        assert companies[0]["stock_code"] == "000001"
        assert companies[0]["company_name"] == "平安银行"
        
        # Disable company
        config.disable_company("000001")
        assert len(config.get_companies()) == 0  # get_companies returns enabled only
        
        # Enable company
        config.enable_company("000001")
        assert len(config.get_companies()) == 1
        
        # Remove company
        config.remove_company("000001")
        all_companies = config.get("companies", [])
        assert len(all_companies) == 0

    def test_validate_companies_config(self):
        """测试公司配置验证"""
        config = ConfigManager()
        
        # No companies
        valid, errors = config.validate_companies_config()
        assert not valid
        assert "没有配置任何公司" in errors[0]
        
        # Add valid company
        config.add_company("000001", "平安银行")
        valid, errors = config.validate_companies_config()
        assert valid
        
        # Manually inject invalid company
        companies = config.get("companies")
        companies.append({"stock_code": "INVALID"})
        config.set("companies", companies)
        
        valid, errors = config.validate_companies_config()
        assert not valid
        assert "股票代码格式错误" in str(errors)

    def test_load_test_config(self):
        """测试加载测试专用配置"""
        test_conf_path = Path(self.temp_dir.name) / "test_env_config.json"
        with open(test_conf_path, "w", encoding="utf-8") as f:
            json.dump({"test_env": True}, f)
            
        config = ConfigManager()
        loaded = config.load_test_config(str(test_conf_path))
        assert loaded["test_env"] is True
        
        val = config.get_test_config("test_env")
        assert val is True

    def test_use_constants(self):
        """测试常量访问"""
        config = ConfigManager()
        
        # Access base url
        base_url = config.use_constants("base_url")
        assert base_url == "https://www.cninfo.com.cn"
        
        # Access nested constant
        page_load = config.use_constants("timeouts.page_load")
        assert isinstance(page_load, int)
        
        # Access nonexistent
        assert config.use_constants("nonexistent") is None

    def test_get_companies_summary(self):
        """测试获取公司配置摘要"""
        config = ConfigManager(config_file=str(self.config_path))
        config.add_company("000001", "A", enabled=True)
        config.add_company("000002", "B", enabled=False)
        
        summary = config.get_companies_summary()
        assert summary["total_companies"] == 2
        assert summary["enabled_companies"] == 1
        assert summary["disabled_companies"] == 1
        assert "000001" in summary["stock_codes"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])