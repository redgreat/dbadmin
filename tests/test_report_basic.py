"""
测试报表管理功能
"""
import pytest
from app.models.report import ReportConfig, ReportGeneration, SoftDeleteMixin
from app.services.report_service import ReportService


def test_soft_delete_mixin():
    """测试软删除混入类"""
    assert hasattr(SoftDeleteMixin, 'soft_delete')
    assert hasattr(SoftDeleteMixin, 'filter_active')


def test_report_config_model():
    """测试报表配置模型"""
    # 检查模型类是否存在
    assert ReportConfig is not None
    # 检查模型是否有_meta属性（Tortoise ORM的模型元数据）
    assert hasattr(ReportConfig, '_meta')
    # 检查字段是否在_meta中定义
    fields = ReportConfig._meta.fields
    assert 'system_name' in fields
    assert 'report_name' in fields
    assert 'sql_statement' in fields
    assert 'db_connection' in fields  # 外键字段名
    assert 'maintainer' in fields


def test_report_generation_model():
    """测试报表生成记录模型"""
    # 检查模型类是否存在
    assert ReportGeneration is not None
    # 检查模型是否有_meta属性
    assert hasattr(ReportGeneration, '_meta')
    # 检查字段是否在_meta中定义
    fields = ReportGeneration._meta.fields
    assert 'report_name' in fields
    assert 'report_config' in fields  # 外键字段名
    assert 'generator' in fields
    assert 'status' in fields
    assert 'file_path' in fields
    assert 'execution_json' in fields


def test_sql_validation():
    """测试SQL安全验证"""
    # 测试合法的SELECT语句
    is_valid, msg = ReportService.validate_sql("SELECT * FROM users")
    assert is_valid is True
    assert msg == ""

    # 测试非法的DELETE语句
    is_valid, msg = ReportService.validate_sql("DELETE FROM users WHERE id=1")
    assert is_valid is False
    assert "DELETE" in msg

    # 测试非法的DROP语句
    is_valid, msg = ReportService.validate_sql("DROP TABLE users")
    assert is_valid is False
    assert "DROP" in msg

    # 测试UPDATE语句（应该被拒绝，因为不是SELECT）
    is_valid, msg = ReportService.validate_sql("UPDATE users SET name='test'")
    assert is_valid is False
    # UPDATE会被检测为危险关键字
    assert "UPDATE" in msg


def test_system_name_options():
    """测试系统名称选项"""
    import asyncio
    options = asyncio.run(ReportService.get_system_name_options())
    assert isinstance(options, list)
    assert len(options) > 0
    assert "订单中心" in options


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
