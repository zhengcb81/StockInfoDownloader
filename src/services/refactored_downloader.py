"""
重构后的下载器服务
使用模块化架构，整合浏览器服务、文件服务等组件
"""

import time
from typing import List, Optional, Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..core.logger import get_logger
from ..core.config import ConfigManager
from ..core.config_constants import ConfigConstants
from ..services.browser_service import BrowserService
from ..services.file_service import FileService
from ..data.mapping import MappingManager


class RefactoredDownloader:
    """重构后的下载器类"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化下载器

        Args:
            config_file: 配置文件路径
        """
        self.config_manager = ConfigManager(config_file)
        self.browser_service = BrowserService(self.config_manager)
        self.file_service = FileService(self.config_manager)
        self.mapping_manager = MappingManager()

        self.logger = get_logger(__name__)

        # 配置参数
        self.max_downloads_per_session = self.config_manager.get(
            'download.max_downloads_per_session', 5)

    def download_stock_pdfs(self,
                          stock_code: str,
                          stock_name: str,
                          suffix: str = "research",
                          allowed_keywords: Optional[List[str]] = None,
                          max_pages: Optional[int] = None) -> List[str]:
        """
        下载股票PDF文件

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            suffix: 页面后缀
            allowed_keywords: 允许的关键词列表
            max_pages: 最大页数

        Returns:
            List[str]: 下载成功的文件路径列表
        """
        # 获取组织ID
        org_id = self._get_org_id(stock_code)
        if not org_id:
            self.logger.error(f"无法获取股票 {stock_code} 的组织ID")
            return []

        # 获取股票目录
        stock_dir = self.file_service.get_stock_directory(stock_code, stock_name)

        # 构建URL
        url = self._build_url(stock_code, org_id, suffix)

        try:
            with self.browser_service as browser:
                # 设置浏览器
                browser.setup_driver()

                # 访问页面
                browser.driver.get(url)
                self.browser_service.dynamic_delay()

                # 下载所有页面
                downloaded_files = self._download_all_pages(
                    browser.driver, stock_code, stock_dir,
                    allowed_keywords, max_pages
                )

                return downloaded_files

        except Exception as e:
            self.logger.error(f"下载过程中发生错误: {e}")
            return []

    def _get_org_id(self, stock_code: str, force_run: bool = False) -> Optional[str]:
        """
        获取股票代码对应的组织ID

        Args:
            stock_code: 股票代码
            force_run: 是否强制重新爬取

        Returns:
            Optional[str]: 组织ID
        """
        try:
            # 从映射文件获取
            org_id = self.mapping_manager.get_org_id(stock_code)
            if org_id and not force_run:
                return org_id

            # 如果映射文件中没有，尝试重新获取
            from orgid_utils import get_org_id_by_code
            org_id = get_org_id_by_code(
                stock_code, force_run=force_run,
                mapping_file=self.config_manager.get('files.mapping_file',
                                                   'stock_orgid_mapping.json')
            )

            if org_id:
                # 更新映射
                self.mapping_manager.save_mapping(stock_code, org_id)

            return org_id

        except Exception as e:
            self.logger.error(f"获取组织ID失败: {e}")
            return None

    def _build_url(self, stock_code: str, org_id: str, suffix: str) -> str:
        """
        构建页面URL

        Args:
            stock_code: 股票代码
            org_id: 组织ID
            suffix: 页面后缀

        Returns:
            str: 页面URL
        """
        base_url = self.config_manager.get('base_url',
                                        ConfigConstants.get_base_url())
        return f"{base_url}/new/disclosure/stock?orgId={org_id}&stockCode={stock_code}#{suffix}"

    def _download_all_pages(self,
                          driver,
                          stock_code: str,
                          stock_dir,
                          allowed_keywords: Optional[List[str]] = None,
                          max_pages: Optional[int] = None) -> List[str]:
        """
        下载所有页面的文件

        Args:
            driver: WebDriver实例
            stock_code: 股票代码
            stock_dir: 股票目录
            allowed_keywords: 允许的关键词列表
            max_pages: 最大页数

        Returns:
            List[str]: 下载成功的文件路径列表
        """
        downloaded_files = []
        page_num = 1

        while True:
            self.logger.info(f"开始下载第 {page_num} 页")

            # 检查是否达到最大页数限制
            if max_pages and page_num > max_pages:
                self.logger.info(f"达到最大页数限制: {max_pages}")
                break

            # 获取当前页面的文档列表
            document_links = self._get_document_links(driver)
            if not document_links:
                self.logger.info("当前页面没有找到文档链接")
                break

            # 下载当前页面的文件
            page_files = self._download_page_files(
                driver, document_links, stock_code, stock_dir, allowed_keywords
            )
            downloaded_files.extend(page_files)

            # 检查是否需要继续翻页
            if not self._go_to_next_page(driver):
                self.logger.info("已经是最后一页")
                break

            page_num += 1

            # 模拟人类行为
            self.browser_service.simulate_human_behavior()
            self.browser_service.dynamic_delay()

        return downloaded_files

    def _get_document_links(self, driver) -> List[Dict[str, Any]]:
        """
        获取页面中的文档链接

        Args:
            driver: WebDriver实例

        Returns:
            List[Dict[str, Any]]: 文档链接列表
        """
        try:
            # 等待表格加载
            table_selector = self.config_manager.get_selector('table_element')
            if not self.browser_service.wait_for_element((By.XPATH, table_selector)):
                self.logger.warning("等待表格元素超时")
                return []

            # 获取所有文档链接
            link_selector = self.config_manager.get_selector('detail_links')
            link_elements = driver.find_elements(By.XPATH, link_selector)

            document_links = []
            for element in link_elements:
                try:
                    href = element.get_attribute('href')
                    if href and '/new/disclosure/detail' in href:
                        # 尝试获取文档标题
                        title_element = element.find_element(By.XPATH, './/ancestor::td[1]')
                        title = title_element.text.strip() if title_element else '未知文档'

                        document_links.append({
                            'url': href,
                            'title': title,
                            'element': element
                        })
                except Exception as e:
                    self.logger.debug(f"解析文档链接失败: {e}")
                    continue

            self.logger.info(f"找到 {len(document_links)} 个文档链接")
            return document_links

        except Exception as e:
            self.logger.error(f"获取文档链接失败: {e}")
            return []

    def _download_page_files(self,
                           driver,
                           document_links: List[Dict[str, Any]],
                           stock_code: str,
                           stock_dir,
                           allowed_keywords: Optional[List[str]] = None) -> List[str]:
        """
        下载当前页面的文件

        Args:
            driver: WebDriver实例
            document_links: 文档链接列表
            stock_code: 股票代码
            stock_dir: 股票目录
            allowed_keywords: 允许的关键词列表

        Returns:
            List[str]: 下载成功的文件路径列表
        """
        downloaded_files = []

        for doc_info in document_links:
            try:
                # 检查关键词匹配
                if allowed_keywords and not self._match_keywords(doc_info['title'], allowed_keywords):
                    continue

                # 下载文件
                file_path = self._download_single_file(driver, doc_info, stock_code, stock_dir)
                if file_path:
                    downloaded_files.append(file_path)

                    # 检查是否需要重启浏览器
                    if self.browser_service.download_count >= self.max_downloads_per_session:
                        self.logger.info("达到最大下载限制，重启浏览器")
                        self.browser_service.restart_driver()

            except Exception as e:
                self.logger.error(f"下载文件失败: {e}")
                continue

        return downloaded_files

    def _match_keywords(self, title: str, keywords: List[str]) -> bool:
        """
        检查标题是否匹配关键词

        Args:
            title: 文档标题
            keywords: 关键词列表

        Returns:
            bool: 是否匹配
        """
        if not keywords:
            return True

        title_lower = title.lower()
        return any(keyword.lower() in title_lower for keyword in keywords)

    def _download_single_file(self,
                             driver,
                             doc_info: Dict[str, Any],
                             stock_code: str,
                             stock_dir) -> Optional[str]:
        """
        下载单个文件

        Args:
            driver: WebDriver实例
            doc_info: 文档信息
            stock_code: 股票代码
            stock_dir: 股票目录

        Returns:
            Optional[str]: 下载的文件路径
        """
        try:
            # 点击文档链接
            doc_info['element'].click()
            self.browser_service.dynamic_delay()

            # 等待下载按钮出现
            download_button_selector = self.config_manager.get_selector('download_button')
            if not self.browser_service.wait_for_element((By.XPATH, download_button_selector)):
                self.logger.warning("等待下载按钮超时")
                return None

            # 点击下载按钮
            download_button = driver.find_element(By.XPATH, download_button_selector)
            download_button.click()

            # 等待下载完成
            download_timeout = self.config_manager.get_timeout('download')
            time.sleep(download_timeout)

            # 查找下载的文件
            downloaded_file = self._find_downloaded_file(stock_dir)
            if downloaded_file:
                self.browser_service.download_count += 1
                return downloaded_file

            return None

        except Exception as e:
            self.logger.error(f"下载单个文件失败: {e}")
            return None

    def _find_downloaded_file(self, directory) -> Optional[str]:
        """
        查找下载的文件

        Args:
            directory: 搜索目录

        Returns:
            Optional[str]: 找到的文件路径
        """
        import glob
        import time

        # 等待文件出现
        max_wait = 30
        for _ in range(max_wait):
            pdf_files = glob.glob(str(directory / "*.pdf"))
            if pdf_files:
                # 返回最新的文件
                latest_file = max(pdf_files, key=os.path.getctime)
                return latest_file
            time.sleep(1)

        return None

    def _go_to_next_page(self, driver) -> bool:
        """
        翻到下一页

        Args:
            driver: WebDriver实例

        Returns:
            bool: 是否成功翻页
        """
        try:
            next_button_selector = self.config_manager.get_selector('next_page_button')
            next_button = driver.find_element(By.XPATH, next_button_selector)

            # 检查是否可点击
            if 'disabled' in next_button.get_attribute('class'):
                return False

            next_button.click()
            self.browser_service.dynamic_delay()
            return True

        except NoSuchElementException:
            self.logger.info("没有找到下一页按钮")
            return False
        except Exception as e:
            self.logger.warning(f"翻页失败: {e}")
            return False