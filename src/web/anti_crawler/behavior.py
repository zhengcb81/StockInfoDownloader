#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Human behavior simulation module.
Simulates realistic human interactions to evade bot detection.
"""

import random
import time
from typing import Dict, List, Optional, Union

from src.core.logger import get_logger
from src.web.anti_crawler.types import BehaviorPattern


class BehaviorSimulator:
    """Behavior simulator"""

    def __init__(self, complexity_level: str = "medium"):
        self.complexity_level = complexity_level
        self.logger = get_logger("BehaviorSimulator")

        # Behavior parameters
        self.mouse_speed_range = (50, 300)  # pixels/second
        self.click_delay_range = (0.1, 0.5)  # seconds
        self.scroll_speed_range = (100, 500)  # pixels/second
        self.typing_speed_range = (50, 150)  # characters/minute
        self.idle_time_range = (1, 10)  # seconds

        # Behavior patterns
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
        self, pattern: BehaviorPattern, duration: Optional[float] = None
    ) -> float:
        """Simulate specified behavior"""
        if pattern not in self.patterns:
            self.logger.warning(f"Unsupported behavior pattern: {pattern}")
            return 0.0

        try:
            func = self.patterns[pattern]
            return func(duration or 0.0)
        except Exception as e:
            self.logger.error(f"Behavior simulation failed: {e}")
            return 0.0

    def simulate_human_interaction(
        self, patterns: List[BehaviorPattern], total_duration: float
    ) -> Dict[str, float]:
        """Simulate complete human-computer interaction"""
        results = {}
        remaining_time = total_duration

        # Randomly select behavior patterns
        for pattern in random.sample(patterns, len(patterns)):
            if remaining_time <= 0:
                break

            # Allocate time for current behavior
            pattern_duration = min(
                remaining_time, random.uniform(1, remaining_time / len(patterns))
            )
            actual_duration = self.simulate_behavior(pattern, pattern_duration)
            results[pattern.value] = actual_duration
            remaining_time -= actual_duration

            # Delay between behaviors
            if remaining_time > 0:
                delay = random.uniform(0.1, 0.5)
                time.sleep(delay)
                remaining_time -= delay

        return results

    def _simulate_mouse_movement(self, duration: Optional[float] = None) -> float:
        """Simulate mouse movement"""
        if duration is None:
            duration = random.uniform(2, 5)

        start_time = time.time()
        end_time = start_time + duration

        points = []
        current_x, current_y = 0, 0

        while time.time() < end_time:
            # Generate movement path
            target_x = random.randint(0, 1920)
            target_y = random.randint(0, 1080)

            # Calculate movement parameters
            distance = (
                (target_x - current_x) ** 2 + (target_y - current_y) ** 2
            ) ** 0.5
            speed = random.uniform(*self.mouse_speed_range)
            move_time = distance / speed if speed > 0 else 0.1

            # Simulate curved movement
            steps = max(10, int(move_time * 30))  # 30 FPS
            for i in range(steps):
                t = i / steps
                # Use Bezier curve to simulate natural movement
                x = current_x + (target_x - current_x) * t
                y = current_y + (target_y - current_y) * t

                # Add random jitter
                x += random.uniform(-2, 2)
                y += random.uniform(-2, 2)

                points.append((x, y))
                time.sleep(move_time / steps)

            current_x, current_y = target_x, target_y

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_scrolling(self, duration: Optional[float] = None) -> float:
        """Simulate scrolling behavior"""
        if duration is None:
            duration = random.uniform(1, 3)

        start_time = time.time()
        end_time = start_time + duration

        current_scroll = 0.0

        while time.time() < end_time:
            # Random scroll distance
            scroll_distance = random.randint(50, 300)
            scroll_speed = random.uniform(*self.scroll_speed_range)
            scroll_time = scroll_distance / scroll_speed

            # Simulate step-by-step scrolling
            steps = max(5, int(scroll_time * 30))
            for i in range(steps):
                step_distance = scroll_distance / steps
                current_scroll += step_distance

                # Add random variation
                variation = random.uniform(-5, 5)
                current_scroll = float(current_scroll + variation)

                time.sleep(scroll_time / steps)

            # Pause after scrolling
            pause_time = random.uniform(0.1, 0.5)
            time.sleep(pause_time)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_typing(self, duration: Optional[float] = None) -> float:
        """Simulate typing behavior"""
        if duration is None:
            duration = random.uniform(3, 8)

        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            # Random input length
            text_length = random.randint(5, 20)
            typing_speed = random.uniform(*self.typing_speed_range)
            typing_time = (text_length / typing_speed) * 60  # Convert to seconds

            # Simulate character-by-character input
            for i in range(text_length):
                # Random character interval
                char_delay = random.uniform(0.05, 0.3)
                time.sleep(char_delay)

                # Occasional pause (thinking time)
                if random.random() < 0.1:  # 10% probability
                    pause_time = random.uniform(0.5, 2.0)
                    time.sleep(pause_time)

                # Simulate backspace and retype
                if random.random() < 0.05:  # 5% probability
                    backspace_count = random.randint(1, 3)
                    time.sleep(backspace_count * 0.1)

            # Pause after input
            pause_time = random.uniform(0.5, 2.0)
            time.sleep(pause_time)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_tab_switching(self, duration: Optional[float] = None) -> float:
        """Simulate tab switching"""
        if duration is None:
            duration = random.uniform(2, 5)

        start_time = time.time()
        end_time = start_time + duration

        switch_count = random.randint(2, 5)

        for i in range(switch_count):
            if time.time() >= end_time:
                break

            # Switch to other tab
            tab_duration = random.uniform(1, 3)
            time.sleep(tab_duration)

            # Switch back to original tab
            return_duration = random.uniform(0.5, 1.5)
            time.sleep(return_duration)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_idle_time(self, duration: Optional[float] = None) -> float:
        """Simulate idle time"""
        if duration is None:
            duration = random.uniform(*self.idle_time_range)

        # Simulate mouse micro-movements
        micro_movements = random.randint(3, 8)
        for i in range(micro_movements):
            time.sleep(duration / micro_movements)
            # Tiny mouse movement
            mouse_jitter = random.uniform(0, 2)
            time.sleep(0.01)

        actual_duration = time.time() - (time.time() - duration)
        return actual_duration

    def _simulate_form_filling(self, duration: Optional[float] = None) -> float:
        """Simulate form filling"""
        if duration is None:
            duration = random.uniform(5, 15)

        start_time = time.time()
        end_time = start_time + duration

        # Simulate filling multiple fields
        field_count = random.randint(3, 8)
        for i in range(field_count):
            if time.time() >= end_time:
                break

            # Switch between fields
            field_switch_time = random.uniform(0.1, 0.3)
            time.sleep(field_switch_time)

            # Fill field (combine with typing behavior)
            field_fill_time = self._simulate_typing(random.uniform(1, 3))

            # Occasionally check field
            if random.random() < 0.2:  # 20% probability
                check_time = random.uniform(0.5, 1.5)
                time.sleep(check_time)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_click_pattern(self, duration: Optional[float] = None) -> float:
        """Simulate click pattern"""
        if duration is None:
            duration = random.uniform(2, 6)

        start_time = time.time()
        end_time = start_time + duration

        click_count = random.randint(3, 8)

        for i in range(click_count):
            if time.time() >= end_time:
                break

            # Click delay
            click_delay = random.uniform(*self.click_delay_range)
            time.sleep(click_delay)

            # Double-click check
            if random.random() < 0.1:  # 10% probability double-click
                double_click_delay = random.uniform(0.1, 0.2)
                time.sleep(double_click_delay)

        actual_duration = time.time() - start_time
        return actual_duration

    def _simulate_drag_drop(self, duration: Union[float, None] = None) -> float:
        """Simulate drag and drop behavior"""
        if duration is None:
            duration = random.uniform(3, 8)

        start_time = time.time()
        end_time = start_time + duration

        # Simulate drag operations
        drag_count = random.randint(1, 3)

        for i in range(drag_count):
            if time.time() >= end_time:
                break

            # Grab time
            grab_time = random.uniform(0.2, 0.5)
            time.sleep(grab_time)

            # Drag movement
            drag_move_time = random.uniform(1, 3)
            self._simulate_mouse_movement(drag_move_time)

            # Release time
            release_time = random.uniform(0.1, 0.3)
            time.sleep(release_time)

        actual_duration = time.time() - start_time
        return actual_duration
