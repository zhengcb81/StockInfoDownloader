"""
关键词匹配工具类
提供灵活的关键词匹配功能，支持多种匹配模式
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KeywordConfig:
    """关键词配置"""

    allowed_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    mode: str = "any"  # any, all, regex
    fields: List[str] = None  # 匹配的字段列表

    def __post_init__(self):
        if self.fields is None:
            self.fields = ["title", "content"]


class KeywordMatcher:
    """关键词匹配器"""

    def __init__(self, config: KeywordConfig):
        self.config = config
        self.compiled_patterns = {}

    def matches(self, text: str, title: str = "", date: str = "") -> bool:
        """
        检查文本是否匹配关键词规则

        Args:
            text: 主要内容文本
            title: 标题文本
            date: 日期文本

        Returns:
            bool: 是否匹配
        """
        if not any([text, title, date]):
            return True

        # 组合所有字段
        combined_text = " ".join([title or "", text or "", date or ""]).lower()

        # 检查排除关键词
        if self._has_exclude_keywords(combined_text):
            return False

        # 检查允许关键词
        return self._matches_allowed_keywords(text, title, date)

    def _has_exclude_keywords(self, text: str) -> bool:
        """检查是否包含排除关键词"""
        if not self.config.exclude_keywords:
            return False

        text_lower = text.lower()
        for keyword in self.config.exclude_keywords:
            if keyword.lower() in text_lower:
                logger.debug(f"排除关键词匹配: {keyword}")
                return True
        return False

    def _matches_allowed_keywords(self, text: str, title: str, date: str) -> bool:
        """检查是否匹配允许关键词"""
        if not self.config.allowed_keywords:
            return True

        if self.config.mode == "regex":
            return self._matches_regex(text, title, date)
        elif self.config.mode == "all":
            return self._matches_all_keywords(text, title, date)
        else:  # any
            return self._matches_any_keyword(text, title, date)

    def _matches_any_keyword(self, text: str, title: str, date: str) -> bool:
        """匹配任意关键词"""
        text = " ".join([text, title, date]).lower()

        for keyword in self.config.allowed_keywords:
            if keyword.lower() in text:
                logger.debug(f"关键词匹配成功: {keyword}")
                return True
        return False

    def _matches_all_keywords(self, text: str, title: str, date: str) -> bool:
        """匹配所有关键词"""
        text = " ".join([text, title, date]).lower()

        for keyword in self.config.allowed_keywords:
            if keyword.lower() not in text:
                return False

        logger.debug("所有关键词匹配成功")
        return True

    def _matches_regex(self, text: str, title: str, date: str) -> bool:
        """使用正则表达式匹配"""
        # 过滤空字符串并去除首尾空格
        parts = [part for part in [text, title, date] if part]
        combined_text = " ".join(parts).strip()

        for pattern in self.config.allowed_keywords:
            try:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.debug(f"正则表达式匹配成功: {pattern}")
                    return True
            except re.error as e:
                logger.warning(f"正则表达式错误: {pattern}, {e}")

        return False

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "KeywordMatcher":
        """从字典创建匹配器"""
        config = KeywordConfig(
            allowed_keywords=config_dict.get("allowed_keywords"),
            exclude_keywords=config_dict.get("exclude_keywords"),
            mode=config_dict.get("allowed_keywords_mode", "any"),
            fields=config_dict.get("keyword_fields", ["title", "content"]),
        )
        return cls(config)

    def validate_keywords(self) -> bool:
        """验证关键词配置是否有效"""
        try:
            if self.config.allowed_keywords and self.config.mode == "regex":
                for pattern in self.config.allowed_keywords:
                    re.compile(pattern)
            return True
        except re.error as e:
            logger.error(f"正则表达式验证失败: {e}")
            return False
