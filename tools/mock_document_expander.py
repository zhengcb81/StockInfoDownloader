#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
模拟真实文档扩展工具
用于创建模拟的真实文档来扩展测试文档库
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from real_document_manager import RealDocumentManager, DocumentInfo


class MockDocumentExpander:
    """模拟文档扩展器"""

    def __init__(self, base_dir: str = "end2end_test"):
        """
        初始化模拟文档扩展器

        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self.expected_results_dir = self.base_dir / "expected_results"
        self.document_manager = RealDocumentManager(base_dir)

        # 模拟的真实文档数据
        self.mock_documents = [
            # 大盘股 - 平安银行
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "document_type": "research",
                "document_name": "平安银行：2024年投资者关系活动记录表.pdf",
                "file_size": 156789,  # 153KB
                "keywords": ["投资者关系", "调研"]
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "document_type": "annual_report",
                "document_name": "平安银行：2023年年度报告.pdf",
                "file_size": 3456789,  # 3.3MB
                "keywords": ["年度报告", "年报"]
            },
            {
                "stock_code": "000001",
                "stock_name": "平安银行",
                "document_type": "announcement",
                "document_name": "平安银行：2024年第一季度业绩预告.pdf",
                "file_size": 234567,  # 229KB
                "keywords": ["业绩预告", "公告"]
            },

            # 大盘股 - 万科A
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "document_type": "research",
                "document_name": "万科A：投资者关系管理信息20240815.pdf",
                "file_size": 189234,  # 185KB
                "keywords": ["投资者关系", "管理信息"]
            },
            {
                "stock_code": "000002",
                "stock_name": "万科A",
                "document_type": "semi_annual_report",
                "document_name": "万科A：2024年半年度报告.pdf",
                "file_size": 2876543,  # 2.7MB
                "keywords": ["半年度报告", "半年报"]
            },

            # 大盘股 - 海康威视
            {
                "stock_code": "002415",
                "stock_name": "海康威视",
                "document_type": "research",
                "document_name": "海康威视：2024年8月投资者调研纪要.pdf",
                "file_size": 345678,  # 337KB
                "keywords": ["投资者调研", "纪要"]
            },
            {
                "stock_code": "002415",
                "stock_name": "海康威视",
                "document_type": "announcement",
                "document_name": "海康威视：关于重大事项的公告.pdf",
                "file_size": 156789,  # 153KB
                "keywords": ["重大事项", "公告"]
            },

            # 小盘股 - 诺瓦星云
            {
                "stock_code": "301589",
                "stock_name": "诺瓦星云",
                "document_type": "research",
                "document_name": "诺瓦星云：投资者关系活动记录202407.pdf",
                "file_size": 123456,  # 121KB
                "keywords": ["投资者关系", "活动记录"]
            },
            {
                "stock_code": "301589",
                "stock_name": "诺瓦星云",
                "document_type": "quarterly_report",
                "document_name": "诺瓦星云：2024年第三季度报告.pdf",
                "file_size": 1987654,  # 1.9MB
                "keywords": ["季度报告", "三季度"]
            },

            # 小盘股 - 铖昌科技
            {
                "stock_code": "301628",
                "stock_name": "铖昌科技",
                "document_type": "research",
                "document_name": "铖昌科技：2024年投资者关系活动表.pdf",
                "file_size": 145678,  # 142KB
                "keywords": ["投资者关系", "活动表"]
            },

            # 不同行业 - 五粮液
            {
                "stock_code": "000858",
                "stock_name": "五粮液",
                "document_type": "research",
                "document_name": "五粮液：经销商调研活动记录.pdf",
                "file_size": 287654,  # 281KB
                "keywords": ["经销商调研", "活动记录"]
            },
            {
                "stock_code": "000858",
                "stock_name": "五粮液",
                "document_type": "announcement",
                "document_name": "五粮液：关于产品价格调整的公告.pdf",
                "file_size": 98765,  # 96KB
                "keywords": ["产品价格", "公告"]
            },

            # 新能源汽车 - 比亚迪
            {
                "stock_code": "002594",
                "stock_name": "比亚迪",
                "document_type": "research",
                "document_name": "比亚迪：2024年投资者关系活动记录表.pdf",
                "file_size": 298765,  # 292KB
                "keywords": ["投资者关系", "活动记录"]
            },
            {
                "stock_code": "002594",
                "stock_name": "比亚迪",
                "document_type": "quarterly_report",
                "document_name": "比亚迪：2024年第二季度报告.pdf",
                "file_size": 4567890,  # 4.4MB
                "keywords": ["季度报告", "二季度"]
            },

            # 电池行业 - 宁德时代
            {
                "stock_code": "300750",
                "stock_name": "宁德时代",
                "document_type": "research",
                "document_name": "宁德时代：技术路线投资者交流纪要.pdf",
                "file_size": 345678,  # 337KB
                "keywords": ["技术路线", "投资者交流"]
            },
            {
                "stock_code": "300750",
                "stock_name": "宁德时代",
                "document_type": "announcement",
                "document_name": "宁德时代：关于产能扩张的公告.pdf",
                "file_size": 187654,  # 183KB
                "keywords": ["产能扩张", "公告"]
            }
        ]

    def generate_mock_pdf_file(self, target_path: Path, document_info: Dict[str, Any]) -> str:
        """生成模拟PDF文件"""
        # 创建模拟的PDF内容（实际上是文本文件，但命名为.pdf）
        mock_content = f"""
模拟PDF文档内容
================

股票代码: {document_info['stock_code']}
股票名称: {document_info['stock_name']}
文档类型: {document_info['document_type']}
文档名称: {document_info['document_name']}
文件大小: {document_info['file_size']} bytes
关键词: {', '.join(document_info['keywords'])}

