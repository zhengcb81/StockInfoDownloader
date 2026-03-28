"""
Anti-Crawler Behavior Module Tests
Tests for human behavior simulation functionality
"""

from unittest.mock import MagicMock, patch

import pytest

from src.web.anti_crawler.behavior import BehaviorSimulator
from src.web.anti_crawler.types import BehaviorPattern


def _make_time_side_effect(start: float = 100.0, step: float = 0.05, count: int = 1000):
    """Create a time.time() side_effect that increments, ensuring while loops terminate."""
    return iter(start + step * i for i in range(count))


class TestBehaviorSimulator:
    """BehaviorSimulator class tests"""

    def test_init_default(self):
        """Test initialization with default complexity level"""
        simulator = BehaviorSimulator()
        assert simulator.complexity_level == "medium"
        assert simulator.mouse_speed_range == (50, 300)
        assert simulator.click_delay_range == (0.1, 0.5)
        assert simulator.scroll_speed_range == (100, 500)
        assert simulator.typing_speed_range == (50, 150)
        assert simulator.idle_time_range == (1, 10)

    def test_init_custom_complexity(self):
        """Test initialization with custom complexity level"""
        simulator = BehaviorSimulator(complexity_level="high")
        assert simulator.complexity_level == "high"

    def test_has_all_behavior_patterns(self):
        """Test all behavior patterns are registered"""
        simulator = BehaviorSimulator()
        expected_patterns = {
            BehaviorPattern.MOUSE_MOVEMENT,
            BehaviorPattern.SCROLLING,
            BehaviorPattern.TYPING,
            BehaviorPattern.TAB_SWITCHING,
            BehaviorPattern.IDLE_TIME,
            BehaviorPattern.FORM_FILLING,
            BehaviorPattern.CLICK_PATTERN,
            BehaviorPattern.DRAG_DROP,
        }
        assert set(simulator.patterns.keys()) == expected_patterns

    def test_simulate_behavior_mouse_movement(self):
        """Test simulating mouse movement behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.MOUSE_MOVEMENT, 0.1)

            assert isinstance(result, float)
            assert result >= 0.0

    def test_simulate_behavior_scrolling(self):
        """Test simulating scrolling behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.SCROLLING, 0.1)

            assert isinstance(result, float)
            assert result >= 0.0

    def test_simulate_behavior_typing(self):
        """Test simulating typing behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.TYPING, 0.1)

            assert isinstance(result, float)
            assert result >= 0.0

    def test_simulate_behavior_tab_switching(self):
        """Test simulating tab switching behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.TAB_SWITCHING, 0.1)

            assert isinstance(result, float)
            assert result >= 0.0

    def test_simulate_behavior_idle_time(self):
        """Test simulating idle time behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.IDLE_TIME, 0.1)

            assert isinstance(result, float)

    def test_simulate_behavior_form_filling(self):
        """Test simulating form filling behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time, \
             patch.object(simulator, "_simulate_typing", return_value=0.5):
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.FORM_FILLING, 0.1)

            assert isinstance(result, float)

    def test_simulate_behavior_click_pattern(self):
        """Test simulating click pattern behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.CLICK_PATTERN, 0.1)

            assert isinstance(result, float)
            assert result >= 0.0

    def test_simulate_behavior_drag_drop(self):
        """Test simulating drag and drop behavior"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time, \
             patch.object(simulator, "_simulate_mouse_movement", return_value=0.5):
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator.simulate_behavior(BehaviorPattern.DRAG_DROP, 0.1)

            assert isinstance(result, float)

    def test_simulate_behavior_unsupported_pattern(self):
        """Test simulating unsupported behavior pattern"""
        simulator = BehaviorSimulator()

        # Create a mock pattern that's not in the patterns dict
        mock_pattern = MagicMock(spec=BehaviorPattern)
        # MagicMock(spec=BehaviorPattern) won't match any key in patterns dict
        # because it's a different object from the enum values

        result = simulator.simulate_behavior(mock_pattern, 1.0)
        assert result == 0.0

    def test_simulate_behavior_exception_handling(self):
        """Test exception handling in behavior simulation"""
        simulator = BehaviorSimulator()

        with patch.object(simulator, "patterns", {BehaviorPattern.MOUSE_MOVEMENT: MagicMock(side_effect=Exception("Sim error"))}):
            result = simulator.simulate_behavior(BehaviorPattern.MOUSE_MOVEMENT, 1.0)
            assert result == 0.0

    def test_simulate_human_interaction(self):
        """Test complete human interaction simulation"""
        simulator = BehaviorSimulator()
        patterns = [BehaviorPattern.MOUSE_MOVEMENT, BehaviorPattern.SCROLLING]

        with patch("src.web.anti_crawler.behavior.time") as mock_time, \
             patch("random.sample", return_value=patterns), \
             patch.object(simulator, "simulate_behavior", return_value=1.0):
            mock_time.time.side_effect = [0, 1, 2]
            mock_time.sleep.return_value = None

            result = simulator.simulate_human_interaction(patterns, 5.0)

            assert isinstance(result, dict)
            assert "mouse_movement" in result or "scrolling" in result

    def test_simulate_human_interaction_empty_patterns(self):
        """Test human interaction with empty pattern list"""
        simulator = BehaviorSimulator()

        with patch("random.sample", return_value=[]):
            result = simulator.simulate_human_interaction([], 5.0)
            assert result == {}

    def test_simulate_human_interaction_exhausted_time(self):
        """Test human interaction stops when time exhausted"""
        simulator = BehaviorSimulator()
        patterns = [BehaviorPattern.MOUSE_MOVEMENT, BehaviorPattern.SCROLLING]

        with patch("src.web.anti_crawler.behavior.time") as mock_time, \
             patch("random.sample", return_value=patterns), \
             patch.object(simulator, "simulate_behavior", return_value=1.0):
            # Start with 0 remaining time
            mock_time.time.side_effect = [0, 0.5, -1]

            result = simulator.simulate_human_interaction(patterns, 0.1)

            # Should stop early due to no remaining time
            assert isinstance(result, dict)

    def test_simulate_idle_time_with_duration(self):
        """Test idle time simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_idle_time(0.5)

            assert isinstance(result, float)

    def test_simulate_click_pattern_with_duration(self):
        """Test click pattern simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_click_pattern(0.1)

            assert isinstance(result, float)

    def test_simulate_typing_with_duration(self):
        """Test typing simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_typing(0.1)

            assert isinstance(result, float)

    def test_simulate_scrolling_with_duration(self):
        """Test scrolling simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_scrolling(0.1)

            assert isinstance(result, float)

    def test_simulate_tab_switching_with_duration(self):
        """Test tab switching simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time:
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_tab_switching(0.5)

            assert isinstance(result, float)

    def test_simulate_form_filling_with_duration(self):
        """Test form filling simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time, \
             patch.object(simulator, "_simulate_typing", return_value=0.5):
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_form_filling(0.5)

            assert isinstance(result, float)

    def test_simulate_drag_drop_with_duration(self):
        """Test drag drop simulation with specific duration"""
        simulator = BehaviorSimulator()

        with patch("src.web.anti_crawler.behavior.time") as mock_time, \
             patch.object(simulator, "_simulate_mouse_movement", return_value=0.5):
            mock_time.time.side_effect = _make_time_side_effect()
            result = simulator._simulate_drag_drop(0.5)

            assert isinstance(result, float)
