#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
真实文档管理工具
用于管理端到端测试所需的真实PDF文档
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DocumentInfo:
    """文档信息类"""
    stock_code: str
    stock_name: str
    document_type: str
    document_name: str
    expected_keywords: List[str]
    file_size: int
    file_hash: str
    source_url: Optional[str] = None
    download_date: Optional[str] = None


class RealDocumentManager:
    """真实文档管理器"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化文档管理器

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.expected_dir = self.base_dir / "expected_results"
        self.document_catalog_file = self.base_dir / "document_catalog.json"

        # 创建必要目录
        self.expected_dir.mkdir(parents=True, exist_ok=True)

        # 加载文档目录
        self.document_catalog = self._load_document_catalog()

    def _load_document_catalog(self) -> Dict[str, DocumentInfo]:
        """加载文档目录"""
        if self.document_catalog_file.exists():
            try:
                with open(self.document_catalog_file, 'r', encoding='utf-8') as f:
                    catalog_data = json.load(f)

                catalog = {}
                for doc_id, doc_data in catalog_data.items():
                    catalog[doc_id] = DocumentInfo(**doc_data)
                return catalog
            except Exception as e:
                print(f"加载文档目录失败: {e}")

        return {}

    def _save_document_catalog(self):
        """保存文档目录"""
        catalog_data = {}
        for doc_id, doc_info in self.document_catalog.items():
            catalog_data[doc_id] = {
                'stock_code': doc_info.stock_code,
                'stock_name': doc_info.stock_name,
                'document_type': doc_info.document_type,
                'document_name': doc_info.document_name,
                'expected_keywords': doc_info.expected_keywords,
                'file_size': doc_info.file_size,
                'file_hash': doc_info.file_hash,
                'source_url': doc_info.source_url,
                'download_date': doc_info.download_date
            }

        with open(self.document_catalog_file, 'w', encoding='utf-8') as f:
            json.dump(catalog_data, f, ensure_ascii=False, indent=2)

    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希值"""
        if not file_path.exists():
            return ""

        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def scan_existing_documents(self) -> List[DocumentInfo]:
        """扫描现有文档"""
        existing_docs = []

        if not self.expected_dir.exists():
            return existing_docs

        # 扫描所有公司目录
        for company_dir in self.expected_dir.iterdir():
            if not company_dir.is_dir():
                continue

            company_name = company_dir.name

            # 扫描PDF文件
            for pdf_file in company_dir.glob("*.pdf"):
                file_size = pdf_file.stat().st_size
                file_hash = self.calculate_file_hash(pdf_file)

                # 从文件名解析信息
                doc_info = self._parse_document_info(
                    company_name, pdf_file.name, file_size, file_hash
                )

                if doc_info:
                    existing_docs.append(doc_info)
                    print(f"扫描到文档: {company_name}/{pdf_file.name} (大小: {file_size} bytes)")
                else:
                    print(f"警告: 无法解析文档信息: {company_name}/{pdf_file.name}")

        return existing_docs

    def _parse_document_info(self, company_name: str, filename: str,
                           file_size: int, file_hash: str) -> Optional[DocumentInfo]:
        """从文件名解析文档信息"""
        # 尝试从文件名中提取股票代码
        stock_code = None
        document_type = "unknown"

        # 常见的文档类型关键词
        report_keywords = {
            "年报": "annual_report",
            "半年报": "semi_annual_report",
            "一季度报告": "quarterly_report",
            "投资者关系": "research",
            "调研": "research",
            "公告": "announcement",
            "业绩预告": "earnings_forecast"
        }

        # 尝试匹配股票代码
        for code in ["300470", "301611", "000001", "002415"]:
            if code in filename:
                stock_code = code
                break

        # 如果没找到股票代码，尝试从公司名称推断
        if not stock_code:
            if "中密控股" in company_name:
                stock_code = "300470"
            elif "珂玛科技" in company_name:
                stock_code = "301611"

        # 确定文档类型
        for keyword, doc_type in report_keywords.items():
            if keyword in filename:
                document_type = doc_type
                break

        if not stock_code:
            return None

        # 提取关键词 - 包括预定义关键词和实际文件名中的关键词
        expected_keywords = []

        # 1. 提取预定义关键词
        for keyword in report_keywords.keys():
            if keyword in filename:
                expected_keywords.append(keyword)

        # 2. 提取文件名中的具体关键词（如日期、报告类型等）
        # 移除公司名称和股票代码部分，提取剩余内容作为关键词
        clean_filename = filename
        if "：" in clean_filename:
            clean_filename = clean_filename.split("：", 1)[1]  # 移除公司名称部分

        # 移除文件扩展名
        clean_filename = clean_filename.replace(".pdf", "")

        # 将剩余内容按空格或标点分割成关键词
        import re
        additional_keywords = re.split(r'[\s\-\:：（）()]', clean_filename)
        additional_keywords = [kw.strip() for kw in additional_keywords if kw.strip() and len(kw.strip()) > 2]

        expected_keywords.extend(additional_keywords)


        return DocumentInfo(
            stock_code=stock_code,
            stock_name=company_name,
            document_type=document_type,
            document_name=filename,
            expected_keywords=expected_keywords,
            file_size=file_size,
            file_hash=file_hash
        )

    def register_document(self, doc_info: DocumentInfo) -> str:
        """注册文档到目录"""
        doc_id = f"{doc_info.stock_code}_{doc_info.document_type}_{doc_info.file_hash[:8]}"

        self.document_catalog[doc_id] = doc_info
        self._save_document_catalog()

        return doc_id

    def validate_test_configuration(self, config_file: str) -> Tuple[bool, List[str]]:
        """验证测试配置的文档完整性"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            return False, [f"加载配置文件失败: {e}"]

        issues = []

        # 检查预期结果目录
        expected_dir = Path(config.get("expected_result_dir", ""))
        if not expected_dir.exists():
            issues.append(f"预期结果目录不存在: {expected_dir}")

        # 检查每个测试用例的文档
        test_cases = config.get("test_cases", [])
        for i, test_case in enumerate(test_cases, 1):
            stock_code = test_case.get("stock_code")
            allowed_keywords = test_case.get("allowed_keywords", [])

            # 查找匹配的文档
            matching_docs = self.find_matching_documents(stock_code, allowed_keywords)

            if not matching_docs:
                issues.append(
                    f"测试用例 {i} (股票代码: {stock_code}): "
                    f"未找到匹配的文档 (关键词: {allowed_keywords})"
                )
            else:
                print(f"测试用例 {i}: 找到 {len(matching_docs)} 个匹配文档")

        return len(issues) == 0, issues

    def find_matching_documents(self, stock_code: str, keywords: List[str]) -> List[DocumentInfo]:
        """查找匹配的文档"""
        matching_docs = []

        for doc_info in self.document_catalog.values():
            if doc_info.stock_code != stock_code:
                continue

            # 检查关键词匹配
            keyword_match = False
            for keyword in keywords:
                # 直接匹配
                if any(keyword == doc_keyword for doc_keyword in doc_info.expected_keywords):
                    keyword_match = True
                    break
                # 部分匹配 - 测试关键词包含在文档关键词中
                if any(keyword in doc_keyword for doc_keyword in doc_info.expected_keywords):
                    keyword_match = True
                    break
                # 部分匹配 - 文档关键词包含在测试关键词中
                if any(doc_keyword in keyword for doc_keyword in doc_info.expected_keywords):
                    keyword_match = True
                    break

            if keyword_match:
                matching_docs.append(doc_info)

        return matching_docs

    def get_document_path(self, doc_info: DocumentInfo) -> Path:
        """获取文档路径"""
        company_dir = self.expected_dir / doc_info.stock_name
        return company_dir / doc_info.document_name

    def copy_document_to_expected(self, source_file: Path, doc_info: DocumentInfo) -> bool:
        """复制文档到预期目录"""
        if not source_file.exists():
            print(f"源文件不存在: {source_file}")
            return False

        # 创建公司目录
        company_dir = self.expected_dir / doc_info.stock_name
        company_dir.mkdir(parents=True, exist_ok=True)

        target_file = company_dir / doc_info.document_name

        try:
            shutil.copy2(source_file, target_file)

            # 验证复制后的文件
            if target_file.exists():
                actual_size = target_file.stat().st_size
                actual_hash = self.calculate_file_hash(target_file)

                if actual_size == doc_info.file_size and actual_hash == doc_info.file_hash:
                    print(f"成功复制文档: {doc_info.document_name}")
                    return True
                else:
                    print(f"文档验证失败: {doc_info.document_name}")
                    target_file.unlink()  # 删除损坏的文件
                    return False
            else:
                print(f"复制失败: {doc_info.document_name}")
                return False

        except Exception as e:
            print(f"复制文档时出错: {e}")
            return False

    def generate_document_report(self) -> Dict[str, any]:
        """生成文档报告"""
        total_docs = len(self.document_catalog)

        # 按股票代码统计
        stock_stats = {}
        for doc_info in self.document_catalog.values():
            if doc_info.stock_code not in stock_stats:
                stock_stats[doc_info.stock_code] = {
                    'stock_name': doc_info.stock_name,
                    'document_count': 0,
                    'document_types': set()
                }

            stock_stats[doc_info.stock_code]['document_count'] += 1
            stock_stats[doc_info.stock_code]['document_types'].add(doc_info.document_type)

        # 按文档类型统计
        type_stats = {}
        for doc_info in self.document_catalog.values():
            if doc_info.document_type not in type_stats:
                type_stats[doc_info.document_type] = 0
            type_stats[doc_info.document_type] += 1

        return {
            'total_documents': total_docs,
            'stock_statistics': stock_stats,
            'type_statistics': type_stats,
            'catalog_file': str(self.document_catalog_file)
        }


def main():
    """主函数"""
    manager = RealDocumentManager()

    print("=== 真实文档管理工具 ===")
    print(f"基础目录: {manager.base_dir}")
    print(f"预期目录: {manager.expected_dir}")

    # 扫描现有文档
    print("\n扫描现有文档...")
    existing_docs = manager.scan_existing_documents()
    print(f"找到 {len(existing_docs)} 个文档")

    # 注册文档
    for doc_info in existing_docs:
        doc_id = manager.register_document(doc_info)
        print(f"注册文档: {doc_id} - {doc_info.document_name}")

    # 验证测试配置
    print("\n验证测试配置...")
    config_file = "config_end2end_test.json"
    if Path(config_file).exists():
        valid, issues = manager.validate_test_configuration(config_file)
        if valid:
            print("测试配置验证通过")
        else:
            print("测试配置验证失败:")
            for issue in issues:
                print(f"  - {issue}")
    else:
        print(f"配置文件不存在: {config_file}")

    # 生成报告
    print("\n生成文档报告...")
    report = manager.generate_document_report()
    print(f"总文档数: {report['total_documents']}")
    print("股票统计:")
    for stock_code, stats in report['stock_statistics'].items():
        print(f"  - {stock_code} ({stats['stock_name']}): {stats['document_count']} 个文档")

    print("文档类型统计:")
    for doc_type, count in report['type_statistics'].items():
        print(f"  - {doc_type}: {count} 个")


if __name__ == "__main__":
    main()