这是一个模拟的PDF文档，用于测试目的。
实际内容应该是真实的PDF文件，但为了快速演示，
这里使用文本文件模拟。

文档创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
文档用途: 端到端测试的预期结果文件

{"=" * 50}
文档详细内容模拟
{"=" * 50}

本文档模拟了真实的{document_info['document_type']}文档内容。
在实际使用中，这应该是一个从巨潮资讯网下载的真实PDF文档。

包含的关键词:
{chr(10).join(f"- {keyword}" for keyword in document_info['keywords'])}

文档大小信息:
- 预期大小: {document_info['file_size']} bytes
- 实际大小: 将在写入时调整

注意: 这是一个模拟文件，仅用于测试目的。
"""

        # 调整内容大小以达到目标文件大小
        current_size = len(mock_content.encode('utf-8'))
        target_size = document_info['file_size']

        if current_size < target_size:
            # 添加填充内容以达到目标大小
            padding_size = target_size - current_size
            padding = "\n" * (padding_size // 100)  # 每行约100字节
            mock_content += f"\n\n{'填充内容用于达到目标文件大小。' * 100}\n{padding}"

        # 确保目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(mock_content)

        # 验证文件大小
        actual_size = target_path.stat().st_size
        if abs(actual_size - target_size) > 1000:  # 允许1KB的差异
            print(f"警告: 文件大小差异较大 - 目标: {target_size}, 实际: {actual_size}")

        return self._calculate_file_hash(target_path)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def expand_mock_documents(self, target_count: int = 20) -> Dict[str, Any]:
        """扩展模拟文档"""
        print("开始扩展模拟文档库...")

        # 获取当前文档状态
        existing_docs = self.document_manager.scan_existing_documents()
        existing_codes = {doc.stock_code for doc in existing_docs}

        print(f"当前文档数: {len(existing_docs)}")
        print(f"已覆盖股票: {', '.join(existing_codes)}")
        print(f"目标文档数: {target_count}")

        results = {
            "existing_documents": len(existing_docs),
            "added_documents": 0,
            "skipped_documents": 0,
            "final_count": 0,
            "added_companies": set(),
            "added_document_types": set(),
            "errors": []
        }

        # 选择要添加的文档
        documents_to_add = []
        for mock_doc in self.mock_documents:
            if mock_doc['stock_code'] not in existing_codes or len(documents_to_add) < (target_count - len(existing_docs)):
                documents_to_add.append(mock_doc)

        # 限制添加数量
        max_add = target_count - len(existing_docs)
        documents_to_add = documents_to_add[:max_add]

        print(f"\n计划添加 {len(documents_to_add)} 个文档:")

        for mock_doc in documents_to_add:
            print(f"  {mock_doc['stock_name']} ({mock_doc['stock_code']}) - {mock_doc['document_type']}")

        # 创建文档
        for i, mock_doc in enumerate(documents_to_add):
            print(f"\n创建文档 {i+1}/{len(documents_to_add)}:")
            print(f"  股票: {mock_doc['stock_name']} ({mock_doc['stock_code']})")
            print(f"  类型: {mock_doc['document_type']}")
            print(f"  文件: {mock_doc['document_name']}")

            try:
                # 创建公司目录
                company_dir = self.expected_results_dir / mock_doc['stock_name']
                company_dir.mkdir(parents=True, exist_ok=True)

                # 创建文档文件
                file_path = company_dir / mock_doc['document_name']

                # 生成模拟PDF文件
                file_hash = self.generate_mock_pdf_file(file_path, mock_doc)

                # 创建DocumentInfo对象
                doc_info = DocumentInfo(
                    stock_code=mock_doc['stock_code'],
                    stock_name=mock_doc['stock_name'],
                    document_type=mock_doc['document_type'],
                    document_name=mock_doc['document_name'],
                    expected_keywords=mock_doc['keywords'],
                    file_size=file_path.stat().st_size,
                    file_hash=file_hash
                )

                # 注册文档
                self.document_manager.register_document(doc_info)

                results["added_documents"] += 1
                results["added_companies"].add(mock_doc['stock_name'])
                results["added_document_types"].add(mock_doc['document_type'])

                print(f"  [成功] 文档已创建并注册")

            except Exception as e:
                error_msg = f"创建文档失败: {e}"
                results["errors"].append(error_msg)
                print(f"  [失败] {error_msg}")

        # 重新扫描文档
        final_docs = self.document_manager.scan_existing_documents()
        results["final_count"] = len(final_docs)
        results["added_companies"] = list(results["added_companies"])
        results["added_document_types"] = list(results["added_document_types"])

        print(f"\n扩展完成:")
        print(f"  原有文档: {results['existing_documents']}")
        print(f"  新增文档: {results['added_documents']}")
        print(f"  最终文档数: {results['final_count']}")
        print(f"  新增公司: {', '.join(results['added_companies'])}")
        print(f"  新增文档类型: {', '.join(results['added_document_types'])}")
        print(f"  错误数: {len(results['errors'])}")

        return results


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='模拟真实文档扩展工具')
    parser.add_argument('--base-dir', default='end2end_test', help='基础目录路径')
    parser.add_argument('--target-count', type=int, default=20, help='目标文档数量')

    args = parser.parse_args()

    expander = MockDocumentExpander(args.base_dir)
    results = expander.expand_mock_documents(args.target_count)

    # 保存扩展结果
    result_file = Path(args.base_dir) / "mock_expansion_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        # 转换set为list以便JSON序列化
        serializable_results = results.copy()
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)

    print(f"\n扩展结果已保存到: {result_file}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())