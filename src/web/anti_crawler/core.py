#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core anti-crawler protection system.
Main EnhancedAntiCrawler class that coordinates all protection mechanisms.
"""

import random
import time
from typing import Any, Dict, Optional

from src.core.logger import get_logger
from src.web.anti_crawler.types import (
    AntiCrawlerLevel,
    BehaviorPattern,
    FingerprintType,
)
from src.web.anti_crawler.behavior import BehaviorSimulator
from src.web.anti_crawler.rate_limiter import AdaptiveRateLimiter
from src.web.anti_crawler.captcha import CaptchaHandler


class EnhancedAntiCrawler:
    """Enhanced anti-crawler protection system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("EnhancedAntiCrawler")

        self.enabled = config.get("enabled", True)
        self.level = AntiCrawlerLevel(config.get("level", "high"))

        # Initialize components
        self.fingerprint_randomization = self._init_fingerprint_randomization()
        self.behavior_simulator = BehaviorSimulator(
            config.get("behavior_simulation", {}).get("complexity_level", "high")
        )
        self.rate_limiter = AdaptiveRateLimiter(
            config.get("adaptive_rate_limiting", {})
        )
        self.captcha_handler = CaptchaHandler(config.get("captcha_handling", {}))

        # Randomization parameters
        self.randomization_factor = config.get("behavior_simulation", {}).get(
            "randomization_factor", 0.3
        )

        # Behavior pattern configuration
        self.enabled_patterns = config.get("behavior_simulation", {}).get(
            "patterns",
            ["mouse_movement", "scrolling", "typing", "tab_switching", "idle_time"],
        )

        # Statistics
        self.stats: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "blocked_requests": 0,
            "captcha_encountered": 0,
            "proxy_rotations": 0,
            "fingerprint_changes": 0,
            "behavior_simulations": 0,
        }

        self.logger.info(f"Enhanced anti-crawler protection system initialized, level: {self.level.value}")

    def _init_fingerprint_randomization(self) -> Dict[FingerprintType, bool]:
        """Initialize fingerprint randomization configuration"""
        fingerprint_config = self.config.get("fingerprint_randomization", {})
        return {
            FingerprintType.USER_AGENT: fingerprint_config.get(
                "user_agent_rotation", True
            ),
            FingerprintType.SCREEN_RESOLUTION: fingerprint_config.get(
                "screen_resolution", True
            ),
            FingerprintType.TIMEZONE: fingerprint_config.get("timezone", True),
            FingerprintType.LANGUAGE: fingerprint_config.get("language", True),
            FingerprintType.PLATFORM: fingerprint_config.get("platform", True),
            FingerprintType.HARDWARE_INFO: fingerprint_config.get(
                "hardware_info", True
            ),
            FingerprintType.WEBGL_RENDERER: fingerprint_config.get(
                "webgl_renderer", False
            ),
            FingerprintType.CANVAS_FINGERPRINT: fingerprint_config.get(
                "canvas_fingerprint", False
            ),
            FingerprintType.AUDIO_FINGERPRINT: fingerprint_config.get(
                "audio_fingerprint", False
            ),
            FingerprintType.FONT_FINGERPRINT: fingerprint_config.get(
                "font_fingerprint", False
            ),
        }

    def before_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-request processing"""
        if not self.enabled:
            return {"success": True, "action": "disabled"}

        self.stats["total_requests"] += 1

        # Check rate limit
        can_request, wait_time = self.rate_limiter.can_make_request()
        if not can_request:
            self.logger.warning(f"Rate limited, need to wait {wait_time:.1f} seconds")
            return {
                "success": False,
                "action": "rate_limited",
                "wait_time": wait_time,
                "reason": "Request frequency too high",
            }

        # Randomize fingerprint
        fingerprint_changes = self._randomize_fingerprint(context)

        # Simulate human behavior
        behavior_results = self._simulate_behavior_patterns()

        # Record behavior simulation
        if behavior_results:
            self.stats["behavior_simulations"] += 1

        return {
            "success": True,
            "action": "pre_request_complete",
            "fingerprint_changes": fingerprint_changes,
            "behavior_simulation": behavior_results,
            "wait_time": wait_time,
        }

    def after_request(
        self, success: bool, response_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Post-request processing"""
        if not self.enabled:
            return {"success": True, "action": "disabled"}

        # Record request result
        self.rate_limiter.record_request(success)

        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["blocked_requests"] += 1

        # Check CAPTCHA
        if response_data:
            page_content = response_data.get("page_content", "")
            response_headers = response_data.get("response_headers", {})

            if self.captcha_handler.detect_captcha(page_content, response_headers):
                self.stats["captcha_encountered"] += 1

                captcha_context = {
                    "proxy_manager": response_data.get("proxy_manager"),
                    "user_agents": response_data.get("user_agents", []),
                }

                captcha_result = self.captcha_handler.handle_captcha(captcha_context)
                return {
                    "success": False,
                    "action": "captcha_detected",
                    "captcha_result": captcha_result,
                    "needs_retry": True,
                }

        return {
            "success": success,
            "action": "post_request_complete",
            "stats": self.stats.copy(),
        }

    def _randomize_fingerprint(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Randomize fingerprint"""
        changes = {}

        # User agent randomization
        if self.fingerprint_randomization[FingerprintType.USER_AGENT]:
            user_agents = context.get("user_agents", [])
            if user_agents:
                new_user_agent = random.choice(user_agents)
                changes["user_agent"] = new_user_agent
                self.stats["fingerprint_changes"] += 1

        # Screen resolution randomization
        if self.fingerprint_randomization[FingerprintType.SCREEN_RESOLUTION]:
            resolutions = [
                (1920, 1080),
                (1366, 768),
                (1440, 900),
                (1536, 864),
                (1280, 720),
                (1600, 900),
                (1280, 1024),
                (2560, 1440),
            ]
            new_resolution = random.choice(resolutions)
            changes["screen_resolution"] = new_resolution

        # Timezone randomization
        if self.fingerprint_randomization[FingerprintType.TIMEZONE]:
            timezones = [
                "Asia/Shanghai",
                "Asia/Tokyo",
                "Asia/Hong_Kong",
                "Asia/Singapore",
            ]
            new_timezone = random.choice(timezones)
            changes["timezone"] = new_timezone

        # Language randomization
        if self.fingerprint_randomization[FingerprintType.LANGUAGE]:
            languages = ["zh-CN", "zh-TW", "en-US", "en-GB"]
            new_language = random.choice(languages)
            changes["language"] = new_language

        return changes

    def _simulate_behavior_patterns(self) -> Dict[str, float]:
        """Simulate behavior patterns"""
        # Convert string patterns to enums
        pattern_enums = []
        for pattern_str in self.enabled_patterns:
            try:
                pattern_enum = BehaviorPattern(pattern_str)
                pattern_enums.append(pattern_enum)
            except ValueError:
                self.logger.warning(f"Unknown behavior pattern: {pattern_str}")

        if not pattern_enums:
            return {}

        # Randomly select patterns to simulate
        selected_patterns = random.sample(
            pattern_enums, min(len(pattern_enums), random.randint(1, 3))
        )

        # Calculate total duration
        total_duration = random.uniform(2, 8)

        # Execute behavior simulation
        results = self.behavior_simulator.simulate_human_interaction(
            selected_patterns, total_duration
        )

        return results

    def get_protection_level(self) -> AntiCrawlerLevel:
        """Get current protection level"""
        return self.level

    def set_protection_level(self, level: AntiCrawlerLevel):
        """Set protection level"""
        self.level = level
        self.logger.info(f"Anti-crawler protection level set to: {level.value}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        stats = self.stats.copy()
        stats.update(self.rate_limiter.get_stats())
        stats["protection_level"] = str(self.level.value)
        stats["enabled"] = self.enabled
        return stats

    def emergency_stop(self):
        """Emergency stop"""
        self.logger.warning("Executing emergency stop, pausing all requests")
        # Enter strict protection mode
        self.rate_limiter.protection_mode = True
        self.rate_limiter.protection_start_time = time.time()
        self.rate_limiter.current_rate_limit = 1  # Minimum rate

    def resume_normal(self):
        """Resume normal mode"""
        self.logger.info("Resuming normal mode")
        self.rate_limiter.protection_mode = False
        self.rate_limiter.current_rate_limit = (
            self.rate_limiter.initial_requests_per_minute
        )

    def rotate_all_protections(self):
        """Rotate all protection mechanisms"""
        self.logger.info("Rotating all protection mechanisms...")

        # Rotate fingerprint
        if self.fingerprint_randomization[FingerprintType.USER_AGENT]:
            self.stats["fingerprint_changes"] += 1

        # Reset rate limiter
        self.rate_limiter.current_rate_limit = (
            self.rate_limiter.initial_requests_per_minute
        )

        self.logger.info("All protection mechanisms rotated")
