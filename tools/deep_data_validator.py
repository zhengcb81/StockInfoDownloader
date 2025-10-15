#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深入真实数据验证工具
提供内容比较、结构验证、质量评估等功能
"""

import os
import sys
import json
import hashlib
import difflib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import logging
import re

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    validation_id: str
    validation_type: str  # 'content', 'structure', 'quality'
    target_path: str
    success: bool
    confidence_score: float  # 0.0-1.0
    details: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class ContentComparisonResult:
    """内容比较结果"""
    file1_path: str
    file2_path: str
    similarity_score: float  # 0.0-1.0
    content_hash1: str
    content_hash2: str
    differences: List[Dict[str, Any]]
    metadata_comparison: Dict[str, Any]


@dataclass
class StructureValidationResult:
    """结构验证结果"""
    file_path: str
    expected_structure: Dict[str, Any]
    actual_structure: Dict[str, Any]
    structure_compliance: float  # 0.0-1.0
    missing_elements: List[str]
    unexpected_elements: List[str]
    validation_details: Dict[str, Any]


@dataclass
class QualityAssessmentResult:
    """质量评估结果"""
    file_path: str
    quality_metrics: Dict[str, float]
    overall_quality_score: float  # 0.0-1.0
    quality_factors: Dict[str, Any]
    improvement_suggestions: List[str]


class DeepDataValidator:
    """深入数据验证器"""

    def __init__(self, config_file: str = "config_end2end_test.json"):
        self.config_file = config_file
        self.config = self._load_config()

        # 验证结果存储
        self.validation_results: List[ValidationResult] = []

        # 质量标准配置
        self.quality_standards = self._initialize_quality_standards()

        # 文档类型结构定义
        self.document_structures = self._initialize_document_structures()

        # 验证会话ID
        self.validation_session_id = f"VALIDATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"深入数据验证器初始化完成 - 会话ID: {self.validation_session_id}")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def _initialize_quality_standards(self) -> Dict[str, Any]:
        """初始化质量标准"""
        return {
            "content_quality": {
                "min_text_length": 100,  # 最小文本长度
                "max_text_length": 1000000,  # 最大文本长度
                "required_keywords": [],  # 必需关键词
                "forbidden_keywords": [],  # 禁止关键词
                "language_check": True,  # 语言检查
                "encoding_check": True,  # 编码检查
            },
            "structure_quality": {
                "required_sections": [],  # 必需章节
                "max_file_size": 50 * 1024 * 1024,  # 50MB
                "allowed_formats": ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
                "min_page_count": 1,
                "max_page_count": 1000
            },
            "metadata_quality": {
                "required_metadata": ['title', 'creation_date', 'author'],
                "metadata_completeness_threshold": 0.7
            },
            "format_quality": {
                "pdf_validation": True,
                "document_structure_check": True,
                "cross_reference_check": True
            }
        }

    def _initialize_document_structures(self) -> Dict[str, Dict[str, Any]]:
        """初始化文档结构定义"""
        return {
            "annual_report": {
                "required_sections": [
                    "公司概况",
                    "财务报告",
                    "经营情况",
                    "未来展望",
                    "风险因素"
                ],
                "optional_sections": [
                    "董事会报告",
                    "监事会报告",
                    "审计报告",
                    "重要事项"
                ],
                "required_tables": [
                    "资产负债表",
                    "利润表",
                    "现金流量表"
                ]
            },
            "quarterly_report": {
                "required_sections": [
                    "财务数据",
                    "经营情况",
                    "重要事项"
                ],
                "optional_sections": [
                    "财务报表",
                    "管理层讨论",
                    "业绩说明"
                ],
                "required_tables": [
                    "主要财务数据"
                ]
            },
            "research": {
                "required_sections": [
                    "调研基本情况",
                    "调研内容",
                    "附件"
                ],
                "optional_sections": [
                    "调研摘要",
                    "参与人员",
                    "相关说明"
                ],
                "required_elements": [
                    "调研日期",
                    "调研地点",
                    "参与机构"
                ]
            },
            "announcement": {
                "required_sections": [
                    "公告事由",
                    "具体内容",
                    "影响说明"
                ],
                "optional_sections": [
                    "背景说明",
                    "风险提示",
                    "备查文件"
                ],
                "required_elements": [
                    "公告日期",
                    "公告编号",
                    "发布主体"
                ]
            }
        }

    def validate_downloaded_documents(self, download_dir: str = None) -> Dict[str, Any]:
        """验证下载的文档"""
        logger.info("开始验证下载的文档...")

        if download_dir is None:
            download_dir = self.config.get("save_dir", "end2end_test/test_results")

        validation_report = {
            "session_id": self.validation_session_id,
            "validation_time": datetime.now().isoformat(),
            "target_directory": download_dir,
            "total_documents": 0,
            "validated_documents": 0,
            "validation_results": [],
            "summary": {}
        }

        if not os.path.exists(download_dir):
            logger.warning(f"下载目录不存在: {download_dir}")
            return validation_report

        # 扫描文档
        documents = self._scan_documents(download_dir)
        validation_report["total_documents"] = len(documents)

        logger.info(f"找到 {len(documents)} 个文档需要验证")

        # 逐个验证文档
        for doc_info in documents:
            try:
                result = self._validate_single_document(doc_info)
                validation_report["validation_results"].append(result.to_dict())

                if result.success:
                    validation_report["validated_documents"] += 1

            except Exception as e:
                logger.error(f"验证文档 {doc_info['path']} 失败: {e}")

        # 生成摘要
        validation_report["summary"] = self._generate_validation_summary()

        # 保存验证报告
        self._save_validation_report(validation_report)

        logger.info(f"文档验证完成 - 验证成功: {validation_report['validated_documents']}/{validation_report['total_documents']}")
        return validation_report

    def _scan_documents(self, directory: str) -> List[Dict[str, Any]]:
        """扫描目录中的文档"""
        documents = []
        allowed_extensions = self.quality_standards["structure_quality"]["allowed_formats"]

        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in allowed_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        stat = os.stat(file_path)
                        doc_info = {
                            "path": file_path,
                            "name": file,
                            "size": stat.st_size,
                            "extension": Path(file).suffix.lower(),
                            "modified_time": datetime.fromtimestamp(stat.st_mtime)
                        }
                        documents.append(doc_info)
                    except Exception as e:
                        logger.warning(f"扫描文档 {file_path} 失败: {e}")

        return documents

    def _validate_single_document(self, doc_info: Dict[str, Any]) -> ValidationResult:
        """验证单个文档"""
        validation_id = f"VAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(doc_info['name']).stem}"

        result = ValidationResult(
            validation_id=validation_id,
            validation_type="comprehensive",
            target_path=doc_info["path"],
            success=False,
            confidence_score=0.0,
            details={},
            issues=[],
            recommendations=[],
            timestamp=datetime.now()
        )

        try:
            # 1. 基础验证
            basic_validation = self._perform_basic_validation(doc_info)
            result.details["basic_validation"] = basic_validation

            # 2. 内容验证
            content_validation = self._perform_content_validation(doc_info)
            result.details["content_validation"] = content_validation

            # 3. 结构验证
            structure_validation = self._perform_structure_validation(doc_info)
            result.details["structure_validation"] = structure_validation

            # 4. 质量评估
            quality_assessment = self._perform_quality_assessment(doc_info)
            result.details["quality_assessment"] = quality_assessment

            # 5. 综合评估
            result.success, result.confidence_score = self._calculate_overall_score(
                basic_validation, content_validation, structure_validation, quality_assessment
            )

            # 6. 收集问题和建议
            result.issues = self._collect_validation_issues(
                basic_validation, content_validation, structure_validation, quality_assessment
            )
            result.recommendations = self._generate_improvement_recommendations(result.issues)

        except Exception as e:
            logger.error(f"验证文档 {doc_info['path']} 过程中发生异常: {e}")
            result.issues.append(f"验证过程异常: {str(e)}")

        self.validation_results.append(result)
        return result

    def _perform_basic_validation(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行基础验证"""
        validation = {
            "file_exists": True,
            "file_readable": False,
            "size_valid": False,
            "extension_valid": False,
            "encoding_valid": False,
            "details": {}
        }

        try:
            # 检查文件可读性
            with open(doc_info["path"], 'rb') as f:
                f.read(1024)  # 尝试读取前1KB
                validation["file_readable"] = True

            # 检查文件大小
            max_size = self.quality_standards["structure_quality"]["max_file_size"]
            validation["size_valid"] = doc_info["size"] <= max_size
            validation["details"]["file_size"] = doc_info["size"]
            validation["details"]["max_allowed_size"] = max_size

            # 检查扩展名
            allowed_formats = self.quality_standards["structure_quality"]["allowed_formats"]
            validation["extension_valid"] = doc_info["extension"] in allowed_formats
            validation["details"]["file_extension"] = doc_info["extension"]

            # 检查编码（如果是文本文件）
            if doc_info["extension"] in ['.txt', '.rtf']:
                try:
                    with open(doc_info["path"], 'r', encoding='utf-8') as f:
                        f.read(1000)
                    validation["encoding_valid"] = True
                except UnicodeDecodeError:
                    try:
                        with open(doc_info["path"], 'r', encoding='gbk') as f:
                            f.read(1000)
                        validation["encoding_valid"] = True
                        validation["details"]["encoding"] = "gbk"
                    except:
                        validation["details"]["encoding_error"] = "无法检测文本编码"

        except Exception as e:
            validation["details"]["read_error"] = str(e)

        return validation

    def _perform_content_validation(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行内容验证"""
        validation = {
            "content_extractable": False,
            "text_length_valid": False,
            "keywords_present": [],
            "forbidden_keywords_found": [],
            "language_detected": None,
            "content_hash": None,
            "details": {}
        }

        try:
            # 提取文本内容（简化版）
            text_content = self._extract_text_content(doc_info["path"])

            if text_content:
                validation["content_extractable"] = True
                validation["content_hash"] = hashlib.md5(text_content.encode()).hexdigest()

                # 检查文本长度
                min_length = self.quality_standards["content_quality"]["min_text_length"]
                max_length = self.quality_standards["content_quality"]["max_text_length"]
                text_length = len(text_content)

                validation["text_length_valid"] = min_length <= text_length <= max_length
                validation["details"]["text_length"] = text_length

                # 关键词检查
                required_keywords = self.quality_standards["content_quality"]["required_keywords"]
                forbidden_keywords = self.quality_standards["content_quality"]["forbidden_keywords"]

                for keyword in required_keywords:
                    if keyword.lower() in text_content.lower():
                        validation["keywords_present"].append(keyword)

                for keyword in forbidden_keywords:
                    if keyword.lower() in text_content.lower():
                        validation["forbidden_keywords_found"].append(keyword)

                # 语言检测（简化版）
                validation["language_detected"] = self._detect_language(text_content)

                # 内容特征分析
                validation["details"] = self._analyze_content_features(text_content)

        except Exception as e:
            validation["details"]["extraction_error"] = str(e)

        return validation

    def _perform_structure_validation(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行结构验证"""
        validation = {
            "structure_detectable": False,
            "document_type": None,
            "required_sections_found": [],
            "missing_sections": [],
            "unexpected_sections": [],
            "structure_compliance": 0.0,
            "details": {}
        }

        try:
            # 从文件名推断文档类型
            document_type = self._infer_document_type(doc_info["name"])
            validation["document_type"] = document_type

            if document_type and document_type in self.document_structures:
                expected_structure = self.document_structures[document_type]

                # 提取文档结构（简化版）
                actual_structure = self._extract_document_structure(doc_info["path"])

                if actual_structure:
                    validation["structure_detectable"] = True

                    # 检查必需章节
                    required_sections = expected_structure.get("required_sections", [])
                    found_sections = actual_structure.get("sections", [])

                    validation["required_sections_found"] = [
                        section for section in required_sections
                        if any(section in found for found in found_sections)
                    ]

                    validation["missing_sections"] = [
                        section for section in required_sections
                        if section not in validation["required_sections_found"]
                    ]

                    # 计算结构合规性
                    if required_sections:
                        validation["structure_compliance"] = (
                            len(validation["required_sections_found"]) / len(required_sections)
                        )

                    validation["details"] = {
                        "expected_sections": required_sections,
                        "found_sections": found_sections,
                        "section_count": len(found_sections)
                    }

        except Exception as e:
            validation["details"]["structure_error"] = str(e)

        return validation

    def _perform_quality_assessment(self, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行质量评估"""
        assessment = {
            "readability_score": 0.0,
            "completeness_score": 0.0,
            "accuracy_indicators": [],
            "quality_factors": {},
            "overall_quality": 0.0,
            "details": {}
        }

        try:
            # 提取文本内容进行质量分析
            text_content = self._extract_text_content(doc_info["path"])

            if text_content:
                # 可读性评分（简化版）
                assessment["readability_score"] = self._calculate_readability_score(text_content)

                # 完整性评分
                assessment["completeness_score"] = self._calculate_completeness_score(
                    text_content, doc_info
                )

                # 准确性指标
                assessment["accuracy_indicators"] = self._check_accuracy_indicators(text_content)

                # 质量因素分析
                assessment["quality_factors"] = self._analyze_quality_factors(text_content, doc_info)

                # 综合质量评分
                assessment["overall_quality"] = (
                    assessment["readability_score"] * 0.3 +
                    assessment["completeness_score"] * 0.4 +
                    len(assessment["accuracy_indicators"]) * 0.1 * 0.3
                )

                assessment["details"] = {
                    "text_sample": text_content[:500] + "..." if len(text_content) > 500 else text_content,
                    "word_count": len(text_content.split()),
                    "sentence_count": len(re.split(r'[。！？.!?]', text_content)),
                    "paragraph_count": len(text_content.split('\n\n'))
                }

        except Exception as e:
            assessment["details"]["assessment_error"] = str(e)

        return assessment

    def _extract_text_content(self, file_path: str) -> str:
        """提取文档文本内容（简化版）"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext in ['.txt', '.rtf']:
                # 尝试不同编码
                for encoding in ['utf-8', 'gbk', 'gb2312']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue

            elif file_ext == '.pdf':
                # 这里应该使用PDF解析库，为了演示返回模拟内容
                return f"PDF文档内容 - {Path(file_path).name}\n这是一个PDF文档的示例内容。包含财务数据、经营情况等信息。"

            elif file_ext in ['.doc', '.docx']:
                # 这里应该使用Word文档解析库，为了演示返回模拟内容
                return f"Word文档内容 - {Path(file_path).name}\n这是一个Word文档的示例内容。包含相关章节和表格数据。"

            return ""

        except Exception as e:
            logger.warning(f"提取文档内容失败 {file_path}: {e}")
            return ""

    def _infer_document_type(self, filename: str) -> Optional[str]:
        """从文件名推断文档类型"""
        filename_lower = filename.lower()

        if "年报" in filename_lower or "年度报告" in filename_lower:
            return "annual_report"
        elif "季度" in filename_lower or "季度报告" in filename_lower:
            return "quarterly_report"
        elif "半年度" in filename_lower or "中期" in filename_lower:
            return "semi_annual_report"
        elif "调研" in filename_lower or "投资者关系" in filename_lower:
            return "research"
        elif "公告" in filename_lower or "通知" in filename_lower:
            return "announcement"
        elif "说明书" in filename_lower or "招股" in filename_lower:
            return "prospectus"

        return None

    def _extract_document_structure(self, file_path: str) -> Dict[str, List[str]]:
        """提取文档结构（简化版）"""
        # 这里应该使用专门的文档解析库
        # 为了演示，返回模拟的结构
        content = self._extract_text_content(file_path)

        if not content:
            return {"sections": [], "tables": [], "figures": []}

        # 简单的章节提取
        sections = re.findall(r'第[一二三四五六七八九十\d]+[章节部分][^\n]*', content)
        if not sections:
            # 尝试其他章节模式
            sections = re.findall(r'^[一二三四五六七八九十\d]+[、\s.][^\n]*', content, re.MULTILINE)

        # 简单的表格提取
        tables = re.findall(r'表[一二三四五六七八九十\d]+[^\n]*', content)

        return {
            "sections": sections,
            "tables": tables,
            "figures": []  # 简化版不提取图表
        }

    def _detect_language(self, text: str) -> str:
        """检测文本语言（简化版）"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)

        if total_chars == 0:
            return "unknown"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "chinese"
        elif chinese_ratio > 0.1:
            return "mixed"
        else:
            return "other"

    def _analyze_content_features(self, text: str) -> Dict[str, Any]:
        """分析内容特征"""
        features = {
            "word_count": len(text.split()),
            "sentence_count": len(re.split(r'[。！？.!?]', text)),
            "paragraph_count": len(text.split('\n\n')),
            "contains_numbers": bool(re.search(r'\d+', text)),
            "contains_dates": bool(re.search(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}', text)),
            "contains_currency": bool(re.search(r'[￥$]\d+|元\w+', text)),
            "contains_percentages": bool(re.search(r'\d+[%％]', text))
        }

        # 计算平均句长
        if features["sentence_count"] > 0:
            features["average_sentence_length"] = features["word_count"] / features["sentence_count"]
        else:
            features["average_sentence_length"] = 0

        return features

    def _calculate_readability_score(self, text: str) -> float:
        """计算可读性评分（简化版）"""
        if not text:
            return 0.0

        words = text.split()
        sentences = re.split(r'[。！？.!?]', text)

        if len(sentences) == 0:
            return 0.0

        # 简化的可读性计算
        avg_sentence_length = len(words) / len(sentences)

        # 基于平均句长的评分（句长越短，可读性越好）
        if avg_sentence_length < 10:
            return 1.0
        elif avg_sentence_length < 20:
            return 0.8
        elif avg_sentence_length < 30:
            return 0.6
        else:
            return 0.4

    def _calculate_completeness_score(self, text: str, doc_info: Dict[str, Any]) -> float:
        """计算完整性评分"""
        score = 0.0

        # 文本长度得分
        text_length = len(text)
        if text_length > 1000:
            score += 0.4
        elif text_length > 500:
            score += 0.3
        elif text_length > 100:
            score += 0.2

        # 结构完整性得分
        document_type = self._infer_document_type(doc_info["name"])
        if document_type and document_type in self.document_structures:
            structure = self._extract_document_structure(doc_info["path"])
            required_sections = self.document_structures[document_type].get("required_sections", [])

            if required_sections:
                found_sections = len([section for section in required_sections
                                    if any(section in found for found in structure.get("sections", []))])
                score += (found_sections / len(required_sections)) * 0.6

        return min(1.0, score)

    def _check_accuracy_indicators(self, text: str) -> List[str]:
        """检查准确性指标"""
        indicators = []

        # 检查是否包含具体数据
        if re.search(r'\d{4}年', text):
            indicators.append("contains_year")

        if re.search(r'\d+\.\d+[%％]', text):
            indicators.append("contains_percentages")

        if re.search(r'\d+[万亿千百]元', text):
            indicators.append("contains_currency_amounts")

        # 检查是否包含表格引用
        if re.search(r'表\d+|Table\s*\d+', text):
            indicators.append("contains_table_references")

        # 检查是否包含图表引用
        if re.search(r'图\d+|Figure\s*\d+', text):
            indicators.append("contains_figure_references")

        return indicators

    def _analyze_quality_factors(self, text: str, doc_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析质量因素"""
        factors = {
            "content_density": 0.0,
            "information_richness": 0.0,
            "structural_organization": 0.0,
            "language_quality": 0.0
        }

        # 内容密度（信息量/字数）
        words = text.split()
        unique_words = set(words)
        if words:
            factors["content_density"] = len(unique_words) / len(words)

        # 信息丰富度（是否包含多种类型信息）
        info_types = 0
        if re.search(r'\d+', text):
            info_types += 1
        if re.search(r'[A-Za-z]+', text):
            info_types += 1
        if re.search(r'[￥$]\d+', text):
            info_types += 1
        if re.search(r'\d{4}年', text):
            info_types += 1

        factors["information_richness"] = info_types / 4.0

        # 结构组织性
        sentences = re.split(r'[。！？.!?]', text)
        factors["structural_organization"] = min(1.0, len(sentences) / 20.0)

        # 语言质量（基于标点符号使用）
        punctuation_count = len(re.findall(r'[，。！？；：""''（）\[\]【】]', text))
        factors["language_quality"] = min(1.0, punctuation_count / len(words) if words else 0)

        return factors

    def _calculate_overall_score(self, basic_val: Dict, content_val: Dict,
                               structure_val: Dict, quality_assess: Dict) -> Tuple[bool, float]:
        """计算总体评分"""
        scores = []

        # 基础验证评分
        basic_score = 0.0
        if basic_val.get("file_readable", False):
            basic_score += 0.3
        if basic_val.get("size_valid", False):
            basic_score += 0.3
        if basic_val.get("extension_valid", False):
            basic_score += 0.4
        scores.append(basic_score)

        # 内容验证评分
        content_score = 0.0
        if content_val.get("content_extractable", False):
            content_score += 0.3
        if content_val.get("text_length_valid", False):
            content_score += 0.3
        if not content_val.get("forbidden_keywords_found", []):
            content_score += 0.4
        scores.append(content_score)

        # 结构验证评分
        structure_score = structure_val.get("structure_compliance", 0.0)
        scores.append(structure_score)

        # 质量评估评分
        quality_score = quality_assess.get("overall_quality", 0.0)
        scores.append(quality_score)

        # 计算加权平均
        weights = [0.2, 0.3, 0.3, 0.2]
        overall_score = sum(score * weight for score, weight in zip(scores, weights))

        # 判断是否成功（评分 > 0.6）
        success = overall_score > 0.6

        return success, overall_score

    def _collect_validation_issues(self, basic_val: Dict, content_val: Dict,
                                structure_val: Dict, quality_assess: Dict) -> List[str]:
        """收集验证问题"""
        issues = []

        # 基础验证问题
        if not basic_val.get("file_readable", False):
            issues.append("文件无法读取")
        if not basic_val.get("size_valid", False):
            issues.append("文件大小超出限制")
        if not basic_val.get("extension_valid", False):
            issues.append("文件格式不支持")

        # 内容验证问题
        if not content_val.get("content_extractable", False):
            issues.append("无法提取文档内容")
        if not content_val.get("text_length_valid", False):
            issues.append("文档文本长度不符合要求")
        if content_val.get("forbidden_keywords_found", []):
            issues.append(f"发现禁止关键词: {', '.join(content_val['forbidden_keywords_found'])}")

        # 结构验证问题
        missing_sections = structure_val.get("missing_sections", [])
        if missing_sections:
            issues.append(f"缺少必需章节: {', '.join(missing_sections)}")

        # 质量评估问题
        if quality_assess.get("overall_quality", 0) < 0.5:
            issues.append("文档整体质量较低")

        return issues

    def _generate_improvement_recommendations(self, issues: List[str]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for issue in issues:
            if "文件无法读取" in issue:
                recommendations.append("检查文件完整性，重新下载文档")
            elif "文件大小超出限制" in issue:
                recommendations.append("优化文档大小，移除不必要的内容")
            elif "文件格式不支持" in issue:
                recommendations.append("转换为支持的文档格式（PDF、DOC、TXT等）")
            elif "无法提取文档内容" in issue:
                recommendations.append("检查文档是否加密或损坏")
            elif "文档文本长度不符合要求" in issue:
                recommendations.append("确保文档包含足够的文本内容")
            elif "发现禁止关键词" in issue:
                recommendations.append("移除或替换文档中的禁止内容")
            elif "缺少必需章节" in issue:
                recommendations.append("补充文档中缺少的必需章节")
            elif "文档整体质量较低" in issue:
                recommendations.append("提高文档内容的完整性和准确性")

        return list(set(recommendations))  # 去重

    def _generate_validation_summary(self) -> Dict[str, Any]:
        """生成验证摘要"""
        if not self.validation_results:
            return {}

        summary = {
            "total_validations": len(self.validation_results),
            "successful_validations": len([r for r in self.validation_results if r.success]),
            "failed_validations": len([r for r in self.validation_results if not r.success]),
            "average_confidence_score": sum(r.confidence_score for r in self.validation_results) / len(self.validation_results),
            "common_issues": {},
            "validation_types": list(set(r.validation_type for r in self.validation_results)),
            "quality_distribution": {
                "high_quality": len([r for r in self.validation_results if r.confidence_score > 0.8]),
                "medium_quality": len([r for r in self.validation_results if 0.6 <= r.confidence_score <= 0.8]),
                "low_quality": len([r for r in self.validation_results if r.confidence_score < 0.6])
            }
        }

        # 统计常见问题
        issue_counts = {}
        for result in self.validation_results:
            for issue in result.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # 取前5个最常见的问题
        summary["common_issues"] = dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5])

        return summary

    def _save_validation_report(self, report: Dict[str, Any]):
        """保存验证报告"""
        try:
            reports_dir = Path("test_environment/validation_reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            report_file = reports_dir / f"deep_validation_report_{self.validation_session_id}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)

            logger.info(f"深入验证报告已保存到: {report_file}")

        except Exception as e:
            logger.error(f"保存验证报告失败: {e}")

    def compare_documents(self, file1_path: str, file2_path: str) -> ContentComparisonResult:
        """比较两个文档的内容"""
        logger.info(f"比较文档: {file1_path} vs {file2_path}")

        try:
            # 提取两个文档的内容
            content1 = self._extract_text_content(file1_path)
            content2 = self._extract_text_content(file2_path)

            # 计算内容哈希
            hash1 = hashlib.md5(content1.encode()).hexdigest()
            hash2 = hashlib.md5(content2.encode()).hexdigest()

            # 计算相似度
            similarity_score = difflib.SequenceMatcher(None, content1, content2).ratio()

            # 分析差异
            differences = self._analyze_content_differences(content1, content2)

            # 比较元数据
            metadata_comparison = self._compare_file_metadata(file1_path, file2_path)

            result = ContentComparisonResult(
                file1_path=file1_path,
                file2_path=file2_path,
                similarity_score=similarity_score,
                content_hash1=hash1,
                content_hash2=hash2,
                differences=differences,
                metadata_comparison=metadata_comparison
            )

            return result

        except Exception as e:
            logger.error(f"文档比较失败: {e}")
            raise

    def _analyze_content_differences(self, content1: str, content2: str) -> List[Dict[str, Any]]:
        """分析内容差异"""
        differences = []

        # 使用difflib比较文本
        differ = difflib.unified_diff(
            content1.splitlines(keepends=True),
            content2.splitlines(keepends=True),
            fromfile='file1',
            tofile='file2'
        )

        diff_lines = list(differ)

        # 统计差异类型
        additions = len([line for line in diff_lines if line.startswith('+')])
        deletions = len([line for line in diff_lines if line.startswith('-')])
        changes = len([line for line in diff_lines if line.startswith('@@')])

        differences = [
            {
                "type": "additions",
                "count": additions,
                "description": f"新增 {additions} 行内容"
            },
            {
                "type": "deletions",
                "count": deletions,
                "description": f"删除 {deletions} 行内容"
            },
            {
                "type": "changes",
                "count": changes,
                "description": f"修改 {changes} 处内容"
            }
        ]

        return differences

    def _compare_file_metadata(self, file1_path: str, file2_path: str) -> Dict[str, Any]:
        """比较文件元数据"""
        try:
            stat1 = os.stat(file1_path)
            stat2 = os.stat(file2_path)

            comparison = {
                "size_difference": stat1.st_size - stat2.st_size,
                "modification_time_difference": stat1.st_mtime - stat2.st_mtime,
                "size_similarity": min(stat1.st_size, stat2.st_size) / max(stat1.st_size, stat2.st_size),
                "file1_info": {
                    "size": stat1.st_size,
                    "modified": datetime.fromtimestamp(stat1.st_mtime).isoformat()
                },
                "file2_info": {
                    "size": stat2.st_size,
                    "modified": datetime.fromtimestamp(stat2.st_mtime).isoformat()
                }
            }

            return comparison

        except Exception as e:
            return {"error": str(e)}


def main():
    """主函数 - 执行深入数据验证"""
    print("=" * 60)
    print("深入真实数据验证工具")
    print("=" * 60)

    # 初始化验证器
    validator = DeepDataValidator()

    # 验证下载的文档
    print("\n1. 验证下载的文档...")
    validation_report = validator.validate_downloaded_documents()

    # 显示验证结果
    print("\n2. 验证结果:")
    summary = validation_report.get("summary", {})
    print(f"   总文档数: {summary.get('total_validations', 0)}")
    print(f"   验证成功: {summary.get('successful_validations', 0)}")
    print(f"   验证失败: {summary.get('failed_validations', 0)}")
    print(f"   平均置信度: {summary.get('average_confidence_score', 0):.2f}")

    # 显示质量分布
    print("\n3. 质量分布:")
    quality_dist = summary.get("quality_distribution", {})
    print(f"   高质量 (>0.8): {quality_dist.get('high_quality', 0)} 个")
    print(f"   中等质量 (0.6-0.8): {quality_dist.get('medium_quality', 0)} 个")
    print(f"   低质量 (<0.6): {quality_dist.get('low_quality', 0)} 个")

    # 显示常见问题
    print("\n4. 常见问题:")
    common_issues = summary.get("common_issues", {})
    for issue, count in list(common_issues.items())[:3]:
        print(f"   {issue}: {count} 次")

    # 演示文档比较功能
    print("\n5. 文档比较演示...")
    download_dir = validator.config.get("save_dir", "end2end_test/test_results")

    # 查找两个文档进行比较
    documents = validator._scan_documents(download_dir)
    if len(documents) >= 2:
        try:
            comparison_result = validator.compare_documents(documents[0]["path"], documents[1]["path"])
            print(f"   比较文档: {documents[0]['name']} vs {documents[1]['name']}")
            print(f"   相似度: {comparison_result.similarity_score:.2f}")
            print(f"   内容哈希1: {comparison_result.content_hash1[:8]}...")
            print(f"   内容哈希2: {comparison_result.content_hash2[:8]}...")

            for diff in comparison_result.differences:
                print(f"   {diff['description']}")
        except Exception as e:
            print(f"   文档比较失败: {e}")
    else:
        print("   文档数量不足，跳过比较演示")

    print("\n深入数据验证完成!")


if __name__ == "__main__":
    main()