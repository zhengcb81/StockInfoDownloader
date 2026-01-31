#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Anti-crawler type definitions and enumerations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import time


class FingerprintType(Enum):
    """Fingerprint type enumeration"""

    USER_AGENT = "user_agent"
    SCREEN_RESOLUTION = "screen_resolution"
    TIMEZONE = "timezone"
    LANGUAGE = "language"
    PLATFORM = "platform"
    HARDWARE_INFO = "hardware_info"
    WEBGL_RENDERER = "webgl_renderer"
    CANVAS_FINGERPRINT = "canvas_fingerprint"
    AUDIO_FINGERPRINT = "audio_fingerprint"
    FONT_FINGERPRINT = "font_fingerprint"


class BehaviorPattern(Enum):
    """Behavior pattern enumeration"""

    MOUSE_MOVEMENT = "mouse_movement"
    SCROLLING = "scrolling"
    TYPING = "typing"
    TAB_SWITCHING = "tab_switching"
    IDLE_TIME = "idle_time"
    FORM_FILLING = "form_filling"
    CLICK_PATTERN = "click_pattern"
    DRAG_DROP = "drag_drop"


class AntiCrawlerLevel(Enum):
    """Anti-crawler protection level"""

    LOW = "low"  # Basic protection
    MEDIUM = "medium"  # Medium protection
    HIGH = "high"  # High intensity protection
    EXTREME = "extreme"  # Extreme protection


@dataclass
class FingerprintProfile:
    """Fingerprint profile configuration"""

    profile_id: str
    user_agent: str
    screen_resolution: Tuple[int, int]
    timezone: str
    language: str
    platform: str
    hardware_concurrency: int
    device_memory: float
    webgl_renderer: Optional[str] = None
    canvas_fingerprint: Optional[str] = None
    audio_fingerprint: Optional[str] = None
    font_fingerprint: Optional[str] = None
    plugins: List[str] = field(default_factory=list)
    mime_types: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    usage_count: int = 0
    success_rate: float = 1.0
    blocked_count: int = 0

    def mark_used(self, success: bool = True):
        """Mark profile as used"""
        self.last_used = time.time()
        self.usage_count += 1

        if success:
            # Update success rate
            self.success_rate = (
                self.success_rate * (self.usage_count - 1) + 1
            ) / self.usage_count
        else:
            self.success_rate = (
                self.success_rate * (self.usage_count - 1)
            ) / self.usage_count
            self.blocked_count += 1

    @property
    def is_suspicious(self) -> bool:
        """Check if fingerprint is suspicious"""
        return (
            self.success_rate < 0.3  # Success rate below 30%
            or self.blocked_count > 5  # Blocked more than 5 times
            or self.usage_count > 100
        )  # Used too many times

    @property
    def score(self) -> float:
        """Calculate fingerprint score"""
        score = 100.0

        # Success rate impact
        score *= self.success_rate

        # Usage count impact (moderate usage is best)
        if 10 <= self.usage_count <= 50:
            score *= 1.1
        elif self.usage_count > 100:
            score *= 0.8

        # Block count impact
        score *= max(0.1, 1.0 - (self.blocked_count * 0.1))

        # Usage frequency impact
        if self.last_used:
            age = time.time() - self.last_used
            if age < 3600:  # Frequent use within 1 hour
                score *= 0.9
            elif age > 86400:  # Not used for 24 hours
                score *= 1.1

        return max(0.0, min(100.0, score))
