#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""资源清理工具"""

import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


def safe_cleanup(cleanup_func: Callable, error_msg: str = "清理失败") -> bool:
    """
    安全执行清理操作

    Args:
        cleanup_func: 清理函数
        error_msg: 错误消息前缀

    Returns:
        bool: 是否成功执行清理

    Raises:
        TypeError: 如果cleanup_func不是可调用对象
    """
    if cleanup_func is None:
        raise TypeError("cleanup_func不能为None")

    if not callable(cleanup_func):
        raise TypeError(
            f"cleanup_func必须是可调用对象，而不是 {type(cleanup_func).__name__}"
        )

    try:
        cleanup_func()
        return True
    except Exception as e:
        logger.warning(f"{error_msg}: {e}")
        return False


def cleanup_directory(path: Optional[str]) -> bool:
    """
    清理目录

    Args:
        path: 目录路径

    Returns:
        bool: 是否成功清理
    """
    if not path:
        return True

    def _cleanup():
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            logger.debug(f"清理目录: {path}")

    return safe_cleanup(_cleanup, f"清理目录失败: {path}")


def cleanup_file(file_path: Optional[str]) -> bool:
    """
    清理文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否成功清理
    """
    if not file_path:
        return True

    def _cleanup():
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"清理文件: {file_path}")

    return safe_cleanup(_cleanup, f"清理文件失败: {file_path}")


def cleanup_path(path: Optional[Path]) -> bool:
    """
    清理路径（文件或目录）

    Args:
        path: 路径对象

    Returns:
        bool: 是否成功清理
    """
    if not path:
        return True

    try:
        if path.is_file():
            return cleanup_file(str(path))
        elif path.is_dir():
            return cleanup_directory(str(path))
        else:
            logger.debug(f"路径不存在，无需清理: {path}")
            return True
    except Exception as e:
        logger.warning(f"清理路径失败 {path}: {e}")
        return False


def cleanup_multiple_paths(paths: list) -> bool:
    """
    批量清理多个路径

    Args:
        paths: 路径列表

    Returns:
        bool: 是否所有路径都成功清理
    """
    results = []
    for path in paths:
        if isinstance(path, str):
            if os.path.isdir(path):
                results.append(cleanup_directory(path))
            elif os.path.isfile(path):
                results.append(cleanup_file(path))
            else:
                results.append(True)
        elif isinstance(path, Path):
            results.append(cleanup_path(path))
        else:
            results.append(True)

    return all(results)


def cleanup_temp_files(directory: Optional[str], extensions: Optional[List[str]] = None) -> bool:
    """
    清理指定目录中的临时文件

    Args:
        directory: 目录路径
        extensions: 要清理的文件扩展名列表，默认清理临时文件

    Returns:
        bool: 是否成功清理
    """
    if not directory or not os.path.exists(directory):
        return True

    if extensions is None:
        extensions = [".tmp", ".crdownload", ".partial", ".download"]

    try:
        cleaned_count = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.debug(f"清理临时文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败 {file_path}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个临时文件")

        return True
    except Exception as e:
        logger.error(f"清理临时文件时发生错误: {e}")
        return False


def cleanup_empty_directories(directory: Optional[str]) -> bool:
    """
    清理空目录

    Args:
        directory: 根目录路径

    Returns:
        bool: 是否成功清理
    """
    if not directory or not os.path.exists(directory):
        return True

    try:
        cleaned_count = 0
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):  # 空目录
                        os.rmdir(dir_path)
                        cleaned_count += 1
                        logger.debug(f"清理空目录: {dir_path}")
                except Exception as e:
                    logger.warning(f"清理空目录失败 {dir_path}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个空目录")

        return True
    except Exception as e:
        logger.error(f"清理空目录时发生错误: {e}")
        return False


def get_directory_size(directory: Optional[str]) -> int:
    """
    获取目录大小（字节）

    Args:
        directory: 目录路径

    Returns:
        int: 目录大小
    """
    if not directory or not os.path.exists(directory):
        return 0

    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    continue
    except Exception as e:
        logger.warning(f"计算目录大小失败 {directory}: {e}")
        return 0

    return total_size


def cleanup_large_files(directory: Optional[str], max_size_mb: int = 100) -> bool:
    """
    清理大文件

    Args:
        directory: 目录路径
        max_size_mb: 最大文件大小（MB）

    Returns:
        bool: 是否成功清理
    """
    if not directory or not os.path.exists(directory):
        return True

    max_size_bytes = max_size_mb * 1024 * 1024
    cleaned_count = 0

    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    if size > max_size_bytes:
                        os.remove(file_path)
                        cleaned_count += 1
                        logger.info(
                            f"清理大文件 ({size/(1024*1024):.1f}MB): {file_path}"
                        )
                except Exception as e:
                    logger.warning(f"检查文件大小失败 {file_path}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个大文件")

        return True
    except Exception as e:
        logger.error(f"清理大文件时发生错误: {e}")
        return False


def safe_remove_tree(path: Optional[str], retries: int = 3) -> bool:
    """
    安全地删除目录树（带重试）

    Args:
        path: 目录路径
        retries: 重试次数

    Returns:
        bool: 是否成功删除
    """
    if not path or not os.path.exists(path):
        return True

    import time

    for attempt in range(retries):
        try:
            shutil.rmtree(path, ignore_errors=True)

            # 验证是否已删除
            if not os.path.exists(path):
                logger.debug(f"成功删除目录: {path}")
                return True

            # 等待后重试
            time.sleep(0.5)
            logger.debug(f"删除目录失败，尝试第 {attempt + 1} 次重试: {path}")

        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"删除目录失败 {path}: {e}")
                return False
            time.sleep(0.5)

    return False


def safe_move_file(source: str, destination: str) -> bool:
    """
    安全地移动文件

    Args:
        source: 源文件路径
        destination: 目标文件路径

    Returns:
        bool: 是否成功移动
    """
    import shutil

    if not os.path.exists(source):
        logger.error(f"源文件不存在: {source}")
        return False

    try:
        # 确保目标目录存在
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        # 移动文件
        shutil.move(source, destination)

        # 验证移动结果
        if os.path.exists(destination) and os.path.getsize(destination) > 0:
            logger.debug(f"文件移动成功: {source} -> {destination}")
            return True
        else:
            logger.error(f"文件移动失败: 目标文件不存在或为空")
            return False

    except Exception as e:
        logger.error(f"文件移动异常: {e}")
        return False


def safe_copy_file(source: str, destination: str) -> bool:
    """
    安全地复制文件

    Args:
        source: 源文件路径
        destination: 目标文件路径

    Returns:
        bool: 是否成功复制
    """
    import shutil

    if not os.path.exists(source):
        logger.error(f"源文件不存在: {source}")
        return False

    try:
        # 确保目标目录存在
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        # 复制文件
        shutil.copy2(source, destination)

        # 验证复制结果
        if os.path.exists(destination) and os.path.getsize(destination) > 0:
            logger.debug(f"文件复制成功: {source} -> {destination}")
            return True
        else:
            logger.error(f"文件复制失败: 目标文件不存在或为空")
            return False

    except Exception as e:
        logger.error(f"文件复制异常: {e}")
        return False
