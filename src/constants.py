"""Application constants — all hardcoded values in one place."""

# ── URLs ──────────────────────────────────────────────────────────────
BASE_URL = "https://www.cninfo.com.cn"
STOCK_PAGE_URL_TEMPLATE = (
    "https://www.cninfo.com.cn/new/disclosure/stock"
    "?stockCode={stock_code}&orgId={org_id}"
)
SEARCH_URL_TEMPLATE = (
    "https://www.cninfo.com.cn/new/fulltextSearch"
    "?notautosubmit=&keyWord={stock_code}"
)
STOCK_NAME_API_TEMPLATE = (
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    "?param={exchange}{stock_code},day,,,1,qfq"
)

# ── Timeouts (seconds) ───────────────────────────────────────────────
PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 10
DOWNLOAD_TIMEOUT = 60
PAGE_LOAD_CHECK_INTERVAL = 2
PAGE_LOAD_MAX_ATTEMPTS = 5
SPA_TAB_SWITCH_WAIT = 2
SPA_CONTENT_WAIT = 3
CONTENT_LOAD_WAIT = 3
PAGINATION_WAIT = 3
DOM_CONTENT_WAIT = 2       # browser.py: wait after domcontentloaded before finding button
POST_DOWNLOAD_WAIT = 1     # downloader.py: sleep after download attempt
INTER_COMPANY_DELAY = 2   # main.py: delay between sequential companies

# ── Selectors ─────────────────────────────────────────────────────────
DETAIL_LINKS_XPATH = "//a[contains(@href, '/new/disclosure/detail')]"
NEXT_PAGE_CSS = "button.btn-next:not([disabled])"
LAST_PAGE_CSS = ".btn-last"
PREV_PAGE_CSS = "button.btn-prev:not([disabled])"

# ── Anti-crawler ──────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 "
    "Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 "
    "Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
]
DEFAULT_DELAY_RANGE = (0.5, 2.0)  # Random delay between requests

# ── Files ─────────────────────────────────────────────────────────────
DEFAULT_MAPPING_FILE = "stock_orgid_mapping.json"
DEFAULT_SAVE_DIR = "downloads"
DEFAULT_LOG_DIR = "logs"
MIN_FILE_SIZE = 100  # bytes — files smaller are considered failed downloads
