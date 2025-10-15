#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试环境一致性保证工具
提供快照、监控、恢复机制，确保测试环境的一致性
"""

import os
import json
import shutil
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class EnvironmentSnapshot:
    """环境快照数据结构"""
    snapshot_id: str
    timestamp: str
    description: str
    directories: Dict[str, Dict[str, Any]]  # 目录结构信息
    files: Dict[str, Dict[str, Any]]  # 文件信息
    config_files: Dict[str, str]  # 配置文件内容哈希
    dependencies: Dict[str, str]  # 依赖版本信息
    environment_variables: Dict[str, str]  # 环境变量
    test_status: str  # 测试状态

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnvironmentSnapshot':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class MonitoringRule:
    """监控规则"""
    rule_id: str
    name: str
    description: str
    target_path: str
    check_type: str  # 'file_count', 'file_size', 'content_hash', 'directory_structure'
    threshold: Any
    action: str  # 'alert', 'restore', 'fail_test'
    enabled: bool = True


class EnvironmentConsistencyManager:
    """环境一致性管理器"""

    def __init__(self,
                 snapshots_dir: str = "test_environment/snapshots",
                 monitoring_config: str = "test_environment/monitoring_config.json",
                 backup_dir: str = "test_environment/backups"):
        self.snapshots_dir = Path(snapshots_dir)
        self.monitoring_config_path = Path(monitoring_config)
        self.backup_dir = Path(backup_dir)

        # 确保目录存在
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 初始化监控规则
        self.monitoring_rules: List[MonitoringRule] = []
        self.load_monitoring_rules()

        # 当前快照
        self.current_snapshot: Optional[EnvironmentSnapshot] = None

        logger.info("环境一致性管理器初始化完成")

    def load_monitoring_rules(self) -> None:
        """加载监控规则"""
        if self.monitoring_config_path.exists():
            try:
                with open(self.monitoring_config_path, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                    self.monitoring_rules = [
                        MonitoringRule(**rule) for rule in rules_data.get('rules', [])
                    ]
                logger.info(f"加载了 {len(self.monitoring_rules)} 个监控规则")
            except Exception as e:
                logger.error(f"加载监控规则失败: {e}")
                self.create_default_monitoring_rules()
        else:
            self.create_default_monitoring_rules()

    def create_default_monitoring_rules(self) -> None:
        """创建默认监控规则"""
        default_rules = [
            MonitoringRule(
                rule_id="ENV_001",
                name="测试目录结构监控",
                description="监控测试目录结构的完整性",
                target_path="end2end_test",
                check_type="directory_structure",
                threshold={"min_files": 1, "required_dirs": ["test_results", "expected_results"]},
                action="alert"
            ),
            MonitoringRule(
                rule_id="ENV_002",
                name="预期文档数量监控",
                description="监控预期文档数量，确保测试数据充足",
                target_path="end2end_test/expected_results",
                check_type="file_count",
                threshold={"min_files": 5},
                action="fail_test"
            ),
            MonitoringRule(
                rule_id="ENV_003",
                name="配置文件完整性监控",
                description="监控配置文件的完整性和正确性",
                target_path="config_end2end_test.json",
                check_type="content_hash",
                threshold=None,
                action="restore"
            ),
            MonitoringRule(
                rule_id="ENV_004",
                name="测试结果目录清洁度",
                description="确保测试结果目录在测试前处于清洁状态",
                target_path="end2end_test/test_results",
                check_type="file_count",
                threshold={"max_files": 2},  # 允许少数系统文件
                action="alert"
            )
        ]

        self.monitoring_rules = default_rules
        self.save_monitoring_rules()
        logger.info("创建了默认监控规则")

    def save_monitoring_rules(self) -> None:
        """保存监控规则"""
        try:
            rules_data = {
                "rules": [asdict(rule) for rule in self.monitoring_rules],
                "last_updated": datetime.now().isoformat()
            }

            self.monitoring_config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.monitoring_config_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)

            logger.info("监控规则保存成功")
        except Exception as e:
            logger.error(f"保存监控规则失败: {e}")

    def create_snapshot(self, description: str = "") -> EnvironmentSnapshot:
        """创建环境快照"""
        logger.info(f"开始创建环境快照: {description}")

        snapshot_id = f"SNAP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().isoformat()

        # 收集目录信息
        directories = self._scan_directories()

        # 收集文件信息
        files = self._scan_files()

        # 收集配置文件信息
        config_files = self._scan_config_files()

        # 收集依赖信息
        dependencies = self._collect_dependencies()

        # 收集环境变量
        environment_variables = dict(os.environ)

        # 创建快照对象
        snapshot = EnvironmentSnapshot(
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            description=description or f"环境快照 - {timestamp}",
            directories=directories,
            files=files,
            config_files=config_files,
            dependencies=dependencies,
            environment_variables=environment_variables,
            test_status="ready"
        )

        # 保存快照
        self._save_snapshot(snapshot)

        # 创建备份
        self._create_backup(snapshot_id)

        self.current_snapshot = snapshot
        logger.info(f"环境快照创建成功: {snapshot_id}")

        return snapshot

    def _scan_directories(self) -> Dict[str, Dict[str, Any]]:
        """扫描目录结构"""
        directories = {}

        # 扫描关键目录
        key_dirs = [
            "end2end_test",
            "end2end_test/test_results",
            "end2end_test/expected_results",
            "src",
            "tools",
            "tests"
        ]

        for dir_path in key_dirs:
            if os.path.exists(dir_path):
                try:
                    file_count = len([f for f in os.listdir(dir_path)
                                    if os.path.isfile(os.path.join(dir_path, f))])
                    dir_count = len([d for d in os.listdir(dir_path)
                                   if os.path.isdir(os.path.join(dir_path, d))])

                    directories[dir_path] = {
                        "exists": True,
                        "file_count": file_count,
                        "directory_count": dir_count,
                        "last_modified": os.path.getmtime(dir_path)
                    }
                except Exception as e:
                    directories[dir_path] = {
                        "exists": True,
                        "error": str(e)
                    }
            else:
                directories[dir_path] = {"exists": False}

        return directories

    def _scan_files(self) -> Dict[str, Dict[str, Any]]:
        """扫描关键文件"""
        files = {}

        # 扫描关键文件
        key_files = [
            "config_end2end_test.json",
            "测试说明.md",
            "e2e_test.py"
        ]

        for file_path in key_files:
            if os.path.exists(file_path):
                try:
                    stat = os.stat(file_path)
                    with open(file_path, 'rb') as f:
                        content_hash = hashlib.md5(f.read()).hexdigest()

                    files[file_path] = {
                        "exists": True,
                        "size": stat.st_size,
                        "last_modified": stat.st_mtime,
                        "content_hash": content_hash
                    }
                except Exception as e:
                    files[file_path] = {
                        "exists": True,
                        "error": str(e)
                    }
            else:
                files[file_path] = {"exists": False}

        return files

    def _scan_config_files(self) -> Dict[str, str]:
        """扫描配置文件内容哈希"""
        config_files = {}

        config_extensions = ['.json', '.yaml', '.yml', '.ini', '.conf']

        for root, dirs, filenames in os.walk('.'):
            # 跳过隐藏目录和大型目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git']]

            for filename in filenames:
                if any(filename.endswith(ext) for ext in config_extensions):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'rb') as f:
                            content_hash = hashlib.md5(f.read()).hexdigest()
                        config_files[file_path] = content_hash
                    except Exception:
                        pass  # 忽略无法读取的文件

        return config_files

    def _collect_dependencies(self) -> Dict[str, str]:
        """收集依赖版本信息"""
        dependencies = {}

        # 尝试读取requirements.txt或pyproject.toml
        dependency_files = ['requirements.txt', 'pyproject.toml', 'setup.py']

        for dep_file in dependency_files:
            if os.path.exists(dep_file):
                try:
                    with open(dep_file, 'r', encoding='utf-8') as f:
                        dependencies[dep_file] = f.read()
                except Exception:
                    pass

        return dependencies

    def _save_snapshot(self, snapshot: EnvironmentSnapshot) -> None:
        """保存快照到文件"""
        snapshot_file = self.snapshots_dir / f"{snapshot.snapshot_id}.json"

        try:
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            raise

    def _create_backup(self, snapshot_id: str) -> None:
        """创建关键文件备份"""
        backup_path = self.backup_dir / snapshot_id
        backup_path.mkdir(exist_ok=True)

        # 备份关键文件和目录
        backup_items = [
            "config_end2end_test.json",
            "end2end_test/expected_results",
            "测试说明.md"
        ]

        for item in backup_items:
            try:
                src = Path(item)
                dst = backup_path / src.name

                if src.is_file():
                    shutil.copy2(src, dst)
                elif src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)

            except Exception as e:
                logger.warning(f"备份文件失败 {item}: {e}")

    def load_snapshot(self, snapshot_id: str) -> Optional[EnvironmentSnapshot]:
        """加载指定的快照"""
        snapshot_file = self.snapshots_dir / f"{snapshot_id}.json"

        if not snapshot_file.exists():
            logger.error(f"快照文件不存在: {snapshot_id}")
            return None

        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot_data = json.load(f)

            snapshot = EnvironmentSnapshot.from_dict(snapshot_data)
            self.current_snapshot = snapshot

            logger.info(f"快照加载成功: {snapshot_id}")
            return snapshot

        except Exception as e:
            logger.error(f"加载快照失败: {e}")
            return None

    def restore_environment(self, snapshot_id: str) -> bool:
        """恢复到指定快照状态"""
        logger.info(f"开始恢复环境到快照: {snapshot_id}")

        snapshot = self.load_snapshot(snapshot_id)
        if not snapshot:
            return False

        try:
            # 恢复文件备份
            backup_path = self.backup_dir / snapshot_id
            if backup_path.exists():
                self._restore_from_backup(backup_path)

            # 清理测试结果目录
            if os.path.exists("end2end_test/test_results"):
                self._clean_directory("end2end_test/test_results")

            logger.info(f"环境恢复成功: {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"环境恢复失败: {e}")
            return False

    def _restore_from_backup(self, backup_path: Path) -> None:
        """从备份恢复文件"""
        for item in backup_path.iterdir():
            target_path = Path(item.name)

            # 删除现有文件/目录
            if target_path.exists():
                if target_path.is_file():
                    target_path.unlink()
                else:
                    shutil.rmtree(target_path)

            # 恢复备份
            if item.is_file():
                shutil.copy2(item, target_path)
            elif item.is_dir():
                shutil.copytree(item, target_path)

    def _clean_directory(self, dir_path: str) -> None:
        """清理目录内容"""
        for item in Path(dir_path).iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                logger.warning(f"清理文件失败 {item}: {e}")

    def monitor_environment(self) -> Dict[str, Any]:
        """监控环境状态"""
        logger.info("开始环境状态监控")

        monitoring_results = {
            "timestamp": datetime.now().isoformat(),
            "total_rules": len(self.monitoring_rules),
            "passed_checks": 0,
            "failed_checks": 0,
            "warnings": [],
            "errors": [],
            "actions_taken": []
        }

        for rule in self.monitoring_rules:
            if not rule.enabled:
                continue

            try:
                result = self._check_monitoring_rule(rule)
                if result["passed"]:
                    monitoring_results["passed_checks"] += 1
                else:
                    monitoring_results["failed_checks"] += 1
                    monitoring_results["errors"].append({
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "error": result["message"]
                    })

                    # 执行相应动作
                    action_result = self._execute_monitoring_action(rule, result)
                    if action_result:
                        monitoring_results["actions_taken"].append({
                            "rule_id": rule.rule_id,
                            "action": rule.action,
                            "result": action_result
                        })

            except Exception as e:
                monitoring_results["failed_checks"] += 1
                monitoring_results["errors"].append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "error": f"监控检查异常: {str(e)}"
                })

        logger.info(f"环境监控完成 - 通过: {monitoring_results['passed_checks']}, 失败: {monitoring_results['failed_checks']}")

        return monitoring_results

    def _check_monitoring_rule(self, rule: MonitoringRule) -> Dict[str, Any]:
        """检查单个监控规则"""
        result = {"passed": False, "message": "", "details": {}}

        if not os.path.exists(rule.target_path):
            result["message"] = f"目标路径不存在: {rule.target_path}"
            return result

        try:
            if rule.check_type == "file_count":
                result = self._check_file_count(rule)
            elif rule.check_type == "file_size":
                result = self._check_file_size(rule)
            elif rule.check_type == "content_hash":
                result = self._check_content_hash(rule)
            elif rule.check_type == "directory_structure":
                result = self._check_directory_structure(rule)
            else:
                result["message"] = f"未知的检查类型: {rule.check_type}"

        except Exception as e:
            result["message"] = f"检查执行异常: {str(e)}"

        return result

    def _check_file_count(self, rule: MonitoringRule) -> Dict[str, Any]:
        """检查文件数量"""
        threshold = rule.threshold or {}
        path = Path(rule.target_path)

        if path.is_file():
            file_count = 1
        elif path.is_dir():
            file_count = len([f for f in path.iterdir() if f.is_file()])
        else:
            return {"passed": False, "message": "路径不是文件或目录"}

        min_files = threshold.get("min_files", 0)
        max_files = threshold.get("max_files", float('inf'))

        if min_files <= file_count <= max_files:
            return {"passed": True, "details": {"file_count": file_count}}
        else:
            return {
                "passed": False,
                "message": f"文件数量 {file_count} 不在要求范围 [{min_files}, {max_files}]",
                "details": {"file_count": file_count}
            }

    def _check_file_size(self, rule: MonitoringRule) -> Dict[str, Any]:
        """检查文件大小"""
        path = Path(rule.target_path)

        if not path.is_file():
            return {"passed": False, "message": "目标不是文件"}

        file_size = path.stat().st_size
        threshold = rule.threshold or {}

        min_size = threshold.get("min_size", 0)
        max_size = threshold.get("max_size", float('inf'))

        if min_size <= file_size <= max_size:
            return {"passed": True, "details": {"file_size": file_size}}
        else:
            return {
                "passed": False,
                "message": f"文件大小 {file_size} 不在要求范围 [{min_size}, {max_size}]",
                "details": {"file_size": file_size}
            }

    def _check_content_hash(self, rule: MonitoringRule) -> Dict[str, Any]:
        """检查文件内容哈希"""
        path = Path(rule.target_path)

        if not path.is_file():
            return {"passed": False, "message": "目标不是文件"}

        with open(path, 'rb') as f:
            current_hash = hashlib.md5(f.read()).hexdigest()

        # 如果有当前快照，与快照比较
        if self.current_snapshot and path.name in self.current_snapshot.config_files:
            expected_hash = self.current_snapshot.config_files[path.name]
            if current_hash == expected_hash:
                return {"passed": True, "details": {"content_hash": current_hash}}
            else:
                return {
                    "passed": False,
                    "message": f"文件内容哈希不匹配",
                    "details": {"current_hash": current_hash, "expected_hash": expected_hash}
                }

        return {"passed": True, "details": {"content_hash": current_hash}}

    def _check_directory_structure(self, rule: MonitoringRule) -> Dict[str, Any]:
        """检查目录结构"""
        path = Path(rule.target_path)

        if not path.is_dir():
            return {"passed": False, "message": "目标不是目录"}

        threshold = rule.threshold or {}
        required_dirs = threshold.get("required_dirs", [])
        min_files = threshold.get("min_files", 0)

        # 检查必需的子目录
        existing_dirs = [d.name for d in path.iterdir() if d.is_dir()]
        missing_dirs = [d for d in required_dirs if d not in existing_dirs]

        if missing_dirs:
            return {
                "passed": False,
                "message": f"缺少必需的目录: {', '.join(missing_dirs)}",
                "details": {"existing_dirs": existing_dirs, "missing_dirs": missing_dirs}
            }

        # 检查文件数量
        file_count = len([f for f in path.iterdir() if f.is_file()])
        if file_count < min_files:
            return {
                "passed": False,
                "message": f"文件数量 {file_count} 少于最小要求 {min_files}",
                "details": {"file_count": file_count}
            }

        return {"passed": True, "details": {"file_count": file_count, "directories": existing_dirs}}

    def _execute_monitoring_action(self, rule: MonitoringRule, check_result: Dict[str, Any]) -> Optional[str]:
        """执行监控动作"""
        if rule.action == "alert":
            logger.warning(f"环境监控警告 - {rule.name}: {check_result['message']}")
            return f"已发出警告: {check_result['message']}"

        elif rule.action == "restore":
            if self.current_snapshot:
                if self.restore_environment(self.current_snapshot.snapshot_id):
                    return f"已恢复到快照: {self.current_snapshot.snapshot_id}"
                else:
                    return "环境恢复失败"
            else:
                return "没有可用快照进行恢复"

        elif rule.action == "fail_test":
            logger.error(f"环境检查失败 - {rule.name}: {check_result['message']}")
            raise RuntimeError(f"环境一致性检查失败: {check_result['message']}")

        return None

    def list_snapshots(self) -> List[Dict[str, str]]:
        """列出所有可用快照"""
        snapshots = []

        for snapshot_file in self.snapshots_dir.glob("SNAP_*.json"):
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    snapshot_data = json.load(f)

                snapshots.append({
                    "snapshot_id": snapshot_data["snapshot_id"],
                    "timestamp": snapshot_data["timestamp"],
                    "description": snapshot_data["description"],
                    "test_status": snapshot_data["test_status"]
                })
            except Exception as e:
                logger.warning(f"读取快照文件失败 {snapshot_file}: {e}")

        # 按时间戳排序
        snapshots.sort(key=lambda x: x["timestamp"], reverse=True)

        return snapshots

    def cleanup_old_snapshots(self, keep_count: int = 10) -> int:
        """清理旧快照，保留最新的几个"""
        snapshots = self.list_snapshots()

        if len(snapshots) <= keep_count:
            return 0

        # 删除旧快照
        deleted_count = 0
        for snapshot in snapshots[keep_count:]:
            try:
                snapshot_file = self.snapshots_dir / f"{snapshot['snapshot_id']}.json"
                backup_path = self.backup_dir / snapshot['snapshot_id']

                if snapshot_file.exists():
                    snapshot_file.unlink()

                if backup_path.exists():
                    shutil.rmtree(backup_path)

                deleted_count += 1
                logger.info(f"删除旧快照: {snapshot['snapshot_id']}")

            except Exception as e:
                logger.warning(f"删除快照失败 {snapshot['snapshot_id']}: {e}")

        return deleted_count

    def generate_consistency_report(self) -> Dict[str, Any]:
        """生成一致性报告"""
        logger.info("生成环境一致性报告")

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "snapshot_info": {},
            "monitoring_results": {},
            "available_snapshots": self.list_snapshots(),
            "recommendations": []
        }

        # 当前快照信息
        if self.current_snapshot:
            report["snapshot_info"] = {
                "snapshot_id": self.current_snapshot.snapshot_id,
                "timestamp": self.current_snapshot.timestamp,
                "description": self.current_snapshot.description,
                "test_status": self.current_snapshot.test_status
            }

        # 监控结果
        report["monitoring_results"] = self.monitor_environment()

        # 生成建议
        self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> None:
        """生成改进建议"""
        recommendations = []

        monitoring_results = report["monitoring_results"]

        if monitoring_results["failed_checks"] > 0:
            recommendations.append({
                "type": "environment_issue",
                "priority": "high",
                "message": f"发现 {monitoring_results['failed_checks']} 个环境检查失败，建议立即修复",
                "action": "review_monitoring_rules"
            })

        if len(report["available_snapshots"]) < 3:
            recommendations.append({
                "type": "snapshot_management",
                "priority": "medium",
                "message": "可用快照数量较少，建议定期创建环境快照",
                "action": "create_regular_snapshots"
            })

        if monitoring_results["passed_checks"] == monitoring_results["total_rules"]:
            recommendations.append({
                "type": "maintenance",
                "priority": "low",
                "message": "环境状态良好，建议继续保持当前的监控策略",
                "action": "maintain_current_setup"
            })

        report["recommendations"] = recommendations


def main():
    """主函数 - 演示环境一致性管理功能"""
    print("=" * 60)
    print("测试环境一致性保证工具")
    print("=" * 60)

    # 初始化管理器
    manager = EnvironmentConsistencyManager()

    # 1. 创建环境快照
    print("\n1. 创建环境快照...")
    snapshot = manager.create_snapshot("测试前环境快照")
    print(f"   快照ID: {snapshot.snapshot_id}")

    # 2. 环境监控
    print("\n2. 执行环境监控...")
    monitoring_results = manager.monitor_environment()
    print(f"   总规则数: {monitoring_results['total_rules']}")
    print(f"   通过检查: {monitoring_results['passed_checks']}")
    print(f"   失败检查: {monitoring_results['failed_checks']}")

    # 3. 生成一致性报告
    print("\n3. 生成一致性报告...")
    report = manager.generate_consistency_report()

    print("\n环境一致性报告:")
    print(f"  报告时间: {report['report_timestamp']}")
    print(f"  当前快照: {report['snapshot_info'].get('snapshot_id', 'N/A')}")
    print(f"  可用快照数: {len(report['available_snapshots'])}")
    print(f"  建议数量: {len(report['recommendations'])}")

    # 4. 列出可用快照
    print("\n4. 可用快照列表:")
    snapshots = manager.list_snapshots()
    for i, snap in enumerate(snapshots[:5]):  # 只显示前5个
        print(f"   {i+1}. {snap['snapshot_id']} - {snap['timestamp'][:19]}")

    # 5. 清理旧快照
    print("\n5. 清理旧快照...")
    deleted_count = manager.cleanup_old_snapshots(keep_count=5)
    print(f"   删除了 {deleted_count} 个旧快照")

    print("\n环境一致性管理完成!")

    # 保存报告
    report_file = "test_environment/environment_consistency_report.json"
    os.makedirs("test_environment", exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"一致性报告已保存到: {report_file}")


if __name__ == "__main__":
    main()