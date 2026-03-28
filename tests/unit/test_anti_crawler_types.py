"""
Anti-Crawler Types Tests
Tests for anti-crawler type definitions and enumerations
"""

import time

import pytest

from src.web.anti_crawler.types import (
    AntiCrawlerLevel,
    BehaviorPattern,
    FingerprintProfile,
    FingerprintType,
)


class TestFingerprintType:
    """FingerprintType enum tests"""

    def test_fingerprint_type_values(self):
        """Test fingerprint type enum values"""
        assert FingerprintType.USER_AGENT.value == "user_agent"
        assert FingerprintType.SCREEN_RESOLUTION.value == "screen_resolution"
        assert FingerprintType.TIMEZONE.value == "timezone"
        assert FingerprintType.LANGUAGE.value == "language"
        assert FingerprintType.PLATFORM.value == "platform"
        assert FingerprintType.HARDWARE_INFO.value == "hardware_info"
        assert FingerprintType.WEBGL_RENDERER.value == "webgl_renderer"
        assert FingerprintType.CANVAS_FINGERPRINT.value == "canvas_fingerprint"
        assert FingerprintType.AUDIO_FINGERPRINT.value == "audio_fingerprint"
        assert FingerprintType.FONT_FINGERPRINT.value == "font_fingerprint"


class TestBehaviorPattern:
    """BehaviorPattern enum tests"""

    def test_behavior_pattern_values(self):
        """Test behavior pattern enum values"""
        assert BehaviorPattern.MOUSE_MOVEMENT.value == "mouse_movement"
        assert BehaviorPattern.SCROLLING.value == "scrolling"
        assert BehaviorPattern.TYPING.value == "typing"
        assert BehaviorPattern.TAB_SWITCHING.value == "tab_switching"
        assert BehaviorPattern.IDLE_TIME.value == "idle_time"
        assert BehaviorPattern.FORM_FILLING.value == "form_filling"
        assert BehaviorPattern.CLICK_PATTERN.value == "click_pattern"
        assert BehaviorPattern.DRAG_DROP.value == "drag_drop"


class TestAntiCrawlerLevel:
    """AntiCrawlerLevel enum tests"""

    def test_anti_crawler_level_values(self):
        """Test anti crawler level enum values"""
        assert AntiCrawlerLevel.LOW.value == "low"
        assert AntiCrawlerLevel.MEDIUM.value == "medium"
        assert AntiCrawlerLevel.HIGH.value == "high"
        assert AntiCrawlerLevel.EXTREME.value == "extreme"


