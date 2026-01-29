#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强反爬虫机制
实现多层次反爬虫保护，包括指纹随机化、行为模拟、自适应速率限制等
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.logger import get_logger


class FingerprintType(Enum):
    """指纹类型枚举"""

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
    """行为模式枚举"""

    MOUSE_MOVEMENT = "mouse_movement"
    SCROLLING = "scrolling"
    TYPING = "typing"
    TAB_SWITCHING = "tab_switching"
    IDLE_TIME = "idle_time"
    FORM_FILLING = "form_filling"
    CLICK_PATTERN = "click_pattern"
    DRAG_DROP = "drag_drop"


class AntiCrawlerLevel(Enum):
    """反爬虫保护级别"""

    LOW = "low"  # 基础保护
    MEDIUM = "medium"  # 中等保护
    HIGH = "high"  # 高强度保护
    EXTREME = "extreme"  # 极端保护


@dataclass
class FingerprintProfile:
    """指纹配置文件"""

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
        """标记使用"""
        self.last_used = time.time()
        self.usage_count += 1

        if success:
            # 更新成功率
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
        """检查指纹是否可疑"""
        return (
            self.success_rate < 0.3  # 成功率低于30%
            or self.blocked_count > 5  # 被封次数超过5次
            or self.usage_count > 100
        )  # 使用次数过多

    @property
    def score(self) -> float:
        """计算指纹评分"""
        score = 100.0

        # 成功率影响
        score *= self.success_rate

        # 使用次数影响（适中使用最好）
        if 10 <= self.usage_count <= 50:
            score *= 1.1
        elif self.usage_count > 100:
            score *= 0.8

        # 封禁次数影响
        score *= max(0.1, 1.0 - (self.blocked_count * 0.1))

        # 使用频率影响
        if self.last_used:
            age = time.time() - self.last_used
            if age < 3600:  # 1小时内频繁使用
                score *= 0.9
            elif age > 86400:  # 24小时未使用
                score *= 1.1

        return max(0.0, min(100.0, score))


