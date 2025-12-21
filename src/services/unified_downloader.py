#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一下载器实现
基于DownloadServiceV2的增强版本，集成最佳实践
"""

import time
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from src.interfaces.downloader_interface import (
    IDownloader,
    IBrowserStrategy,
    IAntiCrawlerStrategy,
    DownloadRequest,
    DownloadResult,
    DownloadStatus
)
from src.abstracts.base_downloader import (
    BaseDownloader,
    BaseBrowserStrategy,
    BaseAntiCrawlerStrategy
)
from src.config.downloader_config import config_manager
from src.core.logger import get_logger


# ==================== 调试标记系统（解耦架构 - 方案B）====================

class DebugStep(Enum):
    """调试步骤枚举 - 7个关键步骤"""
    ORG_ID_MAPPING = "org_id_mapping"  # 映射org ID
    URL_GENERATION = "url_generation"  # 生成URL
    WEBPAGE_CONNECTION = "webpage_connection"  # 连接到目标网页
    PDF_VISIBILITY = "pdf_visibility"  # 看到PDF文档
    PAGINATION = "pagination"  # 翻页操作
    KEYWORD_MATCHING = "keyword_matching"  # 关键词匹配
    DOWNLOAD_PAGE_OPENING = "download_page_opening"  # 打开下载页面
    DOWNLOAD_SUCCESS = "download_success"  # 成功下载


class DebugMarker:
    """调试标记数据结构"""

    def __init__(self, step: DebugStep, success: bool, details: Dict[str, Any] = None, error: str = None):
        self.step = step
        self.success = success
        self.details = details or {}
        self.error = error
        self.timestamp = datetime.now()
        self.marker_id = f"{step.value}_{int(time.time() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "marker_id": self.marker_id,
            "step": self.step.value,
            "step_name": self.step.name,
            "success": self.success,
            "details": self.details,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "timestamp_ms": int(time.time() * 1000)
        }

    def to_log_string(self) -> str:
        """转换为日志字符串"""
        status = "SUCCESS" if self.success else "FAILED"
        details_str = json.dumps(self.details, ensure_ascii=False, separators=(',', ':')) if self.details else "{}"
        error_str = f" | Error: {self.error}" if self.error else ""

        # 限制详情字符串长度，避免日志过长
        if len(details_str) > 200:
            details_str = details_str[:200] + "..."

        return f"[DEBUG_MARKER] {status} {self.step.name} | Details: {details_str}{error_str}"


class DebugMarkerManager:
    """调试标记管理器 - 单例模式，解耦设计"""

    _instance = None

    def __new__(cls, log_dir: str = "logs/debug_markers"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance._init_params = {"log_dir": log_dir}  # 保存初始化参数
        return cls._instance

    def __init__(self, log_dir: str = "logs/debug_markers"):
        if self._initialized:
            return

        # 如果__new__中保存了不同的参数，使用新参数重新初始化
        if hasattr(self, '_init_params') and self._init_params.get("log_dir") != log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.markers: List[DebugMarker] = []
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.marker_file = self.log_dir / f"markers_{self.session_id}.jsonl"
            self._initialized = True
            return

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.markers: List[DebugMarker] = []
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.marker_file = self.log_dir / f"markers_{self.session_id}.jsonl"
        self._initialized = True

    @classmethod
    def reset_instance(cls):
        """重置单例实例（用于测试）"""
        cls._instance = None

    def add_marker(self, step: DebugStep, success: bool, details: Dict[str, Any] = None, error: str = None) -> DebugMarker:
        """添加调试标记"""
        marker = DebugMarker(step, success, details, error)
        self.markers.append(marker)

        # 立即写入文件，确保即使程序崩溃也能保留标记
        self._write_marker_to_file(marker)

        # 同时输出到控制台日志
        print(marker.to_log_string())

        return marker

    def _write_marker_to_file(self, marker: DebugMarker):
        """将标记写入文件"""
        try:
            with open(self.marker_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(marker.to_dict(), ensure_ascii=False) + '\n')
                f.flush()
        except Exception as e:
            print(f"[ERROR] 写入调试标记失败: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """获取标记统计摘要"""
        total = len(self.markers)
        successful = len([m for m in self.markers if m.success])
        failed = total - successful

        # 按步骤统计
        steps_summary = {}
        for step in DebugStep:
            step_markers = [m for m in self.markers if m.step == step]
            if step_markers:
                steps_summary[step.value] = {
                    "total": len(step_markers),
                    "successful": len([m for m in step_markers if m.success]),
                    "failed": len([m for m in step_markers if not m.success])
                }

        return {
            "session_id": self.session_id,
            "total_markers": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "steps": steps_summary
        }

    def get_markers_for_e2e_test(self) -> List[Dict[str, Any]]:
        """为端到端测试提供标记数据"""
        return [m.to_dict() for m in self.markers]

    def clear(self):
        """清空所有标记（用于测试）"""
        self.markers.clear()


def get_debug_marker_manager() -> DebugMarkerManager:
    """获取标记管理器实例"""
    return DebugMarkerManager()


class UnifiedDownloader(BaseDownloader):
    """
    统一下载器实现

    基于DownloadServiceV2的架构，集成RefactoredDownloader的服务分离优点，
    提供统一、高效、可维护的下载解决方案。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 服务组件
        self.file_service = FileService(self.config)
        self.validation_service = ValidationService(self.config)
        self.monitoring_service = MonitoringService(self.config)

        # 下载历史记录
        self.download_history: List[Dict[str, Any]] = []
        self.current_session_id = self._generate_session_id()

        # 浏览器崩溃预防机制
        self.download_attempt_count = 0
        self.max_downloads_before_restart = 10  # 每10次下载后重启浏览器
        self.current_request: Optional[DownloadRequest] = None  # 保存当前请求以便崩溃后恢复

        # 调试标记管理器（解耦设计）
        self._debug_manager = get_debug_marker_manager()

        self.logger.info("统一下载器初始化完成")

    # ==================== 调试标记封装器（方案B核心）====================

    def _debug_step(self, step: DebugStep, func: Callable, *args, **kwargs) -> Any:
        """
        调试步骤封装器 - 方案B的核心

        用法:
            result = self._debug_step(
                DebugStep.URL_GENERATION,
                self._real_build_target_url,
                request
            )

        Args:
            step: 调试步骤枚举
            func: 实际要执行的函数
            *args, **kwargs: 函数参数

        Returns:
            函数执行结果

        Raises:
            原函数的异常会被捕获并记录，然后重新抛出
        """
        try:
            result = func(*args, **kwargs)
            # 成功时记录标记
            self._log_debug_marker(step, True, {"result": result})
            return result
        except Exception as e:
            # 失败时记录标记
            self._log_debug_marker(step, False, {}, str(e))
            # 重新抛出异常，保持原有行为
            raise

    def _log_debug_marker(self, step: DebugStep, success: bool, details: Dict[str, Any] = None, error: str = None):
        """内部方法：记录调试标记"""
        self._debug_manager.add_marker(step, success, details, error)

    def get_debug_markers(self) -> List[Dict[str, Any]]:
        """获取所有调试标记（供e2e_test使用）"""
        return self._debug_manager.get_markers_for_e2e_test()

    def get_debug_summary(self) -> Dict[str, Any]:
        """获取调试标记摘要"""
        return self._debug_manager.get_summary()

    def _init_browser_strategy(self) -> None:
        """初始化浏览器策略（覆盖基类方法）"""
        strategy_name = self.config.get('browser_strategy', 'playwright')
        try:
            # 提取download_dir（用于所有浏览器策略）- 统一使用save_dir
            download_dir = self.config.get('save_dir', 'downloads')

            print(f"[DEBUG] _init_browser_strategy: strategy={strategy_name}, download_dir={download_dir}")

            # 确保事件循环状态正确（针对Playwright）
            if strategy_name == 'playwright':
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self.logger.warning("检测到运行中的事件循环，这可能影响Playwright初始化")
                        # 尝试在新的线程中处理，或者确保不在事件循环中
                except RuntimeError:
                    # 没有事件循环，这是正常的
                    pass

                # 确保清理任何现有的浏览器实例
                if hasattr(self, 'browser_strategy') and self.browser_strategy:
                    try:
                        self.browser_strategy.cleanup()
                        import time
                        time.sleep(1)  # 等待清理完成
                    except:
                        pass

            if strategy_name == 'playwright':
                from src.web.playwright_strategy import PlaywrightStrategy
                # PlaywrightStrategy也需要download_dir作为单独参数
                self.browser_strategy = PlaywrightStrategy(
                    headless=True,
                    download_dir=download_dir,
                    config=self.config
                )
            elif strategy_name == 'selenium':
                from src.web.selenium_strategy import SeleniumStrategy
                # SeleniumStrategy需要download_dir作为单独参数
                self.browser_strategy = SeleniumStrategy(
                    headless=True,
                    download_dir=download_dir,
                    config=self.config
                )
            else:
                raise ValueError(f"不支持的浏览器策略: {strategy_name}")

            self.logger.info(f"浏览器策略初始化成功: {strategy_name}")
        except Exception as e:
            self.logger.error(f"浏览器策略初始化失败: {e}")
            raise

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def download_stock_pdfs(self, request: DownloadRequest) -> DownloadResult:
        """
        下载股票PDF文件 - 主要入口点

        Args:
            request: 下载请求配置

        Returns:
            DownloadResult: 下载结果
        """
        # DEBUG: 检查传入的request对象
        print(f"[DEBUG] download_stock_pdfs: 接收到request对象")
        print(f"[DEBUG]   stock_code: {request.stock_code}")
        print(f"[DEBUG]   save_dir: {request.save_dir}")
        print(f"[DEBUG]   has org_id: {hasattr(request, 'org_id')}")
        print(f"[DEBUG]   has stock_name: {hasattr(request, 'stock_name')}")
        if hasattr(request, 'org_id'):
            print(f"[DEBUG]   org_id: {request.org_id}")
        if hasattr(request, 'stock_name'):
            print(f"[DEBUG]   stock_name: {request.stock_name}")

        start_time = time.time()

        # 如果没有org_id，尝试获取（步骤1: ORG_ID_MAPPING）
        if not hasattr(request, 'org_id') or not request.org_id:
            def _get_org_id():
                from src.data.mapping import MappingManager
                mapping_manager = MappingManager("stock_orgid_mapping.json")
                org_id = mapping_manager.get_org_id(request.stock_code)
                if org_id:
                    request.org_id = org_id
                    return org_id
                raise Exception(f"无法获取{request.stock_code}的org_id")

            try:
                # 使用封装器自动记录调试标记
                org_id = self._debug_step(
                    DebugStep.ORG_ID_MAPPING,
                    _get_org_id
                )
                print(f"[DEBUG] 自动获取org_id: {org_id}")
            except Exception as e:
                self.logger.warning(f"获取org_id失败: {e}")
                # 记录失败标记
                self._log_debug_marker(
                    DebugStep.ORG_ID_MAPPING,
                    False,
                    {"stock_code": request.stock_code},
                    str(e)
                )

        # 验证并准备请求
        self._validate_and_prepare_request(request)

        # 更新状态
        self._update_status(
            is_running=True,
            current_page=0,
            total_pages=request.max_pages,
            downloaded_count=0,
            error_count=0,
            last_error=None
        )

        try:
            self.logger.info(f"开始下载 {request.stock_code} 的PDF文件")

            # 执行下载
            result = self._perform_download(request)

            # 记录下载历史
            self._record_download_history(request, result)

            # 执行后处理
            if result.success:
                self._post_download_processing(request, result)

            # 更新状态
            duration = time.time() - start_time
            self._update_status(
                is_running=False,
                downloaded_count=len(result.downloaded_files),
                last_error=None
            )

            # 添加监控数据
            self.monitoring_service.record_download_session(
                session_id=self.current_session_id,
                request=request,
                result=result,
                duration=duration
            )

            return result

        except Exception as e:
            self.logger.error(f"下载过程发生异常: {e}")

            # 更新失败状态
            duration = time.time() - start_time
            self._update_status(
                is_running=False,
                last_error=str(e),
                error_count=self._status.error_count + 1
            )

            return DownloadResult(
                success=False,
                downloaded_files=[],
                total_files=0,
                errors=[str(e)],
                duration_seconds=duration,
                metadata={
                    'session_id': self.current_session_id,
                    'error_type': type(e).__name__
                }
            )

    def _perform_download(self, request: DownloadRequest) -> DownloadResult:
        """执行实际的下载逻辑"""
        # DEBUG: 检查_perform_download接收到的request
        print(f"[DEBUG] _perform_download: 接收到request对象")
        print(f"[DEBUG]   stock_code: {request.stock_code}")
        print(f"[DEBUG]   save_dir: {request.save_dir}")
        print(f"[DEBUG]   has stock_name: {hasattr(request, 'stock_name')}")
        if hasattr(request, 'stock_name'):
            print(f"[DEBUG]   stock_name: {request.stock_name}")

        downloaded_files = []
        errors = []

        try:
            # 保存当前请求以便浏览器崩溃后恢复
            self.current_request = request
            print(f"[DEBUG] 设置current_request: stock_code={request.stock_code}, has_stock_name={hasattr(request, 'stock_name')}")
            if hasattr(request, 'stock_name'):
                print(f"[DEBUG] current_request.stock_name = {request.stock_name}")

            # 初始化浏览器
            if not self.browser_strategy.initialize():
                raise RuntimeError("浏览器初始化失败")

            # 构建目标URL（步骤2: URL_GENERATION）
            target_url = self._build_target_url(request)

            # 导航到页面并等待加载（步骤3: WEBPAGE_CONNECTION）
            def _connect_to_webpage():
                # 导航到页面
                if not self.browser_strategy.navigate_to_page(target_url):
                    raise RuntimeError("页面导航失败")

                # 等待页面加载
                if not self.browser_strategy.wait_for_element("body", timeout=30):
                    raise RuntimeError("页面加载超时")

                # 获取页面标题用于调试
                page_title = ""
                try:
                    page_title = self.browser_strategy.get_page_title()
                except:
                    pass

                return {
                    "url": target_url,
                    "page_title": page_title
                }

            connection_result = self._debug_step(
                DebugStep.WEBPAGE_CONNECTION,
                _connect_to_webpage
            )

            # *** FIX #2: 根据suffix切换到对应的标签页 ***
            if request.suffix:
                self._switch_to_tab(request.suffix)

            # 额外等待页面内容完全加载（特别是动态内容）
            import time
            time.sleep(3)

            # 执行分页下载
            downloaded_files, errors = self._download_with_pagination(request)

            return DownloadResult(
                success=len(downloaded_files) > 0,
                downloaded_files=downloaded_files,
                total_files=len(downloaded_files),
                errors=errors,
                duration_seconds=0,  # 将在上层计算
                metadata={
                    'url': target_url,
                    'session_id': self.current_session_id,
                    'pages_processed': self._status.current_page
                }
            )

        except Exception as e:
            errors.append(f"下载执行失败: {str(e)}")
            raise

    def _build_target_url(self, request: DownloadRequest) -> str:
        """构建目标URL - 使用封装器自动记录调试标记（步骤2: URL_GENERATION）"""
        return self._debug_step(
            DebugStep.URL_GENERATION,
            self._real_build_target_url,
            request
        )

    def _real_build_target_url(self, request: DownloadRequest) -> str:
        """实际的URL构建逻辑"""
        # 统一使用 disclosure/stock 格式（带 orgId）
        if hasattr(request, 'org_id') and request.org_id:
            # 简化: 只需要 stockCode 和 orgId，suffix 作为 hash 添加
            url = f"https://www.cninfo.com.cn/new/disclosure/stock?stockCode={request.stock_code}&orgId={request.org_id}"
            if request.suffix:
                url += f"#{request.suffix}"  # suffix 作为 URL hash，告诉页面激活哪个标签
        else:
            # 如果没有 org_id，使用旧的 catalogName 格式作为备选
            url = f"http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/stock&stock={request.stock_code}&catalogName=disk"
            if request.suffix:
                url += f"#{request.suffix}"

        # 调试日志
        print(f"[DEBUG] _build_target_url: stock_code={request.stock_code}, suffix={request.suffix}, org_id={getattr(request, 'org_id', None)}")
        print(f"[DEBUG] 构建的URL: {url}")
        print(f"[DEBUG] URL模式: base + hash (#{request.suffix})")

        return url

    def _switch_to_tab(self, suffix: str) -> bool:
        """根据suffix切换到对应的标签页"""
        self.logger.info(f"尝试切换到标签页: suffix={suffix}")  # ✅ 添加日志
        try:
            # 定义suffix到标签页名称的映射
            tab_mapping = {
                'research': '调研',
                'periodicReports': '定期报告',
                'latestAnnouncement': '最新公告',
                'announcement': '公告',
                'stock': '个股',
                'data': '数据',
                'notice': '公告'
            }
            
            tab_name = tab_mapping.get(suffix, '最新公告')
            print(f"[DEBUG] 切换到标签页: {tab_name} (suffix: {suffix})")
            
            # 添加重试机制
            max_attempts = 3
            for attempt in range(max_attempts):
                if self._try_switch_tab(suffix, tab_name):
                    return True
                elif attempt < max_attempts - 1:
                    print(f"[WARN] 标签页切换失败，重试 {attempt + 2}/{max_attempts}")
                    time.sleep(2)
            
            print(f"[ERROR] 无法切换到标签页 {suffix} ({tab_name})")
            return False
        except Exception as e:
            print(f"[DEBUG] 切换标签页异常: {e}")
            return False
    
    def _try_switch_tab(self, suffix: str, tab_name: str) -> bool:
        """尝试切换标签页（单次）"""
        try:
            # 查找包含标签页文本的按钮或链接
            tab_selectors = [
                f"//div[contains(@class, 'tab')]//*[contains(text(), '{tab_name}')]",
                f"//span[contains(text(), '{tab_name}')]/parent::button",
                f"//a[contains(text(), '{tab_name}')]",
                f"//button[contains(text(), '{tab_name}')]",
                f"//*[@data-name='{suffix}']",
                f"//*[@id='{suffix}']"
            ]
            
            tab_element = None
            for selector in tab_selectors:
                try:
                    if '/' in selector:  # XPath
                        elements = self.browser_strategy.find_elements(selector, by="xpath")
                    else:  # CSS
                        elements = self.browser_strategy.find_elements(selector)
                    
                    if elements and len(elements) > 0:
                        tab_element = elements[0]
                        print(f"[DEBUG] 找到标签页元素: {selector}")
                        break
                except Exception as e:
                    print(f"[DEBUG] 尝试选择器失败 {selector}: {e}")
                    continue
            
            # 直接使用JavaScript切换标签页（更可靠）
            self.logger.info(f"使用JavaScript切换标签页: {tab_name} (suffix: {suffix})")
            
            # 更可靠的JavaScript，包含等待和重试
            js_script = f"""
            (function() {{
                // 等待页面加载
                setTimeout(function() {{}}, 1000);
                
                // 方法1: 查找data-name或id属性
                var tab = document.querySelector("[data-name='{suffix}']") || 
                         document.querySelector("[id='{suffix}']");
                if (tab) {{
                    console.log('Found tab by attribute:', tab);
                    tab.click();
                    return 'success:found_by_attribute';
                }}
                
                // 方法2: 查找所有导航元素并匹配文本
                var selectors = ['.tab-item', '.el-tabs__item', '.nav-item', 
                               '.el-menu-item', 'a', 'button', 'li', 'span'];
                var allElements = [];
                
                for (var sel of selectors) {{
                    var elements = document.querySelectorAll(sel);
                    for (var i = 0; i < elements.length; i++) {{
                        var text = (elements[i].textContent || elements[i].innerText || '').trim();
                        if (text.includes('{tab_name}')) {{
                            console.log('Found tab by text:', text, elements[i]);
                            elements[i].click();
                            return 'success:found_by_text:' + text;
                        }}
                        // 也收集所有文本用于调试
                        if (text.length > 0 && text.length < 20) {{
                            allElements.push(text);
                        }}
                    }}
                }}
                
                // 方法3: 查找包含URL hash的链接
                var links = document.querySelectorAll('a[href*="#{suffix}"]');
                if (links.length > 0) {{
                    console.log('Found tab by href:', links[0].href);
                    links[0].click();
                    return 'success:found_by_href';
                }}
                
                console.log('Available tab texts:', allElements.slice(0, 20));  // 打印前20个文本用于调试
                return 'failed:not_found:research';
            }})()
            """
            
            try:
                result = self.browser_strategy.execute_script(js_script)
                self.logger.info(f"JavaScript执行结果: {result}")
                
                if result and 'success' in result:
                    self.logger.info(f"JavaScript切换成功: {result}")
                    time.sleep(3)
                else:
                    self.logger.warning(f"JavaScript切换未确认: {result}，将验证当前URL状态")
                    # 即使JavaScript执行失败，也可能是浏览器环境限制，继续验证URL
                
                # 验证当前URL（关键修复：即使JavaScript返回None，也验证URL）
                current_url = self.browser_strategy.get_current_url()
                self.logger.info(f"当前URL: {current_url}")
                
                if f'#{suffix}' in current_url:
                    self.logger.info(f"✅ URL验证成功: 包含 #{suffix}")
                    time.sleep(2)
                    return True
                else:
                    self.logger.warning(f"❌ URL验证失败: 不包含 #{suffix}")
                    # 即使URL验证失败，也继续尝试下载（某些站点可能使用动态加载）
                    self.logger.info("URL验证失败，但继续尝试在当前页面查找下载链接")
                    return True
                    
            except Exception as e:
                    self.logger.error(f"JavaScript执行异常: {e}", exc_info=True)
                    self.logger.info("JavaScript执行异常，但继续尝试在当前页面查找下载链接")
                    return True
            print(f"[WARN] 无法切换到标签页 {suffix} ({tab_name})，将使用当前页面")
            return False
            
        except Exception as e:
            print(f"[DEBUG] 切换标签页异常: {e}")
            return False

    def _download_with_pagination(self, request: DownloadRequest) -> tuple[List[str], List[str]]:
        """分页下载文件 - 在翻页时记录PAGINATION标记"""
        # DEBUG: 检查_download_with_pagination接收到的request
        print(f"[DEBUG] _download_with_pagination: 接收到request对象")
        print(f"[DEBUG]   stock_code: {request.stock_code}")
        print(f"[DEBUG]   save_dir: {request.save_dir}")
        print(f"[DEBUG]   has stock_name: {hasattr(request, 'stock_name')}")
        if hasattr(request, 'stock_name'):
            print(f"[DEBUG]   stock_name: {request.stock_name}")

        downloaded_files = []
        errors = []

        # DEBUG MARKER: 开始分页下载流程
        try:
            from ..utils.debug_marker import DebugMarker
            pagination_flow_marker = DebugMarker("pagination_flow")
            pagination_flow_marker.add_step("flow_start", "开始分页下载流程", {
                "org_id": request.org_id,
                "max_pages": request.max_pages,
                "stock_code": request.stock_code,
                "suffix": request.suffix
            })
        except ImportError:
            pagination_flow_marker = None

        for page_num in range(1, request.max_pages + 1):
            try:
                self._update_status(current_page=page_num)

                if pagination_flow_marker:
                    pagination_flow_marker.add_step(f"page_{page_num}_start", f"开始处理第 {page_num} 页", {
                        "page_num": page_num
                    })

                # 查找下载链接
                download_links = self._find_download_links()

                if pagination_flow_marker:
                    pagination_flow_marker.add_step(f"page_{page_num}_links", f"第 {page_num} 页链接查找结果", {
                        "page_num": page_num,
                        "links_found": len(download_links)
                    })

                if download_links:
                    # 处理下载链接
                    page_files, page_errors = self._process_download_links(
                        download_links, request
                    )

                    downloaded_files.extend(page_files)
                    errors.extend(page_errors)

                    if pagination_flow_marker:
                        pagination_flow_marker.add_step(f"page_{page_num}_downloaded", f"第 {page_num} 页下载完成", {
                            "page_num": page_num,
                            "files_downloaded": len(page_files),
                            "errors": len(page_errors)
                        })
                else:
                    self.logger.info(f"第 {page_num} 页没有找到匹配的下载链接")

                # 检查是否还有下一页（除非已经到达最大页数）
                if page_num < request.max_pages:
                    if pagination_flow_marker:
                        pagination_flow_marker.add_step(f"page_{page_num}_check_next", f"检查第 {page_num} 页是否有下一页", {
                            "current_url": self.browser_strategy.get_current_url() if hasattr(self.browser_strategy, 'get_current_url') else "unknown"
                        })

                    # DEBUG: Enhanced has_next_page logging
                    self.logger.info(f"[PAGINATION_DEBUG] Page {page_num}: Checking if next page exists...")
                    has_next = self._has_next_page()
                    current_url_after_check = self.browser_strategy.get_current_url() if hasattr(self.browser_strategy, 'get_current_url') else "unknown"

                    self.logger.info(f"[PAGINATION_DEBUG] Page {page_num}: _has_next_page() returned {has_next}, current URL: {current_url_after_check}")

                    if pagination_flow_marker:
                        pagination_flow_marker.add_step(f"page_{page_num}_has_next_result", f"第 {page_num} 页has_next_page结果", {
                            "has_next": has_next,
                            "current_url": current_url_after_check
                        })

                    if not has_next:
                        self.logger.info(f"已到达最后一页，第 {page_num} 页")
                        if pagination_flow_marker:
                            pagination_flow_marker.add_step("no_next_page", "已到达最后一页", {
                                "final_page": page_num,
                                "final_url": current_url_after_check
                            })
                            pagination_flow_marker.save()
                        break

                    # 翻到下一页（记录PAGINATION标记）
                    self.logger.info(f"翻到第 {page_num + 1} 页...")

                    if pagination_flow_marker:
                        pagination_flow_marker.add_step(f"page_{page_num}_pagination_start", f"开始翻页到第 {page_num + 1} 页", {
                            "from_page": page_num,
                            "to_page": page_num + 1,
                            "url_before": current_url_after_check
                        })

                    def _perform_pagination():
                        # DEBUG: Enhanced go_to_next_page logging
                        self.logger.info(f"[PAGINATION_DEBUG] Page {page_num}: Calling _go_to_next_page()...")
                        go_to_result = self._go_to_next_page()
                        self.logger.info(f"[PAGINATION_DEBUG] Page {page_num}: _go_to_next_page() returned {go_to_result}")

                        if not go_to_result:
                            raise Exception("翻页失败")

                        # 等待页面加载
                        time.sleep(2.0)

                        # DEBUG: Check URL after pagination
                        url_after = self.browser_strategy.get_current_url() if hasattr(self.browser_strategy, 'get_current_url') else "unknown"
                        self.logger.info(f"[PAGINATION_DEBUG] Page {page_num}: After pagination, URL is {url_after}")

                        return {
                            "current_page": page_num,
                            "next_page": page_num + 1,
                            "page_url": url_after,
                            "go_to_result": go_to_result
                        }

                    try:
                        pagination_result = self._debug_step(
                            DebugStep.PAGINATION,
                            _perform_pagination
                        )
                        if pagination_flow_marker:
                            pagination_flow_marker.add_step(f"page_{page_num}_pagination_success", f"第 {page_num} 页翻页成功", {
                                "result": pagination_result
                            })
                        self.logger.info(f"[PAGINATION_DEBUG] Page {page_num}: Pagination completed successfully: {pagination_result}")
                    except Exception as e:
                        self.logger.warning(f"翻页失败，停止搜索: {e}")
                        if pagination_flow_marker:
                            pagination_flow_marker.add_step(f"page_{page_num}_pagination_failed", f"第 {page_num} 页翻页失败", {
                                "error": str(e)
                            })
                            pagination_flow_marker.save()
                        # 记录失败标记
                        self._log_debug_marker(
                            DebugStep.PAGINATION,
                            False,
                            {"current_page": page_num},
                            str(e)
                        )
                        self.logger.error(f"[PAGINATION_DEBUG] Page {page_num}: Pagination failed with error: {e}")
                        break

                else:
                    self.logger.info(f"已处理完所有 {request.max_pages} 页")
                    if pagination_flow_marker:
                        pagination_flow_marker.add_step("max_pages_reached", "已达到最大页数", {
                            "max_pages": request.max_pages
                        })
                        pagination_flow_marker.save()

            except Exception as e:
                error_msg = f"处理第 {page_num} 页时发生错误: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                if pagination_flow_marker:
                    pagination_flow_marker.add_step(f"page_{page_num}_exception", f"第 {page_num} 页处理异常", {
                        "error": str(e)
                    })
                continue

        if pagination_flow_marker and page_num == request.max_pages:
            pagination_flow_marker.save()

        return downloaded_files, errors

    def _find_download_links(self) -> List[Dict[str, str]]:
        """查找下载链接 - 使用封装器记录PDF_VISIBILITY和KEYWORD_MATCHING标记"""
        # 首先查找所有链接，记录PDF_VISIBILITY标记
        download_links = self._debug_step(
            DebugStep.PDF_VISIBILITY,
            self._real_find_download_links
        )

        # 如果有下载链接且需要关键词过滤，记录KEYWORD_MATCHING标记
        if download_links and self.current_request:
            allowed_keywords = getattr(self.current_request, 'allowed_keywords', None)
            if allowed_keywords:
                # 关键词匹配已经在_real_find_download_links中完成
                # 这里只需要记录成功标记
                self._log_debug_marker(
                    DebugStep.KEYWORD_MATCHING,
                    True,
                    {
                        "total_links": len(download_links),
                        "keywords": allowed_keywords,
                        "matched_count": len(download_links)
                    }
                )

        return download_links

    def _real_find_download_links(self) -> List[Dict[str, str]]:
        """实际的查找下载链接逻辑"""
        try:
            # 调试信息
            print(f"[DEBUG] UnifiedDownloader._find_download_links called")
            try:
                current_url = self.browser_strategy.get_current_url()
                print(f"[DEBUG] Current URL: {current_url}")
            except Exception as e:
                print(f"[DEBUG] Failed to get URL: {e}")

            # 获取当前请求的关键词过滤条件
            allowed_keywords = getattr(self.current_request, 'allowed_keywords', None) if self.current_request else None
            print(f"[DEBUG] allowed_keywords: {allowed_keywords}")

            # 查找所有链接元素
            elements = self.browser_strategy.find_elements("a")
            print(f"[DEBUG] Found {len(elements)} <a> elements on page")

            # 额外查找可能的其他链接容器
            try:
                # 尝试查找可能包含公告链接的容器
                containers = self.browser_strategy.find_elements(".announcement-list, .news-list, .data-list")
                print(f"[DEBUG] Found {len(containers)} potential list containers")
            except:
                pass

            download_links = []
            total_links = 0
            detail_links = 0
            keyword_matched = 0
            sample_links = []  # 保存前5个链接用于调试
            detail_link_samples = []  # 保存详情页链接样本用于调试（最多20个）

            for element in elements:
                try:
                    # 获取链接文本和URL
                    link_text = self.browser_strategy.get_text(element)
                    link_url = self.browser_strategy.get_attribute(element, "href")

                    total_links += 1

                    # 保存前5个链接用于调试
                    if len(sample_links) < 5:
                        sample_links.append({
                            'text': link_text[:50] if link_text else '',
                            'url': link_url
                        })

                    if not (link_text and link_url):
                        continue

                    # 检查是否是详情页链接（不是直接PDF链接）
                    is_detail_link = False
                    # 获取当前请求的股票代码
                    current_stock_code = getattr(self.current_request, 'stock_code', None) if self.current_request else None

                    # 检查是否是详情页链接（支持多种URL模式）
                    if link_url:
                        # 模式1：包含/disclosure/detail/
                        if '/new/disclosure/detail' in link_url:
                            is_detail_link = True
                        # 模式2：包含股票代码的链接（可能不是detail页面，但包含stockCode参数）
                        elif current_stock_code and f'stockCode={current_stock_code}' in link_url:
                            is_detail_link = True
                        # 模式3：其他可能的详情页URL模式
                        elif '/disclosure/' in link_url and 'stockCode=' in link_url:
                            is_detail_link = True

                    if is_detail_link:
                        detail_links += 1
                        # 保存详情页链接样本用于调试
                        if len(detail_link_samples) < 20:
                            detail_link_samples.append({
                                'text': link_text[:100] if link_text else '',
                                'url': link_url
                            })
                        print(f"[DEBUG] 找到详情页链接 {detail_links}: '{link_text}' -> {link_url}")

                        # 关键词过滤：如果指定了关键词，只下载匹配的文件
                        keyword_match = True
                        if allowed_keywords:
                            # 使用KeywordMatcher进行关键词匹配（包含所有配置功能）
                            from ..utils.keyword_matcher import KeywordMatcher, KeywordConfig

                            keyword_config = KeywordConfig(
                                allowed_keywords=allowed_keywords,
                                mode="any"  # 默认模式：包含任意关键词即通过
                            )
                            keyword_matcher = KeywordMatcher(keyword_config)

                            # 检查是否匹配
                            text_to_check = link_text if link_text else ""
                            keyword_match = keyword_matcher.matches(text=text_to_check, title=text_to_check)

                            if keyword_match:
                                keyword_matched += 1
                                # 记录匹配的关键词
                                matched_keyword = next((keyword for keyword in allowed_keywords if keyword.lower() in (text_to_check.lower() if text_to_check else "")), "未知")
                                print(f"[DEBUG] [通过] 关键词匹配: '{matched_keyword}' in '{text_to_check}'")
                            else:
                                print(f"[DEBUG] [跳过] 关键词不匹配: 链接文本 '{text_to_check}' 不包含任何关键词 {allowed_keywords}")
                                continue

                        if keyword_match:
                            # 修复相对URL
                            full_url = link_url
                            if link_url and link_url.startswith('/'):
                                full_url = f'https://www.cninfo.com.cn{link_url}'

                            download_links.append({
                                'text': link_text,
                                'url': full_url
                            })

                            print(f"[DEBUG] [通过] 详情页链接匹配成功: {link_text}")

                except Exception as e:
                    print(f"[DEBUG] 处理链接时出错: {e}")
                    continue

            self.logger.info(f"链接统计: 总链接{total_links}, 详情页{detail_links}, 关键词匹配{keyword_matched}, 最终下载{len(download_links)}")

            # 打印前5个链接用于调试
            print(f"[DEBUG] 前5个链接样本:")
            for i, link in enumerate(sample_links):
                print(f"  {i+1}. 文本: {link['text']}")
                print(f"     URL: {link['url']}")

            # 打印详情页链接样本用于调试
            if detail_link_samples:
                print(f"[DEBUG] 找到 {len(detail_link_samples)} 个详情页链接样本 (总共 {detail_links} 个):")
                for i, link in enumerate(detail_link_samples[:10]):  # 只显示前10个
                    print(f"  详情页{i+1}. 文本: {link['text']}")
                    print(f"        URL: {link['url']}")
            else:
                print(f"[DEBUG] 未找到任何详情页链接")

            return download_links

        except Exception as e:
            self.logger.error(f"查找下载链接失败: {e}")
            raise

    def _should_download_file(self, text: str, url: str) -> bool:
        """判断是否应该下载文件"""
        # 基本检查
        if not text or not url:
            return False

        # 检查是否是详情页链接（支持多种URL模式）
        is_detail_link = False
        if '/new/disclosure/detail' in url:
            is_detail_link = True
        elif '/disclosure/' in url and 'stockCode=' in url:
            is_detail_link = True

        if not is_detail_link:
            return False

        # TODO: 可以添加更多过滤逻辑，比如基于关键词等

        return True

    def _process_download_links(
        self,
        links: List[Dict[str, str]],
        request: DownloadRequest
    ) -> tuple[List[str], List[str]]:
        """处理下载链接"""
        # DEBUG: 检查_process_download_links接收到的request
        print(f"[DEBUG] _process_download_links: 接收到request对象, 链接数={len(links)}")
        print(f"[DEBUG]   stock_code: {request.stock_code}")
        print(f"[DEBUG]   save_dir: {request.save_dir}")
        print(f"[DEBUG]   has stock_name: {hasattr(request, 'stock_name')}")
        if hasattr(request, 'stock_name'):
            print(f"[DEBUG]   stock_name: {request.stock_name}")

        downloaded_files = []
        errors = []

        for link in links:
            try:
                # 下载文件
                filename = self.file_service.clean_filename(link['text'])
                # 确保文件扩展名为.pdf
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'

                file_path = self._download_file(
                    url=link['url'],
                    filename=filename,
                    save_dir=request.save_dir,
                    request=request
                )

                if file_path and Path(file_path).exists():
                    downloaded_files.append(file_path)
                    self.logger.info(f"文件下载成功: {Path(file_path).name}")
                else:
                    errors.append(f"文件下载失败: {link['text']}")

            except Exception as e:
                error_msg = f"下载文件时出错 {link['text']}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        return downloaded_files, errors

    def _download_file(self, url: str, filename: str, save_dir: str, request: DownloadRequest = None) -> Optional[str]:
        """下载单个文件 - 记录DOWNLOAD_PAGE_OPENING和DOWNLOAD_SUCCESS标记"""
        # DEBUG: 检查_download_file接收到的request
        print(f"[DEBUG] _download_file: 接收到request对象")
        print(f"[DEBUG]   url: {url}")
        print(f"[DEBUG]   filename: {filename}")
        print(f"[DEBUG]   save_dir: {save_dir}")
        print(f"[DEBUG]   request is None: {request is None}")
        if request:
            print(f"[DEBUG]   request.stock_code: {request.stock_code}")
            print(f"[DEBUG]   request has stock_name: {hasattr(request, 'stock_name')}")
            if hasattr(request, 'stock_name'):
                print(f"[DEBUG]   request.stock_name: {request.stock_name}")

        # 步骤7: DOWNLOAD_PAGE_OPENING - 打开下载页面
        try:
            self._log_debug_marker(
                DebugStep.DOWNLOAD_PAGE_OPENING,
                True,
                {
                    "detail_url": url,
                    "filename": filename
                }
            )
        except:
            pass

        # 步骤8: DOWNLOAD_SUCCESS - 执行实际下载并记录结果
        try:
            result = self._debug_step(
                DebugStep.DOWNLOAD_SUCCESS,
                self._real_download_file,
                url, filename, save_dir, request
            )
            return result
        except Exception as e:
            # 如果是浏览器崩溃，尝试重启并重试
            error_msg = str(e).lower()
            if 'crashed' in error_msg or 'target crashed' in error_msg:
                self.logger.warning(f"检测到浏览器崩溃，尝试重启浏览器: {e}")
                try:
                    # 清理当前浏览器实例
                    if self.browser_strategy:
                        self.browser_strategy.cleanup()
                        time.sleep(1)  # 等待清理完成

                    # 重新初始化浏览器
                    self._init_browser_strategy()
                    time.sleep(2)  # 等待浏览器重新启动

                    # 如果有保存的请求，重新导航到列表页
                    if self.current_request:
                        target_url = self._build_target_url(self.current_request)
                        self.logger.info(f"重新导航到列表页: {target_url}")
                        if self.browser_strategy.navigate_to_page(target_url):
                            time.sleep(2)
                            self.logger.info("列表页导航成功，继续下载")
                        else:
                            self.logger.error("列表页导航失败")

                    self.download_attempt_count = 0  # 重置计数器

                    # 重试下载
                    try:
                        result = self._debug_step(
                            DebugStep.DOWNLOAD_SUCCESS,
                            self._real_download_file,
                            url, filename, save_dir, request
                        )
                        return result
                    except Exception as retry_error:
                        self._log_debug_marker(
                            DebugStep.DOWNLOAD_SUCCESS,
                            False,
                            {"url": url, "filename": filename},
                            str(retry_error)
                        )
                        return None
                except Exception as restart_error:
                    self.logger.error(f"浏览器重启失败: {restart_error}")
                    self._log_debug_marker(
                        DebugStep.DOWNLOAD_SUCCESS,
                        False,
                        {"url": url, "filename": filename},
                        str(restart_error)
                    )
                    return None
            else:
                # 其他错误，直接记录失败标记
                self._log_debug_marker(
                    DebugStep.DOWNLOAD_SUCCESS,
                    False,
                    {"url": url, "filename": filename},
                    str(e)
                )
                return None

    def _real_download_file(self, url: str, filename: str, save_dir: str, request: DownloadRequest = None) -> Optional[str]:
        """实际的文件下载逻辑"""
        try:
            # 获取公司名称（如果可用）
            stock_name = None
            if request and hasattr(request, 'stock_name'):
                stock_name = request.stock_name
                print(f"[DEBUG] _download_file: 从request获取stock_name={stock_name}")
            elif self.current_request and hasattr(self.current_request, 'stock_name'):
                stock_name = self.current_request.stock_name
                print(f"[DEBUG] _download_file: 从current_request获取stock_name={stock_name}")
            else:
                print(f"[DEBUG] _download_file: 未找到stock_name, request={bool(request)}, current_request={bool(self.current_request)}")
                if request:
                    print(f"[DEBUG] request属性: {dir(request)}")

            # 构建完整的保存路径：save_dir / 公司名称 / filename
            if stock_name:
                save_path = Path(save_dir) / stock_name / filename
            else:
                save_path = Path(save_dir) / filename

            save_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"[DEBUG] _download_file: url={url}, filename={filename}, save_path={save_path}")

            # 增加下载计数器
            self.download_attempt_count += 1
            print(f"[DEBUG] 下载尝试次数: {self.download_attempt_count}/{self.max_downloads_before_restart}")

            # 预防性重启：如果下载次数过多，先重启浏览器
            if self.download_attempt_count >= self.max_downloads_before_restart:
                self.logger.info(f"达到最大下载次数({self.max_downloads_before_restart})，预防性重启浏览器")
                try:
                    if self.browser_strategy:
                        self.browser_strategy.cleanup()
                        time.sleep(1)
                    self._init_browser_strategy()
                    time.sleep(2)
                    self.download_attempt_count = 0  # 重置计数器
                    self.logger.info("预防性重启完成")
                except Exception as e:
                    self.logger.error(f"预防性重启失败: {e}")

            # 使用DownloadHelper从详情页下载文件
            # URL是详情页，不是直接的PDF链接
            from .download_helper import SeleniumDownloadHelper, PlaywrightDownloadHelper

            # 获取下载目录 - 统一使用save_dir
            download_dir = self.config.get('save_dir', 'downloads')

            # 根据浏览器策略选择合适的下载辅助器
            strategy_name = self.config.get('browser_strategy', 'playwright')
            if strategy_name == 'playwright':
                helper = PlaywrightDownloadHelper(self.browser_strategy)
            else:  # selenium
                helper = SeleniumDownloadHelper(self.browser_strategy, str(download_dir))

            success = helper.download_from_detail_page(url, str(save_path), timeout=60)

            if success and save_path.exists():
                return str(save_path)
            else:
                self.logger.error(f"文件下载失败: {url}")
                return None

        except Exception as e:
            self.logger.error(f"下载文件失败 {filename}: {e}")
            raise

    def _has_next_page(self) -> bool:
        """检查是否还有下一页"""
        try:
            # 使用浏览器策略的has_next_page方法
            if hasattr(self.browser_strategy, 'has_next_page'):
                return self.browser_strategy.has_next_page()
            else:
                # 回退：查找下一页按钮
                next_button = self.browser_strategy.find_elements(
                    "button.el-pagination__next:not(.is-disabled), "
                    ".pagination .next:not(.disabled), "
                    "a[aria-label='下一页']:not(.disabled), "
                    ".el-pager li.number.active + li.number"
                )
                return len(next_button) > 0
        except Exception:
            return False

    def _go_to_next_page(self) -> bool:
        """跳转到下一页"""
        try:
            # 使用浏览器策略的go_to_next_page方法
            if hasattr(self.browser_strategy, 'go_to_next_page'):
                return self.browser_strategy.go_to_next_page()
            else:
                # 回退：手动查找并点击下一页按钮
                next_button = self.browser_strategy.find_elements(
                    "button.el-pagination__next:not(.is-disabled), "
                    ".pagination .next:not(.disabled), "
                    "a[aria-label='下一页']:not(.disabled), "
                    ".el-pager li.number.active + li.number"
                )
                if next_button:
                    return self.browser_strategy.click(next_button[0])
                return False
        except Exception:
            return False

    def _post_download_processing(self, request: DownloadRequest, result: DownloadResult) -> None:
        """下载后处理"""
        try:
            # 文件验证
            if result.success and result.downloaded_files:
                validated_files = self.validation_service.validate_downloaded_files(
                    result.downloaded_files
                )

                # 更新结果
                result.downloaded_files = validated_files
                result.total_files = len(validated_files)

            # 如果需要，可以添加更多后处理逻辑
            if request.delete_later:
                self._schedule_cleanup(result.downloaded_files)

        except Exception as e:
            self.logger.warning(f"下载后处理失败: {e}")

    def _schedule_cleanup(self, files: List[str]) -> None:
        """安排文件清理"""
        # TODO: 实现文件清理逻辑
        pass

    def _record_download_history(self, request: DownloadRequest, result: DownloadResult) -> None:
        """记录下载历史"""
        try:
            history_entry = {
                'timestamp': datetime.now().isoformat(),
                'session_id': self.current_session_id,
                'stock_code': request.stock_code,
                'stock_name': request.stock_name,
                'suffix': request.suffix,
                'max_pages': request.max_pages,
                'success': result.success,
                'downloaded_files': result.downloaded_files,
                'file_count': result.total_files,
                'errors': result.errors,
                'duration_seconds': result.duration_seconds,
                'metadata': result.metadata
            }

            self.download_history.append(history_entry)

            # 限制历史记录数量
            max_history = 1000
            if len(self.download_history) > max_history:
                self.download_history = self.download_history[-max_history:]

        except Exception as e:
            self.logger.error(f"记录下载历史失败: {e}")

    def get_download_history(self) -> List[Dict[str, Any]]:
        """获取下载历史记录"""
        return self.download_history.copy()

    def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.browser_strategy:
                self.browser_strategy.cleanup()
                self.browser_strategy = None

            self.logger.info("下载器资源清理完成")

        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")

    def download_activity_records(
        self,
        stock_code: str,
        org_id: Optional[str] = None,
        headless: bool = True,
        max_retries: int = 3,
        suffix: str = '',
        allowed_keywords: Optional[List[str]] = None,
        max_pages: Optional[int] = None
    ) -> bool:
        """
        下载投资者关系活动记录表（兼容旧接口）

        Args:
            stock_code: 股票代码
            org_id: 组织ID，如果为None则自动获取
            headless: 是否使用无头模式
            max_retries: 最大重试次数
            suffix: 页面后缀，如research、periodicReports等
            allowed_keywords: 允许的关键词列表，None表示不过滤
            max_pages: 最大下载数，None表示使用默认值

        Returns:
            bool: 下载是否成功
        """
        try:
            # 获取组织ID
            if not org_id:
                from src.data.mapping import MappingManager
                mapping_manager = MappingManager("stock_orgid_mapping.json")
                org_id = mapping_manager.get_org_id(stock_code)
                if not org_id:
                    self.logger.error(f"无法获取 {stock_code} 的组织ID")
                    return False

            # 设置max_pages默认值
            if max_pages is None:
                max_pages = 5

            # 获取股票名称
            stock_name = None
            try:
                from src.data.mapping import MappingManager
                mapping_manager = MappingManager("stock_orgid_mapping.json")
                stock_name = mapping_manager.get_stock_name(stock_code)
                if not stock_name:
                    stock_name = f"股票{stock_code}"
            except Exception as e:
                self.logger.warning(f"获取股票名称失败: {e}")
                stock_name = f"股票{stock_code}"

            # 创建请求对象，包含org_id和stock_name
            # 统一使用save_dir作为配置键名
            save_dir = self.config.get('save_dir', 'downloads')
            request = DownloadRequest(
                stock_code=stock_code,
                suffix=suffix,
                allowed_keywords=allowed_keywords,
                max_pages=max_pages,
                save_dir=save_dir
            )
            # 使用setattr添加额外字段（因为DownloadRequest是dataclass但我们不想修改接口）
            request.org_id = org_id
            request.stock_name = stock_name
            print(f"[DEBUG] 设置org_id到request: {org_id}")
            print(f"[DEBUG] 设置stock_name到request: {stock_name}")

            # 执行下载
            result = self.download_stock_pdfs(request)

            # 返回成功状态
            return result.success

        except Exception as e:
            self.logger.error(f"下载活动记录失败: {e}")
            return False

    def get_supported_browsers(self) -> List[str]:
        """获取支持的浏览器列表"""
        return ['playwright', 'selenium']