class TestFingerprintProfile:
    """FingerprintProfile dataclass tests"""

    def test_init_minimal(self):
        """Test minimal initialization"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0
        )
        assert profile.profile_id == "test_001"
        assert profile.user_agent == "Mozilla/5.0"
        assert profile.screen_resolution == (1920, 1080)
        assert profile.timezone == "UTC"
        assert profile.language == "en-US"
        assert profile.platform == "Win32"
        assert profile.hardware_concurrency == 8
        assert profile.device_memory == 8.0
        assert profile.webgl_renderer is None
        assert profile.canvas_fingerprint is None
        assert profile.audio_fingerprint is None
        assert profile.font_fingerprint is None
        assert profile.plugins == []
        assert profile.mime_types == []
        assert profile.created_at > 0
        assert profile.last_used is None
        assert profile.usage_count == 0
        assert profile.success_rate == 1.0
        assert profile.blocked_count == 0

    def test_init_full(self):
        """Test full initialization"""
        profile = FingerprintProfile(
            profile_id="test_002",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            webgl_renderer="ANGLE",
            canvas_fingerprint="canvas_123",
            audio_fingerprint="audio_456",
            font_fingerprint="font_789",
            plugins=["pdf", "chrome_pdf"],
            mime_types=["application/pdf"],
            created_at=1000.0,
            last_used=2000.0,
            usage_count=10,
            success_rate=0.9,
            blocked_count=2
        )
        assert profile.webgl_renderer == "ANGLE"
        assert profile.canvas_fingerprint == "canvas_123"
        assert profile.audio_fingerprint == "audio_456"
        assert profile.font_fingerprint == "font_789"
        assert profile.plugins == ["pdf", "chrome_pdf"]
        assert profile.mime_types == ["application/pdf"]
        assert profile.created_at == 1000.0
        assert profile.last_used == 2000.0
        assert profile.usage_count == 10
        assert profile.success_rate == 0.9
        assert profile.blocked_count == 2

    def test_mark_used_success(self):
        """Test mark_used with success"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            usage_count=5,
            success_rate=0.8
        )

        initial_time = time.time()
        profile.mark_used(success=True)

        assert profile.last_used >= initial_time
        assert profile.usage_count == 6
        # Success rate: (0.8 * 5 + 1) / 6 = 5.0 / 6 ≈ 0.833
        assert 0.82 < profile.success_rate < 0.85
        assert profile.blocked_count == 0

    def test_mark_used_failure(self):
        """Test mark_used with failure"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            usage_count=5,
            success_rate=0.8
        )

        profile.mark_used(success=False)

        assert profile.last_used is not None
        assert profile.usage_count == 6
        # Success rate: (0.8 * 5) / 6 = 4.0 / 6 ≈ 0.667
        assert 0.66 < profile.success_rate < 0.68
        assert profile.blocked_count == 1

    def test_is_suspicious_low_success_rate(self):
        """Test is_suspicious with low success rate"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            success_rate=0.25
        )
        assert profile.is_suspicious is True

    def test_is_suspicious_high_blocked_count(self):
        """Test is_suspicious with high blocked count"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            blocked_count=6
        )
        assert profile.is_suspicious is True

    def test_is_suspicious_high_usage_count(self):
        """Test is_suspicious with high usage count"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            usage_count=101
        )
        assert profile.is_suspicious is True

    def test_is_suspicious_not_suspicious(self):
        """Test is_suspicious with good profile"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            usage_count=10,
            success_rate=0.9,
            blocked_count=0
        )
        assert profile.is_suspicious is False

    def test_score_initial(self):
        """Test score calculation for new profile"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0
        )
        # New profile should have score close to 100
        assert 90 < profile.score <= 100

    def test_score_with_usage_impact(self):
        """Test score calculation with usage impact"""
        # Moderate usage (10-50) should increase score
        profile_moderate = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            usage_count=25,
            success_rate=1.0
        )
        assert profile_moderate.score > 90

        # High usage (>100) should decrease score
        profile_high = FingerprintProfile(
            profile_id="test_002",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            usage_count=101,
            success_rate=1.0
        )
        assert profile_high.score < 100

    def test_score_with_blocked_count(self):
        """Test score calculation with blocked count"""
        profile = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            blocked_count=3,
            success_rate=1.0
        )
        # Each blocked count reduces score by 10%
        assert profile.score < 100
        assert profile.score > 50

    def test_score_with_success_rate(self):
        """Test score calculation with success rate"""
        profile_good = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            success_rate=0.5
        )
        # 50% success rate should cut score in half
        assert 40 < profile_good.score < 60

    def test_score_clamping(self):
        """Test that score is clamped between 0 and 100"""
        profile_low = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0,
            blocked_count=20,
            success_rate=0.1
        )
        assert 0 <= profile_low.score <= 100

    def test_default_factory_lists(self):
        """Test that default factory lists are independent"""
        profile1 = FingerprintProfile(
            profile_id="test_001",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0
        )
        profile2 = FingerprintProfile(
            profile_id="test_002",
            user_agent="Mozilla/5.0",
            screen_resolution=(1920, 1080),
            timezone="UTC",
            language="en-US",
            platform="Win32",
            hardware_concurrency=8,
            device_memory=8.0
        )

        profile1.plugins.append("test_plugin")

        assert "test_plugin" in profile1.plugins
        assert "test_plugin" not in profile2.plugins
