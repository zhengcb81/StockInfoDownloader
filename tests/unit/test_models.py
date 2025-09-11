"""
数据模型单元测试
"""

import pytest
from datetime import datetime
from src.data.models import StockInfo, DownloadRecord, OrgIdMapping, DownloadTask, DownloadStatus
from tests.unit.test_data_manager import get_test_stock_code, get_test_stock_name, get_test_org_id


class TestStockInfo:
    """测试股票信息模型"""
    
    def test_valid_stock_info(self):
        """测试有效股票信息"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        stock = StockInfo(stock_code=stock_code, stock_name=stock_name)
        
        assert stock.stock_code == stock_code
        assert stock.stock_name == stock_name
        assert stock.is_valid is True
    
    def test_stock_code_normalization(self):
        """测试股票代码标准化"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        # 使用短代码测试标准化
        short_code = stock_code[2:]  # 去掉前两位
        stock = StockInfo(stock_code=short_code, stock_name=stock_name)
        assert stock.stock_code == stock_code
    
    def test_invalid_stock_info(self):
        """测试无效股票信息"""
        with pytest.raises(ValueError):
            StockInfo(stock_code="", stock_name="海康威视")
    
    def test_to_dict(self):
        """测试转换为字典"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        org_id = get_test_org_id(0)
        
        stock = StockInfo(
            stock_code=stock_code, 
            stock_name=stock_name,
            org_id=org_id
        )
        
        data = stock.to_dict()
        assert data["stock_code"] == stock_code
        assert data["stock_name"] == stock_name
        assert data["org_id"] == org_id
    
    def test_from_dict(self):
        """测试从字典创建"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        org_id = get_test_org_id(0)
        
        data = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "org_id": org_id
        }
        
        stock = StockInfo.from_dict(data)
        assert stock.stock_code == stock_code
        assert stock.stock_name == stock_name
        assert stock.org_id == org_id


class TestDownloadRecord:
    """测试下载记录模型"""
    
    def test_initial_state(self):
        """测试初始状态"""
        record = DownloadRecord(
            id="test-123",
            stock_code="002415",
            file_name="test.pdf",
            file_path="/downloads/test.pdf"
        )
        
        assert record.status == DownloadStatus.PENDING
        assert record.retry_count == 0
        assert record.created_at is not None
    
    def test_update_status(self):
        """测试状态更新"""
        record = DownloadRecord(
            id="test-123",
            stock_code="002415",
            file_name="test.pdf",
            file_path="/downloads/test.pdf"
        )
        
        record.update_status(DownloadStatus.DOWNLOADING)
        assert record.status == DownloadStatus.DOWNLOADING
        
        record.mark_failed("网络错误")
        assert record.status == DownloadStatus.FAILED
        assert record.error_message == "网络错误"
        assert record.retry_count == 1
    
    def test_mark_completed(self):
        """测试标记完成"""
        record = DownloadRecord(
            id="test-123",
            stock_code="002415",
            file_name="test.pdf",
            file_path="/downloads/test.pdf"
        )
        
        record.mark_completed(1024)
        assert record.status == DownloadStatus.COMPLETED
        assert record.file_size == 1024
    
    def test_to_dict(self):
        """测试转换为字典"""
        record = DownloadRecord(
            id="test-123",
            stock_code="002415",
            file_name="test.pdf",
            file_path="/downloads/test.pdf"
        )
        
        data = record.to_dict()
        assert data["id"] == "test-123"
        assert data["stock_code"] == "002415"
        assert data["status"] == "pending"


class TestOrgIdMapping:
    """测试组织ID映射模型"""
    
    def test_valid_mapping(self):
        """测试有效映射"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        org_id = get_test_org_id(0)
        
        mapping = OrgIdMapping(
            stock_code=stock_code,
            org_id=org_id,
            stock_name=stock_name
        )
        
        assert mapping.stock_code == stock_code
        assert mapping.org_id == org_id
        assert mapping.is_valid is True
    
    def test_stock_code_normalization(self):
        """测试股票代码标准化"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        org_id = get_test_org_id(0)
        
        # 使用短代码测试标准化
        short_code = stock_code[2:]  # 去掉前两位
        mapping = OrgIdMapping(
            stock_code=short_code,
            org_id=org_id,
            stock_name=stock_name
        )
        assert mapping.stock_code == stock_code
    
    def test_invalid_mapping(self):
        """测试无效映射"""
        with pytest.raises(ValueError):
            OrgIdMapping(stock_code="", org_id="123", stock_name="test")
        
        with pytest.raises(ValueError):
            OrgIdMapping(stock_code="123", org_id="", stock_name="test")
    
    def test_update_confidence(self):
        """测试更新置信度"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        org_id = get_test_org_id(0)
        
        mapping = OrgIdMapping(
            stock_code=stock_code,
            org_id=org_id,
            stock_name=stock_name
        )
        
        mapping.update_confidence(0.9)
        assert mapping.confidence == 0.9
        
        # 测试边界值
        mapping.update_confidence(1.5)
        assert mapping.confidence == 1.0
        
        mapping.update_confidence(-0.1)
        assert mapping.confidence == 0.0


class TestDownloadTask:
    """测试下载任务模型"""
    
    def test_default_target_pages(self):
        """测试默认目标页面"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        stock_info = StockInfo(stock_code=stock_code, stock_name=stock_name)
        task = DownloadTask(task_id="test", stock_info=stock_info)
        
        assert task.target_pages == ["research", "periodicReports"]
    
    def test_custom_target_pages(self):
        """测试自定义目标页面"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        stock_info = StockInfo(stock_code=stock_code, stock_name=stock_name)
        task = DownloadTask(
            task_id="test",
            stock_info=stock_info,
            target_pages=["research"]
        )
        
        assert task.target_pages == ["research"]
    
    def test_to_dict(self):
        """测试转换为字典"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        stock_info = StockInfo(stock_code=stock_code, stock_name=stock_name)
        task = DownloadTask(task_id="test", stock_info=stock_info)
        
        data = task.to_dict()
        assert data["task_id"] == "test"
        assert data["stock_info"]["stock_code"] == stock_code
        assert data["target_pages"] == ["research", "periodicReports"]
    
    def test_from_dict(self):
        """测试从字典创建"""
        stock_code = get_test_stock_code(0)
        stock_name = get_test_stock_name(0)
        
        data = {
            "task_id": "test",
            "stock_info": {
                "stock_code": stock_code,
                "stock_name": stock_name
            },
            "target_pages": ["research"]
        }
        
        task = DownloadTask.from_dict(data)
        assert task.task_id == "test"
        assert task.stock_info.stock_code == stock_code
        assert task.target_pages == ["research"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])