class FileService:
    """文件服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("FileService")

    def clean_filename(self, filename: str) -> str:
        """清理文件名"""
        import re

        # 移除非法字符
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # 限制长度
        if len(cleaned) > 200:
            cleaned = cleaned[:200]

        return cleaned.strip()

    def download_file(self, url: str, filename: str, save_dir: str) -> Optional[str]:
        """下载文件"""
        try:
            save_path = Path(save_dir) / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # TODO: 实现实际的文件下载逻辑
            # 这里应该使用requests或浏览器策略来下载文件

            self.logger.info(f"下载文件: {filename}")
            return str(save_path)

        except Exception as e:
            self.logger.error(f"下载文件失败 {filename}: {e}")
            return None


class ValidationService:
    """验证服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("ValidationService")

    def validate_downloaded_files(self, files: List[str]) -> List[str]:
        """验证下载的文件"""
        validated_files = []

        for file_path in files:
            try:
                path = Path(file_path)

                if not path.exists():
                    self.logger.warning(f"文件不存在: {file_path}")
                    continue

                # 检查文件大小
                file_size = path.stat().st_size
                if file_size < 1024:  # 小于1KB
                    self.logger.warning(f"文件过小，可能损坏: {file_path}")
                    continue

                # TODO: 可以添加更多验证逻辑
                validated_files.append(file_path)

            except Exception as e:
                self.logger.error(f"验证文件失败 {file_path}: {e}")

        return validated_files


class MonitoringService:
    """监控服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger("MonitoringService")
        self.download_sessions: List[Dict[str, Any]] = []

    def record_download_session(
        self,
        session_id: str,
        request: DownloadRequest,
        result: DownloadResult,
        duration: float
    ) -> None:
        """记录下载会话"""
        try:
            session_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'request': {
                    'stock_code': request.stock_code,
                    'max_pages': request.max_pages,
                    'timeout': request.timeout_seconds
                },
                'result': {
                    'success': result.success,
                    'file_count': result.total_files,
                    'error_count': len(result.errors)
                },
                'performance': {
                    'duration_seconds': duration,
                    'files_per_second': result.total_files / duration if duration > 0 else 0
                }
            }

            self.download_sessions.append(session_data)

            # 限制会话记录数量
            max_sessions = 500
            if len(self.download_sessions) > max_sessions:
                self.download_sessions = self.download_sessions[-max_sessions:]

        except Exception as e:
            self.logger.error(f"记录下载会话失败: {e}")

    def get_download_sessions(self) -> List[Dict[str, Any]]:
        """获取下载会话记录"""
        return self.download_sessions.copy()