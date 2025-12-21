#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试标记工具 - 用于记录详细的调试信息
"""

import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class DebugMarker:
    """调试标记 - 记录详细的执行步骤和状态"""

    def __init__(self, marker_type: str):
        """
        初始化调试标记

        Args:
            marker_type: 标记类型 (如: "pagination", "download", "url_generation")
        """
        self.marker_type = marker_type
        self.steps: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.marker_id = f"{marker_type}_{int(time.time() * 1000)}"

    def add_step(self, step_id: str, description: str, details: Dict[str, Any] = None):
        """
        添加步骤记录

        Args:
            step_id: 步骤ID
            description: 步骤描述
            details: 详细信息
        """
        step = {
            "step_id": step_id,
            "description": description,
            "details": details or {},
            "timestamp": time.time(),
            "elapsed_ms": int((time.time() - self.start_time) * 1000)
        }
        self.steps.append(step)

    def save(self, log_dir: str = "logs/debug_markers"):
        """
        保存调试标记到文件

        Args:
            log_dir: 日志目录
        """
        try:
            # 确保目录存在
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # 构建完整的标记数据
            marker_data = {
                "marker_id": self.marker_id,
                "marker_type": self.marker_type,
                "start_time": datetime.now().isoformat(),
                "total_elapsed_ms": int((time.time() - self.start_time) * 1000),
                "steps": self.steps,
                "step_count": len(self.steps)
            }

            # 保存到文件
            filename = f"markers_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            filepath = Path(log_dir) / filename

            # 追加模式写入（每行一个完整的JSON对象）
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(marker_data, ensure_ascii=False) + '\n')

        except Exception as e:
            # 如果保存失败，至少打印到控制台
            print(f"[DEBUG_MARKER] 保存失败: {e}")
            print(f"[DEBUG_MARKER] 数据: {json.dumps(marker_data, ensure_ascii=False)}")

    def __repr__(self):
        return f"DebugMarker(type={self.marker_type}, steps={len(self.steps)})"