class BehaviorSimulator:
    """行为模拟器"""

    def __init__(self, complexity_level: str = "medium"):
        self.complexity_level = complexity_level
        self.logger = get_logger("BehaviorSimulator")

        # 行为参数
        self.mouse_speed_range = (50, 300)  # 像素/秒
        self.click_delay_range = (0.1, 0.5)  # 秒
        self.scroll_speed_range = (100, 500)  # 像素/秒
        self.typing_speed_range = (50, 150)  # 字符/分钟
        self.idle_time_range = (1, 10)  # 秒

        # 行为模式
        self.patterns = {
            BehaviorPattern.MOUSE_MOVEMENT: self._simulate_mouse_movement,
            BehaviorPattern.SCROLLING: self._simulate_scrolling,
            BehaviorPattern.TYPING: self._simulate_typing,
            BehaviorPattern.TAB_SWITCHING: self._simulate_tab_switching,
            BehaviorPattern.IDLE_TIME: self._simulate_idle_time,
            BehaviorPattern.FORM_FILLING: self._simulate_form_filling,
            BehaviorPattern.CLICK_PATTERN: self._simulate_click_pattern,
            BehaviorPattern.DRAG_DROP: self._simulate_drag_drop,
        }

    def simulate_behavior(
        self, pattern: BehaviorPattern, duration: float = None
    ) -> float:
        """模拟指定行为"""
        if pattern not in self.patterns:
            self.logger.warning(f"不支持的行为模式: {pattern}")
            return 0.0

        try:
            func = self.patterns[pattern]
            return func(duration)
        except Exception as e:
            self.logger.error(f"行为模拟失败: {e}")
            return 0.0

    def simulate_human_interaction(
        self, patterns: List[BehaviorPattern], total_duration: float
    ) -> Dict[str, float]:
        """模拟完整的人机交互"""
        results = {}
        remaining_time = total_duration

        # 随机选择行为模式
        for pattern in random.sample(patterns, len(patterns)):
            if remaining_time <= 0:
                break

            # 为当前行为分配时间
            pattern_duration = min(
                remaining_time, random.uniform(1, remaining_time / len(patterns))
            )
            actual_duration = self.simulate_behavior(pattern, pattern_duration)
            results[pattern.value] = actual_duration
            remaining_time -= actual_duration

            # 行为间延迟
            if remaining_time > 0:
                delay = random.uniform(0.1, 0.5)
                time.sleep(delay)
                remaining_time -= delay

        return results

    def _simulate_mouse_movement(self, duration: float = None) -> float:
        """模拟鼠标移动"""
        if duration is None:
            duration = random.uniform(2, 5)

        start_time = time.time()
        end_time = start_time + duration

        points = []
        current_x, current_y = 0, 0

        while time.time() < end_time:
            # 生成移动路径
            target_x = random.randint(0, 1920)
            target_y = random.randint(0, 1080)

            # 计算移动参数
            distance = (
                (target_x - current_x) ** 2 + (target_y - current_y) ** 2
            ) ** 0.5
            speed = random.uniform(*self.mouse_speed_range)
            move_time = distance / speed if speed > 0 else 0.1

            # 模拟曲线移动
            steps = max(10, int(move_time * 30))  # 30 FPS
            for i in range(steps):
                t = i / steps
                # 使用贝塞尔曲线模拟自然移动
                x = current_x + (target_x - current_x) * t
                y = current_y + (target_y - current_y) * t

                # 添加随机抖动
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)

                points.append((x, y))
                time.sleep(move_time / steps)

            current_x, current_y = target_x, target_y

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_scrolling(self, duration: float = None) -> float:
        """模拟滚动行为"""
        if duration is None:
            duration = random.uniform(1, 3)

        start_time = time.time()
        end_time = start_time + duration

        current_scroll = 0

        while time.time() < end_time:
            # 随机滚动距离
            scroll_distance = random.randint(50, 300)
            scroll_speed = random.uniform(*self.scroll_speed_range)
            scroll_time = scroll_distance / scroll_speed

            # 模拟分步滚动
            steps = max(5, int(scroll_time * 30))
            for i in range(steps):
                step_distance = scroll_distance / steps
                current_scroll += step_distance

                # 添加随机变化
                variation = random.uniform(-5, 5)
                current_scroll += variation

                time.sleep(scroll_time / steps)

            # 滚动后暂停
            pause_time = random.uniform(0.1, 0.5)
            time.sleep(pause_time)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_typing(self, duration: float = None) -> float:
        """模拟打字行为"""
        if duration is None:
            duration = random.uniform(3, 8)

        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            # 随机输入长度
            text_length = random.randint(5, 20)
            typing_speed = random.uniform(*self.typing_speed_range)
            typing_time = (text_length / typing_speed) * 60  # 转换为秒

            # 模拟逐字符输入
            for i in range(text_length):
                # 随机字符间隔
                char_delay = random.uniform(0.05, 0.3)
                time.sleep(char_delay)

                # 偶尔暂停（思考时间）
                if random.random() < 0.1:  # 10%概率
                    pause_time = random.uniform(0.5, 2.0)
                    time.sleep(pause_time)

                # 模拟删除和重输
                if random.random() < 0.05:  # 5%概率
                    backspace_count = random.randint(1, 3)
                    time.sleep(backspace_count * 0.1)

            # 输入后暂停
            pause_time = random.uniform(0.5, 2.0)
            time.sleep(pause_time)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_tab_switching(self, duration: float = None) -> float:
        """模拟标签页切换"""
        if duration is None:
            duration = random.uniform(2, 5)

        start_time = time.time()
        end_time = start_time + duration

        switch_count = random.randint(2, 5)

        for i in range(switch_count):
            if time.time() >= end_time:
                break

            # 切换到其他标签页
            tab_duration = random.uniform(1, 3)
            time.sleep(tab_duration)

            # 切换回原标签页
            return_duration = random.uniform(0.5, 1.5)
            time.sleep(return_duration)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_idle_time(self, duration: float = None) -> float:
        """模拟空闲时间"""
        if duration is None:
            duration = random.uniform(*self.idle_time_range)

        # 模拟鼠标微动
        micro_movements = random.randint(3, 8)
        for i in range(micro_movements):
            time.sleep(duration / micro_movements)
            # 微小的鼠标移动
            mouse_jitter = random.uniform(0, 2)
            time.sleep(0.01)

        actual_duration = time.time() - (time.time() - duration)
        return actual_duration

    def _simulate_form_filling(self, duration: float = None) -> float:
        """模拟表单填写"""
        if duration is None:
            duration = random.uniform(5, 15)

        start_time = time.time()
        end_time = start_time + duration

        # 模拟填写多个字段
        field_count = random.randint(3, 8)
        for i in range(field_count):
            if time.time() >= end_time:
                break

            # 字段间切换
            field_switch_time = random.uniform(0.1, 0.3)
            time.sleep(field_switch_time)

            # 填写字段（结合打字行为）
            field_fill_time = self._simulate_typing(random.uniform(1, 3))

            # 偶尔检查字段
            if random.random() < 0.2:  # 20%概率
                check_time = random.uniform(0.5, 1.5)
                time.sleep(check_time)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_click_pattern(self, duration: float = None) -> float:
        """模拟点击模式"""
        if duration is None:
            duration = random.uniform(2, 6)

        start_time = time.time()
        end_time = start_time + duration

        click_count = random.randint(3, 8)

        for i in range(click_count):
            if time.time() >= end_time:
                break

            # 点击延迟
            click_delay = random.uniform(*self.click_delay_range)
            time.sleep(click_delay)

            # 双击检查
            if random.random() < 0.1:  # 10%概率双击
                double_click_delay = random.uniform(0.1, 0.2)
                time.sleep(double_click_delay)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_drag_drop(self, duration: float = None) -> float:
        """模拟拖拽行为"""
        if duration is None:
            duration = random.uniform(3, 8)

        start_time = time.time()
        end_time = start_time + duration

        # 模拟拖拽操作
        drag_count = random.randint(1, 3)

        for i in range(drag_count):
            if time.time() >= end_time:
                break

            # 抓取时间
            grab_time = random.uniform(0.2, 0.5)
            time.sleep(grab_time)

            # 拖拽移动
            drag_move_time = random.uniform(1, 3)
            self._simulate_mouse_movement(drag_move_time)

            # 释放时间
            release_time = random.uniform(0.1, 0.3)
            time.sleep(release_time)

        actual_duration = time.time() - start_time
        return actual_duration


