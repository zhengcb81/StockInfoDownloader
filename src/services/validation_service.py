"""
验证服务模块
提供文件完整性和业务逻辑验证
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.logger import get_logger

logger = get_logger(__name__)


class ValidationService:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def validate_pdf(self, file_path: str) -> bool:
        """验证 PDF 文件是否有效"""
        path = Path(file_path)
        if not path.exists():
            return False
        # 简单检查：大小不为0且以 %PDF 开头
        try:
            if path.stat().st_size < 100:
                return False
            with open(path, "rb") as f:
                header = f.read(4)
                return header == b"%PDF"
        except:
            return False

    def validate_download_result(
        self, downloaded_files: List[str], expected_count: int
    ) -> bool:
        """验证下载结果数量是否符合预期"""
        return len(downloaded_files) >= expected_count
