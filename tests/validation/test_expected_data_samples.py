#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
期待数据样本库的单元测试
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from tests.validation.expected_data_samples import (
    ExpectedDataSampleLibrary,
    SampleType,
)


class TestExpectedDataSampleLibrary:
    """期待数据样本库测试类"""

    def setup_method(self):
        """测试设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.library = ExpectedDataSampleLibrary(self.temp_dir)

    def teardown_method(self):
        """测试清理"""
        self.library.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """测试初始化"""
        assert self.library.base_dir.exists()
        assert self.library.samples_dir.exists()

        # 验证样本数量
        assert len(self.library.samples) == 6

        # 验证样本类型
        sample_names = list(self.library.samples.keys())
        assert "basic_sample" in sample_names
        assert "complete_sample" in sample_names
        assert "partial_sample" in sample_names
        assert "corrupted_sample" in sample_names
        assert "extra_sample" in sample_names
        assert "missing_sample" in sample_names

    def test_get_sample(self):
        """测试获取样本"""
        sample = self.library.get_sample("basic_sample")
        assert sample is not None
        assert sample.name == "basic_sample"
        assert sample.description == "基础样本 - 包含标准股票数据的完整文件集"
        assert sample.sample_type == SampleType.BASIC
        assert len(sample.stock_codes) == 3
        assert sample.expected_files_per_stock == 4

        # 测试不存在的样本
        nonexistent_sample = self.library.get_sample("nonexistent_sample")
        assert nonexistent_sample is None

    def test_get_all_samples(self):
        """测试获取所有样本"""
        all_samples = self.library.get_all_samples()
        assert len(all_samples) == 6

        sample_names = [sample.name for sample in all_samples]
        assert "basic_sample" in sample_names
        assert "complete_sample" in sample_names

    def test_get_sample_path(self):
        """测试获取样本路径"""
        sample_path = self.library.get_sample_path("basic_sample")
        assert sample_path is not None
        assert sample_path.exists()
        assert sample_path.name == "basic_sample"

        # 测试不存在的样本路径
        nonexistent_path = self.library.get_sample_path("nonexistent_sample")
        assert nonexistent_path is None

    def test_get_expected_data_path(self):
        """测试获取期待数据路径"""
        expected_path = self.library.get_expected_data_path("basic_sample")
        assert expected_path is not None
        assert expected_path.exists()
        assert expected_path.name == "expected_data"

        # 验证期待数据内容
        stock_dirs = list(expected_path.iterdir())
        assert len(stock_dirs) == 3  # 3个股票

        for stock_dir in stock_dirs:
            assert stock_dir.is_dir()
            pdf_files = list(stock_dir.glob("*.pdf"))
            assert len(pdf_files) == 4  # 每个股票4个文件

    def test_create_test_scenario(self):
        """测试创建测试场景"""
        actual_data_dir = str(Path(self.temp_dir) / "actual_data")

        scenario = self.library.create_test_scenario("basic_sample", actual_data_dir)
        assert scenario is not None
        assert scenario["sample_name"] == "basic_sample"
        assert scenario["sample_type"] == "basic"
        assert scenario["actual_data_dir"] == actual_data_dir
        assert len(scenario["stock_codes"]) == 3
        assert "validation_rules" in scenario

        # 验证期待数据目录存在
        expected_data_dir = Path(scenario["expected_data_dir"])
        assert expected_data_dir.exists()

        # 测试不存在的样本
        nonexistent_scenario = self.library.create_test_scenario(
            "nonexistent_sample", actual_data_dir
        )
        assert nonexistent_scenario == {}

    def test_sample_data_creation(self):
        """测试样本数据创建"""
        # 测试基础样本
        basic_sample = self.library.get_sample("basic_sample")
        basic_path = self.library.get_expected_data_path("basic_sample")

        assert basic_path.exists()

        # 验证股票目录
        stock_dirs = list(basic_path.iterdir())
        assert len(stock_dirs) == len(basic_sample.stock_codes)

        for stock_dir in stock_dirs:
            pdf_files = list(stock_dir.glob("*.pdf"))
            assert len(pdf_files) == basic_sample.expected_files_per_stock

            # 验证文件大小
            for pdf_file in pdf_files:
                file_size = pdf_file.stat().st_size
                assert file_size > 0

    def test_complete_sample(self):
        """测试完整样本"""
        complete_sample = self.library.get_sample("complete_sample")
        complete_path = self.library.get_expected_data_path("complete_sample")

        assert complete_path.exists()

        # 验证股票数量
        stock_dirs = list(complete_path.iterdir())
        assert len(stock_dirs) == len(complete_sample.stock_codes)

        # 验证文件数量
        for stock_dir in stock_dirs:
            pdf_files = list(stock_dir.glob("*.pdf"))
            assert len(pdf_files) == complete_sample.expected_files_per_stock

    def test_partial_sample(self):
        """测试部分样本"""
        partial_sample = self.library.get_sample("partial_sample")
        partial_path = self.library.get_expected_data_path("partial_sample")

        assert partial_path.exists()

        # 验证股票数量
        stock_dirs = list(partial_path.iterdir())
        assert len(stock_dirs) == len(partial_sample.stock_codes)

        # 验证文件数量（部分样本只有2个文件）
        for stock_dir in stock_dirs:
            pdf_files = list(stock_dir.glob("*.pdf"))
            assert len(pdf_files) == partial_sample.expected_files_per_stock

    def test_corrupted_sample(self):
        """测试损坏样本"""
        corrupted_sample = self.library.get_sample("corrupted_sample")
        corrupted_path = self.library.get_expected_data_path("corrupted_sample")

        assert corrupted_path.exists()

        # 验证文件大小差异
        stock_dir = list(corrupted_path.iterdir())[0]  # 只有一个股票
        pdf_files = list(stock_dir.glob("*.pdf"))

        file_sizes = [f.stat().st_size for f in pdf_files]

        # 应该有不同大小的文件
        assert len(set(file_sizes)) > 1

    def test_export_sample(self):
        """测试导出样本"""
        export_dir = Path(self.temp_dir) / "export"

        # 导出基础样本
        export_path = self.library.export_sample("basic_sample", str(export_dir))

        assert export_path != ""
        assert Path(export_path).exists()

        # 验证导出内容
        config_file = Path(export_path) / "sample_config.json"
        assert config_file.exists()

        expected_data_dir = Path(export_path) / "expected_data"
        assert expected_data_dir.exists()

        # 测试导出不存在的样本
        nonexistent_export = self.library.export_sample(
            "nonexistent_sample", str(export_dir)
        )
        assert nonexistent_export == ""

    def test_export_all_samples(self):
        """测试导出所有样本"""
        export_dir = Path(self.temp_dir) / "export_all"

        export_path = self.library.export_all_samples(str(export_dir))

        assert export_path != ""
        assert Path(export_path).exists()

        # 验证库配置
        config_file = Path(export_path) / "library_config.json"
        assert config_file.exists()

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert config["total_samples"] == 6
        assert "samples" in config

        # 验证样本目录
        for sample_name in self.library.samples.keys():
            sample_dir = Path(export_path) / sample_name
            assert sample_dir.exists()

    def test_sample_config_files(self):
        """测试样本配置文件"""
        # 验证每个样本都有配置文件
        for sample_name in self.library.samples.keys():
            sample_path = self.library.get_sample_path(sample_name)
            config_file = sample_path / "sample_config.json"

            assert config_file.exists()

            # 验证配置内容
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "name" in config
            assert "description" in config
            assert "sample_type" in config
            assert "stock_codes" in config
            assert "expected_files_per_stock" in config
            assert "file_sizes" in config
            assert "validation_rules" in config

    def test_cleanup(self):
        """测试清理功能"""
        # 创建一些测试文件
        test_file = self.library.base_dir / "test_file.txt"
        with open(test_file, "w") as f:
            f.write("test content")

        assert test_file.exists()

        # 执行清理
        self.library.cleanup()

        # 验证目录被清理
        assert not self.library.base_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
