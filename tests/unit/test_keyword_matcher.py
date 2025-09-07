"""
关键词匹配器的单元测试
"""

import pytest
from src.utils.keyword_matcher import KeywordMatcher, KeywordConfig


class TestKeywordMatcher:
    """测试关键词匹配器"""
    
    def test_any_mode_matching(self):
        """测试any模式的匹配"""
        config = KeywordConfig(
            allowed_keywords=["投资者关系", "调研"],
            mode="any"
        )
        matcher = KeywordMatcher(config)
        
        # 匹配任意关键词
        assert matcher.matches(text="投资者关系活动记录表", title="调研报告")
        assert matcher.matches(text="投资者关系", title="")
        assert not matcher.matches(text="年度报告", title="财务报告")
    
    def test_all_mode_matching(self):
        """测试all模式的匹配"""
        config = KeywordConfig(
            allowed_keywords=["投资者关系", "调研"],
            mode="all"
        )
        matcher = KeywordMatcher(config)
        
        # 必须匹配所有关键词
        assert matcher.matches(text="投资者关系调研活动", title="")
        assert not matcher.matches(text="投资者关系活动", title="")
        assert not matcher.matches(text="调研活动", title="")
    
    def test_regex_mode_matching(self):
        """测试regex模式的匹配"""
        config = KeywordConfig(
            allowed_keywords=[r"投资者.*调研", r"关系.*活动"],
            mode="regex"
        )
        matcher = KeywordMatcher(config)
        
        # 正则表达式匹配
        assert matcher.matches(text="投资者关系调研活动", title="")
        assert matcher.matches(text="投资者和调研活动", title="")
        assert not matcher.matches(text="年度调研报告", title="")
    
    def test_exclude_keywords(self):
        """测试排除关键词"""
        config = KeywordConfig(
            allowed_keywords=["投资者关系"],
            exclude_keywords=["更正"]
        )
        matcher = KeywordMatcher(config)
        
        # 排除关键词测试
        assert matcher.matches(text="投资者关系活动", title="")
        assert not matcher.matches(text="投资者关系活动更正", title="")
    
    def test_empty_keywords(self):
        """测试空关键词配置"""
        config = KeywordConfig()
        matcher = KeywordMatcher(config)
        
        # 空关键词应该匹配所有内容
        assert matcher.matches(text="任何内容", title="")
        assert matcher.matches(text="", title="")
    
    def test_case_insensitive_matching(self):
        """测试大小写不敏感匹配"""
        config = KeywordConfig(
            allowed_keywords=["Investor"],
            mode="any"
        )
        matcher = KeywordMatcher(config)
        
        assert matcher.matches(text="INVESTOR Relations", title="")
        assert matcher.matches(text="investor relations", title="")
        assert matcher.matches(text="Investor Relations", title="")
    
    def test_multi_field_matching(self):
        """测试多字段匹配"""
        config = KeywordConfig(
            allowed_keywords=["调研"],
            fields=["title", "content", "date"]
        )
        matcher = KeywordMatcher(config)
        
        # 测试不同字段的匹配
        assert matcher.matches(text="", title="调研活动", date="2024-01-01")
        assert matcher.matches(text="调研报告", title="", date="")
        assert matcher.matches(text="", title="", date="调研日期")
        assert not matcher.matches(text="年度报告", title="财务", date="2024-01-01")
    
    def test_from_dict_creation(self):
        """测试从字典创建匹配器"""
        config_dict = {
            "allowed_keywords": ["调研", "投资者关系"],
            "exclude_keywords": ["更正"],
            "allowed_keywords_mode": "any"
        }
        
        matcher = KeywordMatcher.from_dict(config_dict)
        assert matcher.config.allowed_keywords == ["调研", "投资者关系"]
        assert matcher.config.exclude_keywords == ["更正"]
        assert matcher.config.mode == "any"
    
    def test_invalid_regex_handling(self):
        """测试无效正则表达式的处理"""
        config = KeywordConfig(
            allowed_keywords=["[invalid"],
            mode="regex"
        )
        matcher = KeywordMatcher(config)
        
        # 无效正则应该返回False而不是抛出异常
        result = matcher.matches(text="测试文本")
        assert isinstance(result, bool)
    
    def test_validate_keywords(self):
        """测试关键词验证"""
        # 有效的正则表达式
        config = KeywordConfig(
            allowed_keywords=[r"\d+", r"[a-z]+"],
            mode="regex"
        )
        matcher = KeywordMatcher(config)
        assert matcher.validate_keywords() is True
        
        # 无效的正则表达式
        config = KeywordConfig(
            allowed_keywords=[r"[invalid"],
            mode="regex"
        )
        matcher = KeywordMatcher(config)
        assert matcher.validate_keywords() is False