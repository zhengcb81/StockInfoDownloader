#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试清理工具功能
验证test_cleaner.py模块的各种功能
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.utils.cleaner_tool import CleanerTool, clean_test_files, get_test_directory_status
from ..test_config_manager import ConfigManagerTool

# 初始化测试配置管理器
test_config = ConfigManagerTool()

def log(message):
    """统一的日志输出"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{timestamp}] {message}")
    except UnicodeEncodeError:
        # 处理编码问题，使用安全的输出方式
        safe_message = message.encode('gbk', errors='replace').decode('gbk')
        print(f"[{timestamp}] {safe_message}")

def test_cleaner_basic_functionality():
    """测试清理器基本功能"""
    log("测试清理器基本功能")
    
    # 创建临时测试目录
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_results"
        test_dir.mkdir()
        
        # 创建测试文件（使用英文名称避免编码问题）
        (test_dir / "CompanyA").mkdir()
        (test_dir / "CompanyB").mkdir()
        (test_dir / "CompanyA" / "file1.pdf").write_text("test content 1")
        (test_dir / "CompanyB" / "file2.pdf").write_text("test content 2")
        (test_dir / "root_file.pdf").write_text("test content 3")
        
        # 配置保留文件 - 单元测试使用假数据
        preserve_files = [
            {"stock_code": "CompanyA", "delete_later": False},
            {"stock_code": "CompanyB", "delete_later": True}
        ]
        
        # 执行清理
        cleaner = CleanerTool(str(test_dir))
        result = cleaner.clean_test_directory(preserve_files)
        
        # 验证结果
        status = cleaner.get_directory_status()
        
        assert result["status"] == "success", "清理应该成功"
        # 期望保留CompanyA目录及其中的1个文件
        assert status["directories"] == 1, f"应该只保留1个目录，实际保留{status['directories']}个"
        assert status["files"] == 0, f"应该没有根目录文件，实际有{status['files']}个"
        assert status["dir_list"][0]["name"] == "CompanyA", "应该保留CompanyA目录"
        assert status["dir_list"][0]["file_count"] == 1, "CompanyA目录应该包含1个文件"
        
        log("✓ 清理器基本功能测试通过")
        return True

def test_cleaner_with_real_config():
    """使用真实配置测试清理器"""
    log("使用真实配置测试清理器")
    
    # 加载配置
    config_file = "config_end2end_test.json"
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        log(f"加载配置失败: {e}")
        return False
    
    # 备份原有目录
    save_dir = Path(config["save_dir"])
    backup_dir = save_dir.parent / f"{save_dir.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if save_dir.exists():
        shutil.copytree(save_dir, backup_dir)
        log(f"备份原有目录到: {backup_dir}")
    
    try:
        # 确保测试目录存在
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建测试文件（使用真实的股票代码名称）
        preserve_cases = [case for case in config["test_cases"] if not case.get("delete_later", True)]
        delete_cases = [case for case in config["test_cases"] if case.get("delete_later", True)]
        
        # 为要保留的股票代码创建目录和文件
        for case in preserve_cases:
            stock_dir = save_dir / case["stock_code"]
            stock_dir.mkdir(exist_ok=True)
            (stock_dir / f"{case['stock_code']}_file1.pdf").write_text("test")
        
        # 为要删除的股票代码创建目录和文件
        for case in delete_cases:
            stock_dir = save_dir / case["stock_code"]
            stock_dir.mkdir(exist_ok=True)
            (stock_dir / f"{case['stock_code']}_file1.pdf").write_text("test")
            (stock_dir / f"{case['stock_code']}_file2.pdf").write_text("test")
        
        # 获取清理前状态
        status_before = get_test_directory_status(config["save_dir"])
        log(f"清理前: {status_before['files']} 个文件")
        
        # 执行清理
        preserve_cases = [case for case in config["test_cases"] if not case.get("delete_later", True)]
        clean_result = clean_test_files(config["save_dir"], preserve_cases)
        
        # 获取清理后状态
        status_after = get_test_directory_status(config["save_dir"])
        log(f"清理后: {status_after['files']} 个文件")
        
        # 验证结果 - 应该保留的目录数量
        expected_preserved_dirs = len([case for case in config["test_cases"] if not case.get("delete_later", True)])

        assert status_after["directories"] == expected_preserved_dirs, f"期望保留 {expected_preserved_dirs} 个目录，实际保留 {status_after['directories']} 个"
        log("✓ 真实配置测试通过")
            
    finally:
        # 恢复备份
        if backup_dir.exists():
            if save_dir.exists():
                shutil.rmtree(save_dir)
            shutil.move(str(backup_dir), str(save_dir))
            log(f"恢复备份目录")

        return True

def test_cleaner_edge_cases():
    """测试清理器边界情况"""
    log("测试清理器边界情况")
    
    test_cases = [
        # 空目录
        {"name": "空目录", "setup": lambda d: None},
        
        # 只有要删除的文件
        {"name": "只有要删除的文件", "setup": lambda d: _setup_delete_only(d)},
        
        # 只有要保留的文件
        {"name": "只有要保留的文件", "setup": lambda d: _setup_preserve_only(d)},
        
        # 混合文件
        {"name": "混合文件", "setup": lambda d: _setup_mixed_files(d)},
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_dir = Path(temp_dir) / "test_results"
                test_dir.mkdir()
                
                # 设置测试环境
                test_case["setup"](test_dir)
                
                # 执行清理 - 使用测试配置
                test_stocks = test_config.get_test_stocks()
                preserve_files = [
                    {"stock_code": stock.get('code'), "delete_later": i == 1}
                    for i, stock in enumerate(test_stocks)
                ]
                
                cleaner = CleanerTool(str(test_dir))
                result = cleaner.clean_test_directory(preserve_files)
                
                if result["status"] == "success":
                    log(f"✓ {test_case['name']} 测试通过")
                    passed += 1
                else:
                    log(f"✗ {test_case['name']} 测试失败")
                    
        except Exception as e:
            log(f"✗ {test_case['name']} 测试异常: {e}")
    
    assert passed == total, f"边界情况测试通过 {passed}/{total}"
    log("✓ 边界情况测试全部通过")
    return True

def _setup_delete_only(test_dir):
    """设置只有要删除的文件"""
    (test_dir / "CompanyB").mkdir()
    (test_dir / "CompanyB" / "file.pdf").write_text("test")

def _setup_preserve_only(test_dir):
    """设置只有要保留的文件"""
    (test_dir / "CompanyA").mkdir()
    (test_dir / "CompanyA" / "file.pdf").write_text("test")

def _setup_mixed_files(test_dir):
    """设置混合文件"""
    (test_dir / "CompanyA").mkdir()
    (test_dir / "CompanyB").mkdir()
    (test_dir / "CompanyA" / "preserve_file.pdf").write_text("test")
    (test_dir / "CompanyB" / "delete_file.pdf").write_text("test")
    (test_dir / "root_file.pdf").write_text("test")

def test_cleaner_dry_run():
    """测试清理器模拟运行功能"""
    log("测试清理器模拟运行功能")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_results"
        test_dir.mkdir()
        
        # 创建测试文件（使用英文名称避免编码问题）
        (test_dir / "CompanyA").mkdir()
        (test_dir / "CompanyB").mkdir()
        (test_dir / "CompanyA" / "file1.pdf").write_text("test")
        (test_dir / "CompanyB" / "file2.pdf").write_text("test")
        
        # 模拟运行 - 保留CompanyA，删除CompanyB
        preserve_files = [
            {"stock_code": "CompanyA", "delete_later": False},
            {"stock_code": "CompanyB", "delete_later": True}
        ]
        
        cleaner = CleanerTool(str(test_dir))
        result_dry = cleaner.clean_test_directory(preserve_files, dry_run=True)
        
        # 验证文件没有被实际删除（应该仍然是2个目录）
        status_after_dry = cleaner.get_directory_status()
        
        assert status_after_dry["directories"] == 2 and result_dry["dry_run"], "模拟运行测试失败"
        log("✓ 模拟运行测试通过")
        return True

def main():
    """主测试函数"""
    log("开始测试清理工具功能")
    
    tests = [
        ("基本功能测试", test_cleaner_basic_functionality),
        ("真实配置测试", test_cleaner_with_real_config),
        ("边界情况测试", test_cleaner_edge_cases),
        ("模拟运行测试", test_cleaner_dry_run),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        log(f"\n{'='*60}")
        log(f"运行测试: {test_name}")
        log(f"{'='*60}")
        
        try:
            if test_func():
                passed += 1
                log(f"PASS {test_name} 通过")
            else:
                log(f"FAIL {test_name} 失败")
        except Exception as e:
            log(f"ERROR {test_name} 异常: {e}")
    
    log(f"\n{'='*60}")
    log(f"测试总结: {passed}/{total} 通过")
    log(f"{'='*60}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)