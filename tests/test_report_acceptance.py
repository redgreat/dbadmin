"""
报表管理功能验收测试脚本
运行此脚本验证所有功能是否正常
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.report import ReportConfig, ReportGeneration, SoftDeleteMixin
from app.services.report_service import ReportService
from app.services.sql_execution_service import SQLExecutionService
from app.services.excel_export_service import ExcelExportService
from app.core.config_loader import config


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(message):
    """打印成功消息"""
    print(f"[PASS] {message}")


def print_error(message):
    """打印错误消息"""
    print(f"[FAIL] {message}")


def test_models():
    """测试模型定义"""
    print_header("1. 测试模型定义")

    try:
        # 测试ReportConfig模型
        assert hasattr(ReportConfig, '_meta')
        fields = ReportConfig._meta.fields
        required_fields = ['system_name', 'report_name', 'sql_statement', 'db_connection', 'maintainer']
        for field in required_fields:
            assert field in fields, f"缺少字段: {field}"
        print_success("ReportConfig模型字段完整")

        # 测试ReportGeneration模型
        assert hasattr(ReportGeneration, '_meta')
        fields = ReportGeneration._meta.fields
        required_fields = ['report_name', 'report_config', 'generator', 'status', 'file_path', 'execution_json']
        for field in required_fields:
            assert field in fields, f"缺少字段: {field}"
        print_success("ReportGeneration模型字段完整")

        # 测试软删除混入类
        assert hasattr(SoftDeleteMixin, 'soft_delete')
        assert hasattr(SoftDeleteMixin, 'filter_active')
        print_success("SoftDeleteMixin方法完整")

        return True
    except Exception as e:
        print_error(f"模型测试失败: {str(e)}")
        return False


def test_sql_validation():
    """测试SQL验证"""
    print_header("2. 测试SQL安全验证")

    try:
        # 测试合法SQL
        is_valid, msg = ReportService.validate_sql("SELECT * FROM users WHERE id = 1")
        assert is_valid is True, "合法SQL被拒绝"
        print_success("合法SQL验证通过")

        # 测试非法SQL - DELETE
        is_valid, msg = ReportService.validate_sql("DELETE FROM users")
        assert is_valid is False, "DELETE语句未被拦截"
        assert "DELETE" in msg
        print_success("DELETE语句被正确拦截")

        # 测试非法SQL - DROP
        is_valid, msg = ReportService.validate_sql("DROP TABLE users")
        assert is_valid is False, "DROP语句未被拦截"
        assert "DROP" in msg
        print_success("DROP语句被正确拦截")

        # 测试非法SQL - UPDATE
        is_valid, msg = ReportService.validate_sql("UPDATE users SET name='test'")
        assert is_valid is False, "UPDATE语句未被拦截"
        assert "UPDATE" in msg
        print_success("UPDATE语句被正确拦截")

        return True
    except Exception as e:
        print_error(f"SQL验证测试失败: {str(e)}")
        return False


def test_system_names():
    """测试系统名称选项"""
    print_header("3. 测试系统名称选项")

    try:
        options = asyncio.run(ReportService.get_system_name_options())
        assert isinstance(options, list), "返回类型错误"
        assert len(options) > 0, "选项列表为空"
        assert "订单系统" in options, "缺少默认选项"
        print_success(f"系统名称选项获取成功，共{len(options)}个选项")
        print(f"   选项列表: {', '.join(options)}")
        return True
    except Exception as e:
        print_error(f"系统名称选项测试失败: {str(e)}")
        return False


def test_config():
    """测试配置"""
    print_header("4. 测试配置")

    try:
        # 测试报表配置
        assert hasattr(config, 'report'), "缺少report配置"
        report_config = config.report

        assert hasattr(report_config, 'report_dir'), "缺少report_dir配置"
        assert hasattr(report_config, 'max_rows_per_sheet'), "缺少max_rows_per_sheet配置"
        assert hasattr(report_config, 'max_sheets_per_file'), "缺少max_sheets_per_file配置"
        assert hasattr(report_config, 'page_size'), "缺少page_size配置"

        print_success(f"报表目录: {report_config.report_dir}")
        print_success(f"每sheet最大行数: {report_config.max_rows_per_sheet}")
        print_success(f"每文件最大sheet数: {report_config.max_sheets_per_file}")
        print_success(f"分页大小: {report_config.page_size}")

        return True
    except Exception as e:
        print_error(f"配置测试失败: {str(e)}")
        return False


def test_services():
    """测试服务类"""
    print_header("5. 测试服务类")

    try:
        # 测试ReportService
        assert hasattr(ReportService, 'create_config')
        assert hasattr(ReportService, 'update_config')
        assert hasattr(ReportService, 'delete_config')
        assert hasattr(ReportService, 'get_config_list')
        assert hasattr(ReportService, 'check_permission')
        assert hasattr(ReportService, 'validate_sql')
        print_success("ReportService方法完整")

        # 测试SQLExecutionService
        assert hasattr(SQLExecutionService, 'get_connection')
        assert hasattr(SQLExecutionService, 'execute_query')
        assert hasattr(SQLExecutionService, 'get_total_count')
        print_success("SQLExecutionService方法完整")

        # 测试ExcelExportService
        assert hasattr(ExcelExportService, 'export_report')
        assert hasattr(ExcelExportService, '_execute_export')
        assert hasattr(ExcelExportService, '_write_data_to_sheet')
        print_success("ExcelExportService方法完整")

        # 测试配置常量
        assert ExcelExportService.MAX_ROWS_PER_SHEET == 500000
        assert ExcelExportService.MAX_SHEETS_PER_FILE == 2
        assert ExcelExportService.PAGE_SIZE == 1000
        print_success("ExcelExportService配置常量正确")

        return True
    except Exception as e:
        print_error(f"服务类测试失败: {str(e)}")
        return False


def test_api_routes():
    """测试API路由"""
    print_header("6. 测试API路由")

    try:
        from app.api.v1.report import report_router

        routes = [route.path for route in report_router.routes]
        required_routes = [
            '/config/list',
            '/config/detail',
            '/config/create',
            '/config/update',
            '/config/delete',
            '/options/systems',
            '/generate',
            '/generation/list',
            '/generation/download',
            '/generation/delete'
        ]

        for route in required_routes:
            assert route in routes, f"缺少路由: {route}"

        print_success(f"API路由完整，共{len(routes)}个路由")
        for route in routes:
            print(f"   - {route}")

        return True
    except Exception as e:
        print_error(f"API路由测试失败: {str(e)}")
        return False


def test_file_structure():
    """测试文件结构"""
    print_header("7. 测试文件结构")

    try:
        base_path = Path(__file__).parent.parent

        # 检查后端文件
        backend_files = [
            'app/models/report.py',
            'app/schemas/report.py',
            'app/services/report_service.py',
            'app/services/sql_execution_service.py',
            'app/services/excel_export_service.py',
            'app/api/v1/report/report.py',
            'app/api/v1/report/__init__.py'
        ]

        for file_path in backend_files:
            full_path = base_path / file_path
            assert full_path.exists(), f"文件不存在: {file_path}"
        print_success("后端文件完整")

        # 检查前端文件
        frontend_files = [
            'web/src/views/report/config/index.vue',
            'web/src/views/report/generation/index.vue'
        ]

        for file_path in frontend_files:
            full_path = base_path / file_path
            assert full_path.exists(), f"文件不存在: {file_path}"
        print_success("前端文件完整")

        # 检查上传目录
        upload_dir = base_path / 'uploads' / 'reports'
        assert upload_dir.exists(), "上传目录不存在"
        print_success(f"上传目录存在: {upload_dir}")

        return True
    except Exception as e:
        print_error(f"文件结构测试失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  报表管理功能验收测试")
    print("=" * 60)

    tests = [
        ("模型定义", test_models),
        ("SQL安全验证", test_sql_validation),
        ("系统名称选项", test_system_names),
        ("配置", test_config),
        ("服务类", test_services),
        ("API路由", test_api_routes),
        ("文件结构", test_file_structure)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"{name}测试异常: {str(e)}")
            results.append((name, False))

    # 打印总结
    print_header("测试总结")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {name}")

    print("\n" + "=" * 60)
    print(f"  测试结果: {passed}/{total} 通过")
    print("=" * 60)

    if passed == total:
        print("\n[SUCCESS] 所有测试通过！报表管理功能开发完成！\n")
        return 0
    else:
        print(f"\n[WARNING] 有 {total - passed} 项测试失败，请检查！\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
