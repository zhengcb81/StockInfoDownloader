#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一下载器实现
基于DownloadServiceV2的增强版本，集成最佳实践
"""

import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

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

        self.logger.info("统一下载器初始化完成")

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
        start_time = time.time()

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
            result = self._execute_download_with_retry(request)

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
        downloaded_files = []
        errors = []

        try:
            # 初始化浏览器
            if not self.browser_strategy.initialize():
                raise RuntimeError("浏览器初始化失败")

            # 构建目标URL
            target_url = self._build_target_url(request)

            # 导航到页面
            if not self.browser_strategy.navigate_to_page(target_url):
                raise RuntimeError("页面导航失败")

            # 等待页面加载
            if not self.browser_strategy.wait_for_element("body", timeout=30):
                raise RuntimeError("页面加载超时")

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
        """构建目标URL"""
        base_url = "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/stock"

        # 构建查询参数
        params = {
            'stock': request.stock_code,
            'catalogName': 'disk'  # 公告类别
        }

        if request.suffix:
            params['suffix'] = request.suffix

        # 构建完整URL
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}&{param_str}"

    def _download_with_pagination(self, request: DownloadRequest) -> tuple[List[str], List[str]]:
        """分页下载文件"""
        downloaded_files = []
        errors = []

        for page_num in range(1, request.max_pages + 1):
            try:
                self._update_status(current_page=page_num)

                # 查找下载链接
                download_links = self._find_download_links()

                if not download_links:
                    self.logger.info(f"第 {page_num} 页没有找到下载链接，可能已到达最后一页")
                    break

                # 处理下载链接
                page_files, page_errors = self._process_download_links(
                    download_links, request
                )

                downloaded_files.extend(page_files)
                errors.extend(page_errors)

                # 检查是否还有下一页
                if not self._has_next_page():
                    self.logger.info(f"已到达最后一页，第 {page_num} 页")
                    break

                # 等待一段时间再处理下一页
                time.sleep(1.0)

            except Exception as e:
                error_msg = f"处理第 {page_num} 页时发生错误: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                continue

        return downloaded_files, errors

    def _find_download_links(self) -> List[Dict[str, str]]:
        """查找下载链接"""
        links = []

        try:
            # 查找包含下载链接的元素
            elements = self.browser_strategy.find_elements("a[href*='.pdf']")

            for element in elements:
                try:
                    link_text = element.text.strip()
                    link_url = element.get_attribute('href')

                    if link_url and self._should_download_file(link_text, link_url):
                        links.append({
                            'text': link_text,
                            'url': link_url
                        })
                except Exception as e:
                    self.logger.warning(f"处理下载链接时出错: {e}")
                    continue

            self.logger.info(f"找到 {len(links)} 个下载链接")

        except Exception as e:
            self.logger.error(f"查找下载链接失败: {e}")

        return links

    def _should_download_file(self, text: str, url: str) -> bool:
        """判断是否应该下载文件"""
        # 基本检查
        if not text or not url:
            return False

        # 检查文件扩展名
        if not url.lower().endswith('.pdf'):
            return False

        # TODO: 可以添加更多过滤逻辑，比如基于关键词等

        return True

    def _process_download_links(
        self,
        links: List[Dict[str, str]],
        request: DownloadRequest
    ) -> tuple[List[str], List[str]]:
        """处理下载链接"""
        downloaded_files = []
        errors = []

        for link in links:
            try:
                # 下载文件
                file_path = self.file_service.download_file(
                    url=link['url'],
                    filename=self.file_service.clean_filename(link['text']),
                    save_dir=request.save_dir
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

    def _has_next_page(self) -> bool:
        """检查是否还有下一页"""
        try:
            # 查找下一页按钮
            next_button = self.browser_strategy.find_elements("a:contains('下一页'), button:contains('下一页')")
            return len(next_button) > 0
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