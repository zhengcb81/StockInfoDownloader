#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
代码质量检查工具

检查代码风格、复杂度、安全性等方面的问题
"""

import os
import sys
import ast
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

class CodeQualityChecker:
    """代码质量检查器"""
    
    def __init__(self):
        self.issues = []
        self.stats = {
            'files_checked': 0,
            'lines_of_code': 0,
            'functions': 0,
            'classes': 0,
            'issues_found': 0
        }
    
    def check_file(self, file_path: str) -> List[Dict]:
        """检查单个文件"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 更新统计信息
            self.stats['files_checked'] += 1
            self.stats['lines_of_code'] += len(lines)
            
            # 解析AST
            try:
                tree = ast.parse(content)
                issues.extend(self._check_ast(tree, file_path))
            except SyntaxError as e:
                issues.append({
                    'file': file_path,
                    'line': e.lineno,
                    'type': 'syntax_error',
                    'message': f"语法错误: {e.msg}",
                    'severity': 'error'
                })
            
            # 检查代码风格
            issues.extend(self._check_style(lines, file_path))
            
            # 检查安全性
            issues.extend(self._check_security(content, file_path))
            
        except Exception as e:
            issues.append({
                'file': file_path,
                'line': 0,
                'type': 'file_error',
                'message': f"无法读取文件: {e}",
                'severity': 'error'
            })
        
        self.issues.extend(issues)
        self.stats['issues_found'] += len(issues)
        return issues
    
    def _check_ast(self, tree: ast.AST, file_path: str) -> List[Dict]:
        """检查AST相关问题"""
        issues = []
        
        for node in ast.walk(tree):
            # 统计函数和类
            if isinstance(node, ast.FunctionDef):
                self.stats['functions'] += 1
                issues.extend(self._check_function(node, file_path))
            elif isinstance(node, ast.ClassDef):
                self.stats['classes'] += 1
                issues.extend(self._check_class(node, file_path))
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                issues.extend(self._check_import(node, file_path))
        
        return issues
    
    def _check_function(self, node: ast.FunctionDef, file_path: str) -> List[Dict]:
        """检查函数相关问题"""
        issues = []
        
        # 检查函数长度
        if hasattr(node, 'end_lineno') and node.end_lineno:
            func_length = node.end_lineno - node.lineno
            if func_length > 50:
                issues.append({
                    'file': file_path,
                    'line': node.lineno,
                    'type': 'function_too_long',
                    'message': f"函数 '{node.name}' 过长 ({func_length} 行)，建议拆分",
                    'severity': 'warning'
                })
        
        # 检查参数数量
        if len(node.args.args) > 7:
            issues.append({
                'file': file_path,
                'line': node.lineno,
                'type': 'too_many_parameters',
                'message': f"函数 '{node.name}' 参数过多 ({len(node.args.args)} 个)",
                'severity': 'warning'
            })
        
        # 检查是否有文档字符串
        if not ast.get_docstring(node):
            issues.append({
                'file': file_path,
                'line': node.lineno,
                'type': 'missing_docstring',
                'message': f"函数 '{node.name}' 缺少文档字符串",
                'severity': 'info'
            })
        
        return issues
    
    def _check_class(self, node: ast.ClassDef, file_path: str) -> List[Dict]:
        """检查类相关问题"""
        issues = []
        
        # 检查是否有文档字符串
        if not ast.get_docstring(node):
            issues.append({
                'file': file_path,
                'line': node.lineno,
                'type': 'missing_docstring',
                'message': f"类 '{node.name}' 缺少文档字符串",
                'severity': 'info'
            })
        
        # 检查方法数量
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        if len(methods) > 20:
            issues.append({
                'file': file_path,
                'line': node.lineno,
                'type': 'too_many_methods',
                'message': f"类 '{node.name}' 方法过多 ({len(methods)} 个)，考虑拆分",
                'severity': 'warning'
            })
        
        return issues
    
    def _check_import(self, node, file_path: str) -> List[Dict]:
        """检查导入相关问题"""
        issues = []
        
        # 检查通配符导入
        if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
            issues.append({
                'file': file_path,
                'line': node.lineno,
                'type': 'wildcard_import',
                'message': f"避免使用通配符导入: from {node.module} import *",
                'severity': 'warning'
            })
        
        return issues
    
    def _check_style(self, lines: List[str], file_path: str) -> List[Dict]:
        """检查代码风格"""
        issues = []
        
        for i, line in enumerate(lines, 1):
            # 检查行长度
            if len(line) > 120:
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'line_too_long',
                    'message': f"行过长 ({len(line)} 字符)，建议不超过120字符",
                    'severity': 'info'
                })
            
            # 检查尾随空格
            if line.rstrip() != line and line.strip():
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'trailing_whitespace',
                    'message': "行末有多余空格",
                    'severity': 'info'
                })
            
            # 检查制表符
            if '\t' in line:
                issues.append({
                    'file': file_path,
                    'line': i,
                    'type': 'tab_character',
                    'message': "使用制表符，建议使用空格",
                    'severity': 'info'
                })
        
        return issues
    
    def _check_security(self, content: str, file_path: str) -> List[Dict]:
        """检查安全性问题"""
        issues = []
        
        # 检查潜在的安全问题
        security_patterns = [
            (r'eval\s*\(', 'eval函数可能存在安全风险'),
            (r'exec\s*\(', 'exec函数可能存在安全风险'),
            (r'subprocess\.call\s*\(.*shell\s*=\s*True', 'shell=True可能存在命令注入风险'),
            (r'password\s*=\s*["\'][^"\']+["\']', '硬编码密码'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', '硬编码API密钥'),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        'file': file_path,
                        'line': i,
                        'type': 'security_risk',
                        'message': message,
                        'severity': 'warning'
                    })
        
        return issues
    
    def check_directory(self, directory: str, extensions: List[str] = None) -> None:
        """检查目录中的所有Python文件"""
        if extensions is None:
            extensions = ['.py']
        
        for root, dirs, files in os.walk(directory):
            # 跳过特定目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    self.check_file(file_path)
    
    def generate_report(self) -> str:
        """生成检查报告"""
        report = []
        report.append("=" * 60)
        report.append("代码质量检查报告")
        report.append("=" * 60)
        
        # 统计信息
        report.append(f"\n📊 统计信息:")
        report.append(f"  检查文件数: {self.stats['files_checked']}")
        report.append(f"  代码行数: {self.stats['lines_of_code']}")
        report.append(f"  函数数量: {self.stats['functions']}")
        report.append(f"  类数量: {self.stats['classes']}")
        report.append(f"  发现问题: {self.stats['issues_found']}")
        
        # 按严重程度分组
        issues_by_severity = {}
        for issue in self.issues:
            severity = issue['severity']
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            issues_by_severity[severity].append(issue)
        
        # 输出问题
        severity_order = ['error', 'warning', 'info']
        severity_icons = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
        
        for severity in severity_order:
            if severity in issues_by_severity:
                issues = issues_by_severity[severity]
                report.append(f"\n{severity_icons[severity]} {severity.upper()} ({len(issues)} 个):")
                
                for issue in issues:
                    report.append(f"  {issue['file']}:{issue['line']} - {issue['message']}")
        
        # 质量评分
        total_issues = len(self.issues)
        if total_issues == 0:
            score = 100
        else:
            # 根据问题严重程度计算分数
            error_weight = 10
            warning_weight = 5
            info_weight = 1
            
            weighted_issues = (
                len(issues_by_severity.get('error', [])) * error_weight +
                len(issues_by_severity.get('warning', [])) * warning_weight +
                len(issues_by_severity.get('info', [])) * info_weight
            )
            
            # 基于代码行数计算分数
            score = max(0, 100 - (weighted_issues * 100 / max(self.stats['lines_of_code'], 1)))
        
        report.append(f"\n🎯 质量评分: {score:.1f}/100")
        
        if score >= 90:
            report.append("🎉 代码质量优秀！")
        elif score >= 70:
            report.append("👍 代码质量良好，还有改进空间")
        elif score >= 50:
            report.append("⚠️ 代码质量一般，建议优化")
        else:
            report.append("💥 代码质量需要大幅改进")
        
        return '\n'.join(report)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="代码质量检查工具")
    parser.add_argument('path', help='要检查的文件或目录路径')
    parser.add_argument('--output', '-o', help='输出报告到文件')
    parser.add_argument('--extensions', nargs='+', default=['.py'], help='要检查的文件扩展名')
    
    args = parser.parse_args()
    
    checker = CodeQualityChecker()
    
    if os.path.isfile(args.path):
        checker.check_file(args.path)
    elif os.path.isdir(args.path):
        checker.check_directory(args.path, args.extensions)
    else:
        print(f"❌ 路径不存在: {args.path}")
        return 1
    
    report = checker.generate_report()
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📄 报告已保存到: {args.output}")
    else:
        print(report)
    
    # 如果有错误，返回非零退出码
    error_count = len([issue for issue in checker.issues if issue['severity'] == 'error'])
    return 1 if error_count > 0 else 0

if __name__ == "__main__":
    sys.exit(main()) 