class AdaptiveRateLimiter:
    """自适应速率限制器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("AdaptiveRateLimiter")

        # 速率限制参数
        self.initial_requests_per_minute = config.get("initial_requests_per_minute", 30)
        self.max_requests_per_minute = config.get("max_requests_per_minute", 100)
        self.adjustment_factor = config.get("adjustment_factor", 1.2)
        self.success_rate_threshold = config.get("success_rate_threshold", 0.8)
        self.error_rate_threshold = config.get("error_rate_threshold", 0.2)

        # 动态参数
        self.current_rate_limit = self.initial_requests_per_minute
        self.request_history = []
        self.success_history = []
        self.error_history = []

        # 统计窗口
        self.window_size = 60  # 60秒窗口
        self.last_adjustment = time.time()

        # 保护机制
        self.protection_mode = False
        self.protection_start_time = None
        self.protection_duration = 300  # 5分钟保护模式

        self.logger.info(
            f"自适应速率限制器初始化完成，初始速率: {self.initial_requests_per_minute}/分钟"
        )

    def record_request(self, success: bool = True):
        """记录请求结果"""
        current_time = time.time()

        # 记录请求
        self.request_history.append(current_time)
        if success:
            self.success_history.append(current_time)
        else:
            self.error_history.append(current_time)

        # 清理历史记录
        self._cleanup_history()

        # 定期调整速率
        if current_time - self.last_adjustment > 30:  # 每30秒调整一次
            self._adjust_rate_limit()

    def _cleanup_history(self):
        """清理过期历史记录"""
        cutoff_time = time.time() - self.window_size

        self.request_history = [t for t in self.request_history if t > cutoff_time]
        self.success_history = [t for t in self.success_history if t > cutoff_time]
        self.error_history = [t for t in self.error_history if t > cutoff_time]

    def _adjust_rate_limit(self):
        """调整速率限制"""
        current_time = time.time()
        self.last_adjustment = current_time

        # 检查是否应该退出保护模式
        if (
            self.protection_mode
            and (current_time - self.protection_start_time) > self.protection_duration
        ):
            self.protection_mode = False
            self.logger.info("退出保护模式")

        # 计算统计信息
        total_requests = len(self.request_history)
        successful_requests = len(self.success_history)
        error_requests = len(self.error_history)

        if total_requests == 0:
            return

        success_rate = successful_requests / total_requests
        error_rate = error_requests / total_requests

        # 根据成功率调整速率
        if success_rate >= self.success_rate_threshold and not self.protection_mode:
            # 成功率高，适当增加速率
            new_rate = min(
                self.current_rate_limit * self.adjustment_factor,
                self.max_requests_per_minute,
            )
            if new_rate > self.current_rate_limit:
                self.current_rate_limit = new_rate
                self.logger.info(
                    f"提高速率限制至 {self.current_rate_limit:.1f}/分钟 (成功率: {success_rate:.2%})"
                )

        elif (
            success_rate < self.success_rate_threshold
            or error_rate > self.error_rate_threshold
        ):
            # 成功率低或错误率高，降低速率
            new_rate = self.current_rate_limit / self.adjustment_factor
            self.current_rate_limit = max(1, new_rate)

            # 如果错误率过高，进入保护模式
            if error_rate > 0.5 or success_rate < 0.5:
                self.protection_mode = True
                self.protection_start_time = current_time
                self.current_rate_limit = max(5, self.current_rate_limit / 2)
                self.logger.warning(
                    f"进入保护模式，降低速率限制至 {self.current_rate_limit:.1f}/分钟"
                )

            self.logger.warning(
                f"降低速率限制至 {self.current_rate_limit:.1f}/分钟 (成功率: {success_rate:.2%}, 错误率: {error_rate:.2%})"
            )

    def can_make_request(self) -> Tuple[bool, float]:
        """检查是否可以发起请求"""
        if self.protection_mode:
            # 保护模式下更加保守
            recent_requests = len(
                [t for t in self.request_history if time.time() - t < 10]
            )
            if recent_requests >= 2:
                wait_time = (
                    10 - (time.time() - self.request_history[-1])
                    if self.request_history
                    else 0
                )
                return False, max(0, wait_time)

        # 检查速率限制
        recent_requests = len([t for t in self.request_history if time.time() - t < 60])
        if recent_requests >= self.current_rate_limit:
            wait_time = (
                60 - (time.time() - self.request_history[-1])
                if self.request_history
                else 0
            )
            return False, max(0, wait_time)

        return True, 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        self._cleanup_history()

        total_requests = len(self.request_history)
        successful_requests = len(self.success_history)
        error_requests = len(self.error_history)

        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        error_rate = error_requests / total_requests if total_requests > 0 else 0

        current_requests_per_minute = len(
            [t for t in self.request_history if time.time() - t < 60]
        )

        return {
            "current_rate_limit": self.current_rate_limit,
            "current_requests_per_minute": current_requests_per_minute,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "protection_mode": self.protection_mode,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "error_requests": error_requests,
        }


class CaptchaHandler:
    """验证码处理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("CaptchaHandler")

        self.strategies = config.get(
            "strategies", ["delay_retry", "proxy_rotation", "user_agent_change"]
        )
        self.max_wait_time = config.get("max_wait_time", 120)
        self.solve_timeout = config.get("solve_timeout", 30)

        # 验证码检测模式
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
        self, page_content: str, response_headers: Dict[str, str] = None
    ) -> bool:
        """检测是否遇到验证码"""
        # 检查页面内容
        content_lower = page_content.lower()
        for indicator in self.captcha_indicators:
            if indicator.lower() in content_lower:
                return True

        # 检查响应头
        if response_headers:
            for key, value in response_headers.items():
                if any(
                    indicator in value.lower() for indicator in self.captcha_indicators
                ):
                    return True

        return False

    def handle_captcha(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证码"""
        self.logger.info("检测到验证码，开始处理...")

        results = []

        for strategy in self.strategies:
            try:
                result = self._execute_strategy(strategy, context)
                results.append(result)

                if result.get("success"):
                    self.logger.info(f"验证码处理成功，策略: {strategy}")
                    return result

            except Exception as e:
                self.logger.error(f"验证码处理策略 {strategy} 失败: {e}")
                results.append(
                    {"strategy": strategy, "success": False, "error": str(e)}
                )

        # 所有策略都失败
        self.logger.error("所有验证码处理策略都失败了")
        return {
            "success": False,
            "strategy": "all",
            "error": "所有验证码处理策略失败",
            "results": results,
        }

    def _execute_strategy(
        self, strategy: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行具体策略"""
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
                "error": f"未知策略: {strategy}",
            }

    def _strategy_delay_retry(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """延迟重试策略"""
        delay = random.uniform(30, 60)  # 30-60秒延迟
        self.logger.info(f"执行延迟重试策略，等待 {delay:.1f} 秒")

        time.sleep(delay)

        return {
            "strategy": "delay_retry",
            "success": True,
            "delay": delay,
            "action": "delayed_retry",
        }

    def _strategy_proxy_rotation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """代理轮换策略"""
        proxy_manager = context.get("proxy_manager")
        if not proxy_manager:
            return {
                "strategy": "proxy_rotation",
                "success": False,
                "error": "代理管理器不可用",
            }

        # 轮换所有代理
        proxy_manager.rotate_all_proxies()

        return {
            "strategy": "proxy_rotation",
            "success": True,
            "action": "proxy_rotated",
        }

    def _strategy_user_agent_change(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """用户代理更改策略"""
        user_agents = context.get("user_agents", [])
        if not user_agents:
            return {
                "strategy": "user_agent_change",
                "success": False,
                "error": "用户代理列表不可用",
            }

        # 选择新的用户代理
        new_user_agent = random.choice(user_agents)

        return {
            "strategy": "user_agent_change",
            "success": True,
            "action": "user_agent_changed",
            "new_user_agent": new_user_agent,
        }

    def _strategy_ip_change(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """IP更改策略"""
        # 这个策略需要更复杂的实现，可能涉及VPN或代理切换
        self.logger.info("执行IP更改策略")

        # 模拟IP更改（实际实现需要具体网络操作）
        time.sleep(5)  # 模拟IP切换时间

        return {"strategy": "ip_change", "success": True, "action": "ip_changed"}


class EnhancedAntiCrawler:
    """增强反爬虫保护系统"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("EnhancedAntiCrawler")

        self.enabled = config.get("enabled", True)
        self.level = AntiCrawlerLevel(config.get("level", "high"))

        # 初始化各个组件
        self.fingerprint_randomization = self._init_fingerprint_randomization()
        self.behavior_simulator = BehaviorSimulator(
            config.get("behavior_simulation", {}).get("complexity_level", "high")
        )
        self.rate_limiter = AdaptiveRateLimiter(
            config.get("adaptive_rate_limiting", {})
        )
        self.captcha_handler = CaptchaHandler(config.get("captcha_handling", {}))

        # 随机化参数
        self.randomization_factor = config.get("behavior_simulation", {}).get(
            "randomization_factor", 0.3
        )

        # 行为模式配置
        self.enabled_patterns = config.get("behavior_simulation", {}).get(
            "patterns",
            ["mouse_movement", "scrolling", "typing", "tab_switching", "idle_time"],
        )

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "blocked_requests": 0,
            "captcha_encountered": 0,
            "proxy_rotations": 0,
            "fingerprint_changes": 0,
            "behavior_simulations": 0,
        }

        self.logger.info(f"增强反爬虫保护系统初始化完成，保护级别: {self.level.value}")

    def _init_fingerprint_randomization(self) -> Dict[FingerprintType, bool]:
        """初始化指纹随机化配置"""
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
        """请求前处理"""
        if not self.enabled:
            return {"success": True, "action": "disabled"}

        self.stats["total_requests"] += 1

        # 检查速率限制
        can_request, wait_time = self.rate_limiter.can_make_request()
        if not can_request:
            self.logger.warning(f"速率限制，需要等待 {wait_time:.1f} 秒")
            return {
                "success": False,
                "action": "rate_limited",
                "wait_time": wait_time,
                "reason": "请求频率过高",
            }

        # 随机化指纹
        fingerprint_changes = self._randomize_fingerprint(context)

        # 模拟人类行为
        behavior_results = self._simulate_behavior_patterns()

        # 记录行为模拟
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
        self, success: bool, response_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """请求后处理"""
        if not self.enabled:
            return {"success": True, "action": "disabled"}

        # 记录请求结果
        self.rate_limiter.record_request(success)

        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["blocked_requests"] += 1

        # 检查验证码
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
        """随机化指纹"""
        changes = {}

        # 用户代理随机化
        if self.fingerprint_randomization[FingerprintType.USER_AGENT]:
            user_agents = context.get("user_agents", [])
            if user_agents:
                new_user_agent = random.choice(user_agents)
                changes["user_agent"] = new_user_agent
                self.stats["fingerprint_changes"] += 1

        # 屏幕分辨率随机化
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

        # 时区随机化
        if self.fingerprint_randomization[FingerprintType.TIMEZONE]:
            timezones = [
                "Asia/Shanghai",
                "Asia/Tokyo",
                "Asia/Hong_Kong",
                "Asia/Singapore",
            ]
            new_timezone = random.choice(timezones)
            changes["timezone"] = new_timezone

        # 语言随机化
        if self.fingerprint_randomization[FingerprintType.LANGUAGE]:
            languages = ["zh-CN", "zh-TW", "en-US", "en-GB"]
            new_language = random.choice(languages)
            changes["language"] = new_language

        return changes

    def _simulate_behavior_patterns(self) -> Dict[str, float]:
        """模拟行为模式"""
        # 将字符串模式转换为枚举
        pattern_enums = []
        for pattern_str in self.enabled_patterns:
            try:
                pattern_enum = BehaviorPattern(pattern_str)
                pattern_enums.append(pattern_enum)
            except ValueError:
                self.logger.warning(f"未知的行为模式: {pattern_str}")

        if not pattern_enums:
            return {}

        # 随机选择要模拟的模式
        selected_patterns = random.sample(
            pattern_enums, min(len(pattern_enums), random.randint(1, 3))
        )

        # 计算总持续时间
        total_duration = random.uniform(2, 8)

        # 执行行为模拟
        results = self.behavior_simulator.simulate_human_interaction(
            selected_patterns, total_duration
        )

        return results

    def get_protection_level(self) -> AntiCrawlerLevel:
        """获取当前保护级别"""
        return self.level

    def set_protection_level(self, level: AntiCrawlerLevel):
        """设置保护级别"""
        self.level = level
        self.logger.info(f"反爬虫保护级别已设置为: {level.value}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats.update(self.rate_limiter.get_stats())
        stats["protection_level"] = self.level.value
        stats["enabled"] = self.enabled
        return stats

    def emergency_stop(self):
        """紧急停止"""
        self.logger.warning("执行紧急停止，暂停所有请求")
        # 进入严格保护模式
        self.rate_limiter.protection_mode = True
        self.rate_limiter.protection_start_time = time.time()
        self.rate_limiter.current_rate_limit = 1  # 最低速率

    def resume_normal(self):
        """恢复正常模式"""
        self.logger.info("恢复正常模式")
        self.rate_limiter.protection_mode = False
        self.rate_limiter.current_rate_limit = (
            self.rate_limiter.initial_requests_per_minute
        )

    def rotate_all_protections(self):
        """轮换所有保护机制"""
        self.logger.info("轮换所有保护机制...")

        # 轮换指纹
        if self.fingerprint_randomization[FingerprintType.USER_AGENT]:
            self.stats["fingerprint_changes"] += 1

        # 重置速率限制器
        self.rate_limiter.current_rate_limit = (
            self.rate_limiter.initial_requests_per_minute
        )

        self.logger.info("所有保护机制已轮换")
