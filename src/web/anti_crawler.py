"""
反爬虫策略模块
提供各种反爬虫检测规避策略
"""

import time
import random
import logging
import os
import sys
from typing import Optional
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

from ..core.logger import get_logger

logger = get_logger(__name__)


def is_test_environment():
    """检测是否为测试环境"""
    return (
        os.environ.get('TEST_ENV') == 'true' or
        'test' in sys.argv[0].lower() or
        'pytest' in sys.argv[0].lower() or
        os.environ.get('PYTEST_CURRENT_TEST') is not None
    )


class AntiCrawlerStrategy:
    """反爬虫策略类，包含旧下载器的所有高级机制"""
    
    def __init__(self):
        """初始化反爬虫策略"""
        # 根据环境设置不同的延迟参数 - 优化性能
        if is_test_environment():
            self.min_delay = 0.1  # 测试环境使用更短的延迟
            self.max_delay = 0.3
            logger.info("使用测试环境反爬虫参数")
        else:
            self.min_delay = 0.3  # 生产环境优化延迟时间
            self.max_delay = 1.0
            logger.info("使用生产环境反爬虫参数")
        
        self.max_session_downloads = 10
        self.download_count = 0
        self._user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
    
    def apply_anti_detection(self, driver) -> None:
        """
        应用增强反检测策略（从旧下载器复制）
        
        Args:
            driver: WebDriver实例
        """
        try:
            # 1. 隐藏webdriver属性
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 2. 修改navigator属性
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: function() { return [1, 2, 3, 4, 5]; }
                });
                Object.defineProperty(navigator, 'languages', {
                    get: function() { return ['zh-CN', 'zh', 'en-US', 'en']; }
                });
            """)
            
            # 3. 设置屏幕分辨率
            driver.execute_script("""
                Object.defineProperty(screen, 'width', {get: () => 1920});
                Object.defineProperty(screen, 'height', {get: () => 1080});
                Object.defineProperty(screen, 'availWidth', {get: () => 1920});
                Object.defineProperty(screen, 'availHeight', {get: () => 1040});
            """)
            
            logger.debug("反检测策略已应用")
            
        except Exception as e:
            logger.error(f"应用反检测策略失败: {e}")
    
    def random_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None) -> None:
        """
        随机延迟
        
        Args:
            min_delay: 最小延迟时间(秒)
            max_delay: 最大延迟时间(秒)
        """
        min_d = min_delay or self.min_delay
        max_d = max_delay or self.max_delay
        
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)
        logger.debug(f"随机延迟: {delay:.2f}秒")
    
    def dynamic_delay(self, base_min=0.5, base_max=1.5):
        """动态延迟，根据下载次数调整延迟时间（优化版本）"""
        # 在测试环境中大幅减少延迟
        if is_test_environment():
            base_min = max(0.05, base_min * 0.2)  # 至少0.05秒
            base_max = max(0.1, base_max * 0.2)  # 至少0.1秒
        
        # 下载次数越多，延迟越长，但增长更平缓
        delay_factor = 1 + (self.download_count / 100)
        min_delay = base_min * delay_factor
        max_delay = base_max * delay_factor
        
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"动态延迟 {delay:.2f} 秒 (因子: {delay_factor:.2f})")
        time.sleep(delay)
        return delay
    
    def simulate_real_mouse_movement(self, driver, element=None):
        """模拟真实的鼠标移动轨迹（从旧下载器复制）"""
        try:
            if not driver:
                return
                
            # 生成轨迹点
            if element:
                # 移动到元素
                location = element.location
                start_x, start_y = 100, 100
                end_x, end_y = location['x'], location['y']
            else:
                # 随机移动
                start_x, start_y = 100, 100
                end_x, end_y = random.randint(200, 500), random.randint(200, 500)
            
            # 生成轨迹点
            points = []
            num_points = random.randint(8, 15)
            for t in [i/num_points for i in range(num_points + 1)]:
                x = start_x + (end_x - start_x) * t + random.randint(-15, 15)
                y = start_y + (end_y - start_y) * t + random.randint(-15, 15)
                points.append((x, y))
            
            actions = ActionChains(driver)
            
            # 移动到起始点
            actions.move_by_offset(points[0][0], points[0][1])
            
            # 沿着轨迹移动
            for i in range(1, len(points)):
                dx = points[i][0] - points[i-1][0]
                dy = points[i][1] - points[i-1][1]
                actions.move_by_offset(dx, dy)
                actions.pause(random.uniform(0.01, 0.08))  # 随机暂停
            
            actions.perform()
            
        except Exception as e:
            logger.debug(f"模拟鼠标移动时发生错误: {e}")
    
    def simulate_complex_browsing(self, driver):
        """模拟复杂的浏览行为（从旧下载器复制）"""
        try:
            if not driver:
                return
            
            behaviors = [
                self._simulate_scrolling,
                self._simulate_random_clicks,
                self._simulate_tab_switching
            ]
            
            # 在测试环境中减少行为数量和延迟
            if is_test_environment():
                num_behaviors = random.randint(1, 2)  # 测试环境只做1-2个行为
                delay_range = (0.1, 0.5)  # 测试环境使用更短延迟
            else:
                num_behaviors = random.randint(2, 3)  # 生产环境做2-3个行为
                delay_range = (0.5, 2)  # 生产环境使用正常延迟
            
            selected_behaviors = random.sample(behaviors, min(num_behaviors, len(behaviors)))
            
            for behavior in selected_behaviors:
                behavior(driver)
                time.sleep(random.uniform(delay_range[0], delay_range[1]))
                
        except Exception as e:
            logger.debug(f"模拟复杂浏览行为时发生错误: {e}")
    
    def _simulate_scrolling(self, driver):
        """模拟滚动行为（从旧下载器复制）"""
        try:
            # 随机滚动到页面不同位置
            scroll_positions = [
                "window.scrollTo(0, document.body.scrollHeight * 0.2);",
                "window.scrollTo(0, document.body.scrollHeight * 0.5);",
                "window.scrollTo(0, document.body.scrollHeight * 0.8);",
                "window.scrollTo(0, 0);"
            ]
            
            # 在测试环境中减少滚动次数和延迟
            if is_test_environment():
                num_scrolls = random.randint(1, 2)  # 测试环境只做1-2次滚动
                delay_range = (0.1, 0.3)  # 测试环境使用更短延迟
            else:
                num_scrolls = random.randint(2, 3)  # 生产环境做2-3次滚动
                delay_range = (0.3, 1.2)  # 生产环境使用正常延迟
            
            selected_scrolls = random.sample(scroll_positions, min(num_scrolls, len(scroll_positions)))
            
            for script in selected_scrolls:
                driver.execute_script(script)
                time.sleep(random.uniform(delay_range[0], delay_range[1]))
                
        except Exception as e:
            logger.debug(f"模拟滚动行为失败: {e}")
    
    def _simulate_random_clicks(self, driver):
        """模拟随机点击（从旧下载器复制）"""
        try:
            # 查找可点击的元素
            clickable_elements = driver.find_elements(By.TAG_NAME, "a") + \
                               driver.find_elements(By.TAG_NAME, "button")
            
            if clickable_elements:
                # 随机选择1-2个元素进行点击
                num_clicks = random.randint(1, min(2, len(clickable_elements)))
                selected_elements = random.sample(clickable_elements, num_clicks)
                
                for element in selected_elements:
                    try:
                        # 检查元素是否可见且可点击
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            time.sleep(random.uniform(0.5, 1.5))
                            # 返回上一页
                            driver.back()
                            time.sleep(random.uniform(0.5, 1.0))
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.debug(f"模拟随机点击失败: {e}")
    
    def _simulate_tab_switching(self, driver):
        """模拟标签页切换（从旧下载器复制）"""
        try:
            # 打开一个新标签页
            driver.execute_script("window.open('about:blank', '_blank');")
            time.sleep(random.uniform(0.5, 1.0))
            
            # 获取所有窗口句柄
            window_handles = driver.window_handles
            
            if len(window_handles) > 1:
                # 切换到新标签页
                driver.switch_to.window(window_handles[-1])
                time.sleep(random.uniform(0.5, 1.0))
                
                # 关闭新标签页
                driver.close()
                time.sleep(random.uniform(0.3, 0.8))
                
                # 切换回原标签页
                driver.switch_to.window(window_handles[0])
                
        except Exception as e:
            logger.debug(f"模拟标签页切换失败: {e}")
    
    def smart_delay(self, min_seconds=2, max_seconds=8):
        """智能延迟，根据配置选择使用动态或随机延迟（从旧下载器复制）"""
        # 使用动态延迟
        self.dynamic_delay(min_seconds, max_seconds)
    
    def increment_download_count(self):
        """增加下载计数"""
        self.download_count += 1
    
    def reset_download_count(self):
        """重置下载计数"""
        self.download_count = 0
    
    def set_session_parameters(self, min_delay: float, max_delay: float, max_downloads: int):
        """
        设置会话参数
        
        Args:
            min_delay: 最小延迟时间
            max_delay: 最大延迟时间  
            max_downloads: 最大下载数
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_session_downloads = max_downloads
    
    def simulate_human_behavior(self, driver) -> None:
        """
        模拟人类行为
        
        Args:
            driver: WebDriver实例
        """
        try:
            # 1. 随机滚动页面
            scroll_actions = [
                "window.scrollTo(0, document.body.scrollHeight * 0.3);",
                "window.scrollTo(0, document.body.scrollHeight * 0.7);",
                "window.scrollTo(0, document.body.scrollHeight * 0.5);"
            ]
            
            for script in random.sample(scroll_actions, random.randint(1, 2)):
                driver.execute_script(script)
                self.random_delay(0.5, 1.5)
            
            # 2. 随机移动鼠标
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                if body:
                    actions = ActionChains(driver)
                    
                    # 随机移动鼠标到不同位置
                    for _ in range(random.randint(1, 3)):
                        x_offset = random.randint(-100, 100)
                        y_offset = random.randint(-100, 100)
                        actions.move_to_element_with_offset(body, x_offset, y_offset)
                        actions.perform()
                        self.random_delay(0.3, 0.8)
                        
            except Exception:
                pass  # 忽略鼠标移动失败
            
            # 3. 随机按键
            if random.random() < 0.3:
                body = driver.find_element(By.TAG_NAME, "body")
                if body:
                    body.send_keys(Keys.PAGE_DOWN)
                    self.random_delay(0.5, 1.0)
            
            logger.debug("人类行为模拟完成")
            
        except Exception as e:
            logger.debug(f"人类行为模拟失败: {e}")
    
    def check_session_limit(self, current_downloads: int) -> bool:
        """
        检查会话下载限制
        
        Args:
            current_downloads: 当前会话下载次数
            
        Returns:
            bool: 是否达到限制
        """
        if current_downloads >= self.max_session_downloads:
            logger.info(f"会话下载限制达到: {current_downloads}/{self.max_session_downloads}")
            return True
        return False
    
    def smart_wait(self, driver, condition, timeout: int = 10) -> bool:
        """
        智能等待，包含随机延迟
        
        Args:
            driver: WebDriver实例
            condition: 等待条件
            timeout: 超时时间
            
        Returns:
            bool: 条件是否满足
        """
        try:
            # 随机延迟前等待
            self.random_delay(0.5, 1.5)
            
            wait = WebDriverWait(driver, timeout)
            wait.until(condition)
            
            # 随机延迟后等待
            self.random_delay(0.3, 1.0)
            
            return True
            
        except TimeoutException:
            logger.warning(f"等待条件超时: {timeout}秒")
            return False
        except Exception as e:
            logger.error(f"智能等待失败: {e}")
            return False
    
    def handle_rate_limit(self, driver, retry_count: int = 0) -> bool:
        """
        处理速率限制
        
        Args:
            driver: WebDriver实例
            retry_count: 重试次数
            
        Returns:
            bool: 是否成功处理
        """
        try:
            # 检查是否有验证码
            captcha_elements = [
                "//div[contains(@class, 'captcha')]",
                "//img[contains(@src, 'captcha')]",
                "//*[contains(text(), '验证')]"
            ]
            
            for xpath in captcha_elements:
                try:
                    driver.find_element(By.XPATH, xpath)
                    logger.warning("检测到验证码")
                    
                    # 在测试环境中大幅减少验证码等待时间
                    if is_test_environment():
                        delay = min(5 + retry_count * 2, 15)  # 测试环境最多15秒
                    else:
                        delay = min(30 + retry_count * 10, 120)  # 生产环境最多120秒
                    
                    logger.info(f"遇到验证码，等待{delay}秒")
                    time.sleep(delay)
                    return False
                    
                except Exception:
                    continue
            
            # 如果没有验证码，增加基础延迟
            if is_test_environment():
                base_delay = min(2 + retry_count, 8)  # 测试环境最多8秒
            else:
                base_delay = 5 + retry_count * 2  # 生产环境正常延迟
            
            logger.info(f"速率限制处理，等待{base_delay}秒")
            time.sleep(base_delay)
            
            return True
            
        except Exception as e:
            logger.error(f"处理速率限制失败: {e}")
            return False
    
    def set_session_parameters(self,
                             min_delay: float = 1.0,
                             max_delay: float = 5.0,
                             max_downloads: int = 5) -> None:
        """
        设置会话参数

        Args:
            min_delay: 最小延迟时间
            max_delay: 最大延迟时间
            max_downloads: 最大下载次数
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_session_downloads = max_downloads
        logger.info(f"会话参数已设置: 延迟{min_delay}-{max_delay}秒, 最大下载{max_downloads}次")

    def before_request(self, request_info):
        """请求前处理（兼容接口）"""
        # 应用随机延迟
        self.random_delay()
        logger.debug(f"请求前处理: {request_info}")

    def after_request(self, response_info):
        """请求后处理（兼容接口）"""
        if response_info.get('success', False):
            self.download_count += 1
            logger.debug(f"请求成功: {response_info}")
        else:
            logger.debug(f"请求失败: {response_info}")

    def should_retry(self, error):
        """判断是否应该重试（兼容接口）"""
        error_str = str(error).lower()
        # 不重试的情况
        no_retry_patterns = [
            'timeout',
            'connection refused',
            'dns lookup failed',
            'ssl error'
        ]
        for pattern in no_retry_patterns:
            if pattern in error_str:
                return False
        return True

    def reset_download_count(self) -> None:
        """重置下载计数"""
        self.download_count = 0
        logger.debug("下载计数已重置")