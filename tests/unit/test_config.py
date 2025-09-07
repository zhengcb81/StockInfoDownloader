"""
配置管理单元测试
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.core.config import ConfigManager, ConfigError


class TestConfigManager:
    """测试配置管理器"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"
        
    def teardown_method(self):
        """每个测试方法后的清理"""
        self.temp_dir.cleanup()
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2
    
    def test_load_valid_config(self):
        """测试加载有效配置"""
        test_config = {
            "stock_code": "002415",
            "save_dir": "downloads",
            "headless": True
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        config = ConfigManager()
        loaded_config = config.load_config(str(self.config_path))
        
        assert loaded_config["stock_code"] == "002415"
        assert loaded_config["save_dir"] == "downloads"
        assert loaded_config["headless"] is True
    
    def test_load_nonexistent_config(self):
        """测试加载不存在的配置文件"""
        config = ConfigManager()
        
        with pytest.raises(ConfigError) as exc_info:
            config.load_config("nonexistent.json")
        
        assert "配置文件不存在" in str(exc_info.value)
    
    def test_load_invalid_json(self):
        """测试加载无效JSON"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write("invalid json")
        
        config = ConfigManager()
        
        with pytest.raises(ConfigError) as exc_info:
            config.load_config(str(self.config_path))
        
        assert "配置文件格式错误" in str(exc_info.value)
    
    def test_get_config_value(self):
        """测试获取配置值"""
        test_config = {
            "stock_code": "002415",
            "pages": [
                {"name": "调研", "suffix": "research"}
            ]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        config = ConfigManager()
        config.load_config(str(self.config_path))
        
        assert config.get("stock_code") == "002415"
        assert config.get("pages.0.name") == "调研"
        assert config.get("nonexistent", "default") == "default"
    
    def test_set_config_value(self):
        """测试设置配置值"""
        config = ConfigManager()
        config.set("test.key", "test_value")
        
        assert config.get("test.key") == "test_value"
    
    def test_save_config(self):
        """测试保存配置"""
        config = ConfigManager()
        config.set("test", "value")
        
        config.save_config(str(self.config_path))
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        assert saved_config["test"] == "value"
    
    def test_reset_config(self):
        """测试重置配置"""
        config = ConfigManager()
        config.set("custom", "value")
        config.reset_config()
        
        assert config.get("stock_code") == "300470"  # 默认值
        assert config.get("custom") is None
    
    def test_get_default_config(self):
        """测试获取默认配置"""
        config = ConfigManager()
        default_config = config.get_default_config()
        
        assert "stock_code" in default_config
        assert "save_dir" in default_config
        assert "headless" in default_config
        assert isinstance(default_config["pages"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])