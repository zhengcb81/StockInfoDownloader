#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
期待数据与实际数据比较测试
集成期待数据验证框架的组件集成测试（使用mock对象）
注意：这不是真正的端到端测试，真正的端到端测试是 e2e_test.py
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# 避免直接导入可能导致初始化问题的模块
from tests.validation.expected_data_validator import (
    ComparisonMode,
    ExpectedDataValidator,
    validate_expected_vs_actual,
    validate_test_case,
)

# 测试股票数据
test_stocks = [
    {"code": "300470", "name": "中密控股", "org_id": "gssz0000470"},
    {"code": "000001", "name": "平安银行", "org_id": "9900000001"},
    {"code": "002415", "name": "海康威视", "org_id": "9900002415"},
]


@pytest.mark.integration
class TestExpectedDataValidationIntegration:
    """期待数据验证组件集成测试类（使用mock对象）"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_dir = os.path.join(self.temp_dir, "downloads")
        self.expected_data_dir = os.path.join(self.temp_dir, "expected_data")

        # 创建目录结构
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.expected_data_dir, exist_ok=True)

        # 创建测试映射文件
        self.mapping_file = os.path.join(self.temp_dir, "test_mapping.json")
        test_mapping = {}

        for stock in test_stocks:
            test_mapping[stock["code"]] = {
                "orgId": stock["org_id"],
                "name": stock["name"],
            }

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(test_mapping, f, ensure_ascii=False, indent=2)

        # 创建期待数据样本
        self._create_expected_data_samples()

        # 初始化验证器
        self.validator = ExpectedDataValidator(ComparisonMode.STRICT)

    def teardown_method(self):
        """测试清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_expected_data_samples(self):
        """创建期待数据样本"""
        # 为每个测试股票创建期待数据目录
        for stock in test_stocks:
            stock_dir = os.path.join(self.expected_data_dir, stock["name"])
            os.makedirs(stock_dir, exist_ok=True)

            # 创建模拟的PDF文件（使用实际内容模拟）
            pdf_content = self._generate_mock_pdf_content(stock)

            # 创建不同类型的报告文件
            report_types = ["一季度报告", "半年报", "年报", "投资者关系活动"]

            for report_type in report_types:
                filename = f"{stock['name']}：{stock['code']}{report_type}.pdf"
                filepath = os.path.join(stock_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(pdf_content)

    def _generate_mock_pdf_content(self, stock):
        """生成模拟的PDF内容"""
        # 创建包含股票信息的模拟PDF内容
        content = f"""
        %PDF-1.4
        1 0 obj
        <<
        /Type /Catalog
        /Pages 2 0 R
        >>
        endobj
        
        2 0 obj
        <<
        /Type /Pages
        /Kids [3 0 R]
        /Count 1
        >>
        endobj
        
        3 0 obj
        <<
        /Type /Page
        /Parent 2 0 R
        /MediaBox [0 0 612 792]
        /Contents 4 0 R
        /Resources <<
            /Font <<
                /F1 5 0 R
            >>
        >>
        >>
        endobj
        
        4 0 obj
        <<
        /Length 100
        >>
        stream
        BT
        /F1 12 Tf
        50 700 Td
        ({stock['name']} ({stock['code']}) 报告) Tj
        ET
        endstream
        endobj
        
        5 0 obj
        <<
        /Type /Font
        /Subtype /Type1
        /BaseFont /Helvetica
        >>
        endobj
        
        xref
        0 6
        0000000000 65535 f 
        0000000009 00000 n 
        0000000058 00000 n 
        0000000115 00000 n 
        0000000234 00000 n 
        0000000415 00000 n 
        trailer
        <<
        /Size 6
        /Root 1 0 R
        >>
        startxref
        500
        %%EOF
        """.encode("utf-8")

        return content

    def _simulate_download(self, stock_code, download_dir):
        """模拟下载过程"""
        # 查找对应的股票信息
        stock_info = next((s for s in test_stocks if s["code"] == stock_code), None)
        if not stock_info:
            return []

        # 创建股票目录
        stock_save_dir = os.path.join(download_dir, stock_info["name"])
        os.makedirs(stock_save_dir, exist_ok=True)

        # 模拟下载文件 - 下载所有期待数据文件以确保匹配
        downloaded_files = []
        report_types = ["一季度报告", "半年报", "年报", "投资者关系活动"]

        for report_type in report_types:
            filename = f"{stock_info['name']}：{stock_info['code']}{report_type}.pdf"
            filepath = os.path.join(stock_save_dir, filename)

            # 从期待数据复制文件作为模拟下载
            expected_file = os.path.join(
                self.expected_data_dir, stock_info["name"], filename
            )

            if os.path.exists(expected_file):
                shutil.copy2(expected_file, filepath)
                downloaded_files.append(filepath)

        return downloaded_files

    def test_expected_vs_actual_validation_strict_mode(self):
        """测试严格模式下的期待数据与实际数据验证"""
        # 模拟下载过程 - 只下载一个股票
        downloaded_files = self._simulate_download(
            test_stocks[0]["code"], self.save_dir
        )

        # 执行验证
        result = self.validator.validate_expected_data(
            Path(self.expected_data_dir), Path(self.save_dir)
        )

        # 验证结果 - 由于我们只下载了一个股票，其他股票目录会缺失
        # 在严格模式下，这会导致整体失败，但我们可以验证下载的股票数据正确
        assert result.total_files_compared > 0

        # 找到实际下载的股票目录结果
        downloaded_stock_result = None
        for dir_result in result.directory_results:
            if dir_result.actual_exists and dir_result.directory_path.endswith(
                test_stocks[0]["name"]
            ):
                downloaded_stock_result = dir_result
                break

        assert downloaded_stock_result is not None, "应该找到下载的股票目录结果"
        assert downloaded_stock_result.is_match() is True, "下载的股票目录应该匹配"
        assert len(downloaded_stock_result.file_comparisons) == len(downloaded_files)

        for file_comp in downloaded_stock_result.file_comparisons:
            assert file_comp.is_match() is True
            assert file_comp.content_match is True

    def test_expected_vs_actual_validation_lenient_mode(self):
        """测试宽松模式下的期待数据与实际数据验证"""
        # 使用宽松模式验证器
        lenient_validator = ExpectedDataValidator(ComparisonMode.LENIENT)

        # 模拟下载过程
        downloaded_files = self._simulate_download(
            test_stocks[1]["code"], self.save_dir
        )

        # 执行验证
        result = lenient_validator.validate_expected_data(
            Path(self.expected_data_dir), Path(self.save_dir)
        )

        # 验证结果 - 宽松模式下应该能处理缺失目录
        assert result.total_files_compared > 0

        # 找到实际下载的股票目录结果
        downloaded_stock_result = None
        for dir_result in result.directory_results:
            if dir_result.actual_exists and dir_result.directory_path.endswith(
                test_stocks[1]["name"]
            ):
                downloaded_stock_result = dir_result
                break

        assert downloaded_stock_result is not None, "应该找到下载的股票目录结果"
        assert downloaded_stock_result.is_match() is True, "下载的股票目录应该匹配"

    def test_single_test_case_validation(self):
        """测试单个测试用例的验证"""
        # 模拟下载过程
        downloaded_files = self._simulate_download(
            test_stocks[2]["code"], self.save_dir
        )

        # 定义测试用例
        test_case = {
            "stock_code": test_stocks[2]["code"],
            "suffix": "research",
            "allowed_keywords": ["一季度报告", "半年报", "投资者关系活动"],
        }

        # 执行验证
        result = self.validator.validate_single_test_case(
            test_case, Path(self.expected_data_dir), Path(self.save_dir)
        )

        # 验证结果 - 单个测试用例验证应该只关注指定的股票
        assert result.overall_success is True
        assert result.total_files_compared > 0
        assert result.files_matched == len(downloaded_files)
        assert result.success_rate == 100.0

    def test_validation_with_missing_files(self):
        """测试文件缺失情况下的验证"""
        # 只下载部分文件
        stock_info = test_stocks[0]
        stock_save_dir = os.path.join(self.save_dir, stock_info["name"])
        os.makedirs(stock_save_dir, exist_ok=True)

        # 只下载一季度报告
        filename = f"{stock_info['name']}：{stock_info['code']}一季度报告.pdf"
        expected_file = os.path.join(
            self.expected_data_dir, stock_info["name"], filename
        )
        actual_file = os.path.join(stock_save_dir, filename)

        if os.path.exists(expected_file):
            shutil.copy2(expected_file, actual_file)

        # 执行验证
        result = self.validator.validate_expected_data(
            Path(self.expected_data_dir), Path(self.save_dir)
        )

        # 验证结果（应该有缺失文件）
        assert result.overall_success is False
        assert result.files_missing > 0
        assert result.success_rate < 100.0

    def test_validation_with_extra_files(self):
        """测试额外文件情况下的验证"""
        # 创建一个新的公司目录来测试额外文件
        extra_company_dir = os.path.join(self.save_dir, "额外公司")
        os.makedirs(extra_company_dir, exist_ok=True)

        # 在额外公司目录中添加文件
        extra_file = os.path.join(extra_company_dir, "额外文件.pdf")
        with open(extra_file, "wb") as f:
            f.write(b"Extra file content")

        # 执行验证
        result = self.validator.validate_expected_data(
            Path(self.expected_data_dir), Path(self.save_dir)
        )

        # 验证结果（应该有额外文件）
        assert result.overall_success is False
        assert result.files_extra > 0
        assert result.success_rate < 100.0

        # 验证错误消息包含额外公司信息
        extra_company_found = False
        for error_msg in result.error_messages:
            if "多余的公司目录" in error_msg and "额外公司" in error_msg:
                extra_company_found = True
                break

        assert extra_company_found, "应该检测到多余的公司目录"

    def test_convenience_functions(self):
        """测试便捷验证函数"""
        # 模拟下载过程
        downloaded_files = self._simulate_download(
            test_stocks[0]["code"], self.save_dir
        )

        # 测试便捷验证函数
        result = validate_expected_vs_actual(
            self.expected_data_dir, self.save_dir, "strict"
        )

        # 验证结果 - 便捷函数应该能正常工作
        assert result.total_files_compared > 0

        # 找到实际下载的股票目录结果
        downloaded_stock_result = None
        for dir_result in result.directory_results:
            if dir_result.actual_exists and dir_result.directory_path.endswith(
                test_stocks[0]["name"]
            ):
                downloaded_stock_result = dir_result
                break

        assert downloaded_stock_result is not None, "应该找到下载的股票目录结果"

        # 测试测试用例验证函数
        test_case = {"stock_code": test_stocks[0]["code"], "suffix": "research"}

        result = validate_test_case(
            test_case, self.expected_data_dir, self.save_dir, "strict"
        )

        # 验证结果 - 单个测试用例验证应该成功
        assert result.overall_success is True
        assert result.total_files_compared > 0

    def test_validation_error_handling(self):
        """测试验证错误处理"""
        # 测试不存在的目录
        result = self.validator.validate_expected_data(
            Path("/nonexistent/expected"), Path(self.save_dir)
        )

        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "期待数据目录不存在" in result.error_messages[0]

        # 测试不存在的实际目录
        result = self.validator.validate_expected_data(
            Path(self.expected_data_dir), Path("/nonexistent/actual")
        )

        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "实际数据目录不存在" in result.error_messages[0]

        # 测试无效的测试用例
        invalid_test_case = {"suffix": "research"}  # 缺少股票代码

        result = self.validator.validate_single_test_case(
            invalid_test_case, Path(self.expected_data_dir), Path(self.save_dir)
        )

        assert result.overall_success is False
        assert len(result.error_messages) > 0
        assert "测试用例缺少股票代码" in result.error_messages[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
