#!/usr/bin/env python3
"""
并行下载示例脚本
演示如何使用ParallelDownloadManager进行多公司并行下载
"""

import time
import logging
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.services.parallel_downloader import create_parallel_downloader
from src.services.stock_service import StockService
from src.core.logger import setup_logging
from src.core.config import ConfigManager


def setup_example_logging():
    """设置示例日志"""
    setup_logging(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def get_sample_stock_codes() -> List[str]:
    """获取示例股票代码列表"""
    # 示例股票代码（深圳交易所）
    return [
        '000001',  # 平安银行
        '000002',  # 万科A
        '000858',  # 五粮液
        '000895',  # 双汇发展
        '002415',  # 海康威视
        '002594',  # 比亚迪
        '002714',  # 牧原股份
        '300059',  # 东方财富
        '300015',  # 爱尔眼科
        '300498',  # 温氏股份
    ]


def example_basic_parallel_download():
    """基础并行下载示例"""
    print("\n=== 基础并行下载示例 ===")

    # 创建并行下载器
    downloader = create_parallel_downloader({
        'max_workers': 3,    # 3个工作线程
        'batch_size': 10,    # 批处理大小
        'enable_proxy': False  # 暂不使用代理
    })

    # 获取示例股票代码
    stock_codes = get_sample_stock_codes()

    print(f"准备下载 {len(stock_codes)} 个公司的数据...")
    print(f"股票代码: {', '.join(stock_codes)}")

    # 添加下载任务
    downloader.add_batch_tasks(stock_codes, target_pages=["research"])

    # 使用上下文管理器自动管理生命周期
    with downloader.session():
        # 监控下载进度
        start_time = time.time()
        last_check = start_time

        while True:
            # 检查是否所有任务完成
            status = downloader.get_status()
            if status['queue_size'] == 0 and status['active_tasks'] == 0:
                break

            # 每5秒打印一次进度
            current_time = time.time()
            if current_time - last_check >= 5:
                elapsed = current_time - start_time
                stats = status['stats']

                print(
                    f"\r进度: "
                    f"运行中 {stats['running_tasks']}, "
                    f"已完成 {stats['completed_tasks']}/{stats['total_tasks']}, "
                    f"成功率 {stats['success_rate']:.1%}, "
                    f"耗时 {elapsed:.0f}s",
                    end="", flush=True
                )

                last_check = current_time

            time.sleep(1)

    # 打印最终结果
    print("\n\n=== 下载完成 ===")
    detailed_stats = downloader.get_detailed_stats()
    stats = detailed_stats['status']['stats']

    print(f"总任务数: {stats['total_tasks']}")
    print(f"完成任务: {stats['completed_tasks']}")
    print(f"失败任务: {stats['failed_tasks']}")
    print(f"总下载文件: {stats['total_downloads']}")
    print(f"成功率: {stats['success_rate']:.2%}")
    print(f"平均耗时: {stats['average_time']:.2f}秒/公司")

    # 显示失败的任务
    if detailed_stats['failed_tasks']:
        print("\n失败的任务:")
        for task in detailed_stats['failed_tasks']:
            print(f"  - {task['stock_code']}: {task['error']}")

    return downloader


def example_pause_and_resume():
    """暂停和恢复示例"""
    print("\n=== 暂停和恢复示例 ===")

    downloader = create_parallel_downloader({
        'max_workers': 2,
        'batch_size': 5
    })

    # 添加一些任务
    stock_codes = get_sample_stock_codes()[:5]  # 只下载前5个
    downloader.add_batch_tasks(stock_codes)

    # 启动下载
    downloader.start()

    print("开始下载...")
    time.sleep(10)  # 运行10秒

    # 暂停下载
    print("\n暂停下载...")
    downloader.pause()
    time.sleep(5)

    # 恢复下载
    print("恢复下载...")
    downloader.resume()

    # 等待完成
    while downloader.task_queue.qsize() > 0 or downloader.active_tasks:
        time.sleep(1)
        status = downloader.get_status()
        print(f"\r运行中: {status['active_tasks']}, 队列: {status['queue_size']}", end="")

    downloader.stop()
    print("\n下载完成")


def example_with_proxy():
    """使用代理的示例（需要配置代理）"""
    print("\n=== 代理下载示例 ===")

    # 注意：需要先在config.json中配置代理信息
    config_manager = ConfigManager()
    proxy_config = config_manager.get('proxy_management', {})

    if not proxy_config.get('enabled', False):
        print("代理未启用，跳过此示例")
        return

    downloader = create_parallel_downloader({
        'max_workers': 3,
        'enable_proxy': True
    })

    stock_codes = get_sample_stock_codes()[:3]  # 只下载3个作为示例
    downloader.add_batch_tasks(stock_codes)

    print("使用代理进行下载...")
    start_time = time.time()

    with downloader.session():
        while downloader.task_queue.qsize() > 0 or downloader.active_tasks:
            time.sleep(2)
            status = downloader.get_status()
            elapsed = time.time() - start_time
            print(
                f"\r进度: "
                f"队列 {status['queue_size']}, "
                f"运行中 {status['active_tasks']}, "
                f"耗时 {elapsed:.0f}s",
                end=""
            )

    print("\n代理下载完成")
    stats = downloader.get_detailed_stats()['status']['stats']
    print(f"成功率: {stats['success_rate']:.2%}")


def example_batch_processing():
    """批处理示例"""
    print("\n=== 批处理示例 ===")

    # 获取所有可用的股票代码
    stock_service = StockService()
    all_stock_codes = stock_service.get_all_stock_codes()

    if not all_stock_codes:
        print("未找到股票代码，使用示例数据")
        all_stock_codes = get_sample_stock_codes()

    print(f"共找到 {len(all_stock_codes)} 个股票代码")

    # 分批处理
    batch_size = 20
    downloader = create_parallel_downloader({
        'max_workers': 4,
        'batch_size': batch_size
    })

    total_start = time.time()
    processed = 0

    with downloader.session():
        for i in range(0, len(all_stock_codes), batch_size):
            batch = all_stock_codes[i:i + batch_size]
            print(f"\n处理批次 {i//batch_size + 1}: {len(batch)} 个公司")

            # 添加批次任务
            downloader.add_batch_tasks(batch)

            # 等待当前批次完成
            batch_start = time.time()
            while downloader.task_queue.qsize() > 0 or downloader.active_tasks:
                time.sleep(2)
                status = downloader.get_status()
                batch_elapsed = time.time() - batch_start
                print(
                    f"\r批次进度: "
                    f"运行中 {status['active_tasks']}, "
                    f"队列 {status['queue_size']}, "
                    f"耗时 {batch_elapsed:.0f}s",
                    end=""
                )

            processed += len(batch)
            total_elapsed = time.time() - total_start
            print(f"\n批次完成！累计处理 {processed}/{len(all_stock_codes)} 个公司")

            # 批次间短暂休息
            if i + batch_size < len(all_stock_codes):
                print("批次间休息10秒...")
                downloader.pause()
                time.sleep(10)
                downloader.resume()

    total_elapsed = time.time() - total_start
    print(f"\n=== 批处理完成 ===")
    print(f"总耗时: {total_elapsed:.1f}秒")
    print(f"平均每公司: {total_elapsed/len(all_stock_codes):.2f}秒")


def main():
    """主函数"""
    setup_example_logging()

    print("StockInfoDownloader 并行下载示例")
    print("=" * 50)

    try:
        # 示例1: 基础并行下载
        example_basic_parallel_download()

        # 示例2: 暂停和恢复
        # example_pause_and_resume()

        # 示例3: 使用代理（需要配置）
        # example_with_proxy()

        # 示例4: 批处理大量数据
        # example_batch_processing()

    except KeyboardInterrupt:
        print("\n\n用户中断，正在停止下载器...")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()