#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CAPTCHA handling module.
Detects and handles various types of CAPTCHA challenges.
"""

import random
import time
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger


class CaptchaHandler:
    """CAPTCHA handler"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("CaptchaHandler")

        self.strategies = config.get(
            "strategies", ["delay_retry", "proxy_rotation", "user_agent_change"]
        )
        self.max_wait_time = config.get("max_wait_time", 120)
        self.solve_timeout = config.get("solve_timeout", 30)

        # CAPTCHA detection patterns
        self.captcha_indicators = [
            "captcha",
            "验证码",
            "请输入验证码",
            "请完成验证",
            "security check",
            "human verification",
            "robot check",
        ]

    def detect_captcha(
        self, page_content: str, response_headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Detect if CAPTCHA is encountered"""
        # Check page content
        content_lower = page_content.lower()
        for indicator in self.captcha_indicators:
            if indicator.lower() in content_lower:
                return True

        # Check response headers
        if response_headers:
            for key, value in response_headers.items():
                if any(
                    indicator in value.lower() for indicator in self.captcha_indicators
                ):
                    return True

        return False

    def handle_captcha(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CAPTCHA"""
        self.logger.info("CAPTCHA detected, starting handling...")

        results = []

        for strategy in self.strategies:
            try:
                result = self._execute_strategy(strategy, context)
                results.append(result)

                if result.get("success"):
                    self.logger.info(f"CAPTCHA handling successful, strategy: {strategy}")
                    return result

            except Exception as e:
                self.logger.error(f"CAPTCHA handling strategy {strategy} failed: {e}")
                results.append(
                    {"strategy": strategy, "success": False, "error": str(e)}
                )

        # All strategies failed
        self.logger.error("All CAPTCHA handling strategies failed")
        return {
            "success": False,
            "strategy": "all",
            "error": "All CAPTCHA handling strategies failed",
            "results": results,
        }

    def _execute_strategy(
        self, strategy: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute specific strategy"""
        if strategy == "delay_retry":
            return self._strategy_delay_retry(context)
        elif strategy == "proxy_rotation":
            return self._strategy_proxy_rotation(context)
        elif strategy == "user_agent_change":
            return self._strategy_user_agent_change(context)
        elif strategy == "ip_change":
            return self._strategy_ip_change(context)
        else:
            return {
                "strategy": strategy,
                "success": False,
                "error": f"Unknown strategy: {strategy}",
            }

    def _strategy_delay_retry(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Delay retry strategy"""
        delay = random.uniform(30, 60)  # 30-60 second delay
        self.logger.info(f"Executing delay retry strategy, waiting {delay:.1f} seconds")

        time.sleep(delay)

        return {
            "strategy": "delay_retry",
            "success": True,
            "delay": delay,
            "action": "delayed_retry",
        }

    def _strategy_proxy_rotation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy rotation strategy"""
        proxy_manager = context.get("proxy_manager")
        if not proxy_manager:
            return {
                "strategy": "proxy_rotation",
                "success": False,
                "error": "Proxy manager not available",
            }

        # Rotate all proxies
        proxy_manager.rotate_all_proxies()

        return {
            "strategy": "proxy_rotation",
            "success": True,
            "action": "proxy_rotated",
        }

    def _strategy_user_agent_change(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """User agent change strategy"""
        user_agents = context.get("user_agents", [])
        if not user_agents:
            return {
                "strategy": "user_agent_change",
                "success": False,
                "error": "User agent list not available",
            }

        # Select new user agent
        new_user_agent = random.choice(user_agents)

        return {
            "strategy": "user_agent_change",
            "success": True,
            "action": "user_agent_changed",
            "new_user_agent": new_user_agent,
        }

    def _strategy_ip_change(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """IP change strategy"""
        # This strategy requires more complex implementation, possibly involving VPN or proxy switching
        self.logger.info("Executing IP change strategy")

        # Simulate IP change (actual implementation requires specific network operations)
        time.sleep(5)  # Simulate IP switch time

        return {"strategy": "ip_change", "success": True, "action": "ip_changed"}
