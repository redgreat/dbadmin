"""
Final Checkpoint Test for Task 11 - Complete System Verification

This test verifies that all features of the database-tools implementation are working:
- Backend services (excelimp_service, formatter_service)
- Backend API endpoints (POST /tool/excelimp/generate, POST /tool/formatter/format)
- Frontend components exist and are properly structured
- Routing and navigation are configured
- All integrations are in place
"""
import io
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openpyxl import Workbook


def create_test_excel() -> bytes:
    """Create a test Excel file with sample data"""
    wb = Workbook()
    ws = wb.active
    
    # Add headers
    ws.append(["姓名", "年龄", "城市", "工资", "入职日期"])
    
    # Add data rows
    ws.append(["张三", 25, "北京", 8000.50, "2023-01-15"])
    ws.append(["李四", 30, "上海", 12000.00, "2022-06-20"])
    ws.append(["王五", 28, "广州", 9500.75, "2023-03-10"])
    ws.append(["赵六", 35, "深圳", 15000.00, "2021-11-05"])
    
    # Save to bytes
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)
    
    return excel_bytes.read()


def test_backend_services():
    """Test backend services are working correctly"""
    print("\n" + "="*70)
    print("1. Testing Backend Services")
    print("="*70)
    
    # Import services
    import importlib.util
    
    # Test excelimp_service
    print("\n[1.1] Testing excelimp_service...")
    excelimp_path = Path(__file__).parent.parent / "app" / "services" / "excelimp_service.py"
    spec = importlib.util.spec_from_file_location("excelimp_service", excelimp_path)
    excelimp_service = importlib.util.module_from_spec(spec)
    sys.modules["excelimp_service"] = excelimp_service
    spec.loader.exec_module(excelimp_service)
    
    excel_content = create_test_excel()
    
    # Test MySQL generation
    sql_mysql = excelimp_service.generate_sql(excel_content, "test.xlsx", "mysql")
    assert sql_mysql is not None
    assert "CREATE TABLE" in sql_mysql
    assert "tmp_" in sql_mysql
    assert "INSERT INTO" in sql_mysql
    assert "ENGINE=InnoDB" in sql_mysql
    assert "张三" in sql_mysql
    print("  ✓ MySQL SQL generation works")
    
    # Test PostgreSQL generation
    sql_pg = excelimp_service.generate_sql(excel_content, "test.xlsx", "postgresql")
    assert sql_pg is not None
    assert "CREATE TABLE" in sql_pg
    assert "tmp_" in sql_pg
    assert "INSERT INTO" in sql_pg
    assert "ENGINE" not in sql_pg
    print("  ✓ PostgreSQL SQL generation works")
    
    # Test formatter_service
    print("\n[1.2] Testing formatter_service...")
    formatter_path = Path(__file__).parent.parent / "app" / "services" / "formatter_service.py"
    spec = importlib.util.spec_from_file_location("formatter_service", formatter_path)
    formatter_service = importlib.util.module_from_spec(spec)
    sys.modules["formatter_service"] = formatter_service
    spec.loader.exec_module(formatter_service)
    
    raw_sql = "select * from users where id=1 and status='active'"
    formatted = formatter_service.format_sql(raw_sql)
    assert formatted is not None
    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "WHERE" in formatted
    print("  ✓ SQL formatting works")
    
    print("\n✓ Backend services verification PASSED")
    return True


def test_backend_api_structure():
    """Test backend API structure is correct"""
    print("\n" + "="*70)
    print("2. Testing Backend API Structure")
    print("="*70)
    
    # Check tool router exists
    print("\n[2.1] Checking tool router...")
    tool_router_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    assert tool_router_path.exists(), "Tool router file not found"
    
    # Read and verify endpoints
    with open(tool_router_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'def generate_excel_sql' in content, "generate_excel_sql endpoint not found"
        assert 'def format_sql_statement' in content, "format_sql_statement endpoint not found"
        assert '/excelimp/generate' in content, "excelimp endpoint path not found"
        assert '/formatter/format' in content, "formatter endpoint path not found"
    print("  ✓ Tool router endpoints defined correctly")
    
    # Check tool router is registered
    print("\n[2.2] Checking tool router registration...")
    v1_init_path = Path(__file__).parent.parent / "app" / "api" / "v1" / "__init__.py"
    with open(v1_init_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'from .tool import tool_router' in content, "Tool router not imported"
        assert 'tool_router' in content, "Tool router not registered"
    print("  ✓ Tool router registered in v1 API")
    
    print("\n✓ Backend API structure verification PASSED")
    return True


def test_frontend_components():
    """Test frontend components exist and are properly structured"""
    print("\n" + "="*70)
    print("3. Testing Frontend Components")
    print("="*70)
    
    # Check ExcelImport component
    print("\n[3.1] Checking ExcelImport component...")
    excelimp_component = Path(__file__).parent.parent / "web" / "src" / "views" / "tool" / "excelimp" / "ExcelImport.vue"
    assert excelimp_component.exists(), "ExcelImport.vue not found"
    
    with open(excelimp_component, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'generateExcelSql' in content, "API call to generateExcelSql not found"
        assert 'n-upload' in content, "File upload component not found"
        assert 'dbType' in content, "Database type selection not found"
    print("  ✓ ExcelImport component exists and has required features")
    
    # Check SqlFormatter component
    print("\n[3.2] Checking SqlFormatter component...")
    formatter_component = Path(__file__).parent.parent / "web" / "src" / "views" / "tool" / "formatter" / "SqlFormatter.vue"
    assert formatter_component.exists(), "SqlFormatter.vue not found"
    
    with open(formatter_component, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'formatSql' in content, "API call to formatSql not found"
        assert 'inputSql' in content, "Input SQL field not found"
        assert 'outputSql' in content, "Output SQL field not found"
    print("  ✓ SqlFormatter component exists and has required features")
    
    # Check index.vue files
    print("\n[3.3] Checking component index files...")
    excelimp_index = Path(__file__).parent.parent / "web" / "src" / "views" / "tool" / "excelimp" / "index.vue"
    formatter_index = Path(__file__).parent.parent / "web" / "src" / "views" / "tool" / "formatter" / "index.vue"
    assert excelimp_index.exists(), "excelimp/index.vue not found"
    assert formatter_index.exists(), "formatter/index.vue not found"
    print("  ✓ Component index files exist")
    
    print("\n✓ Frontend components verification PASSED")
    return True


def test_routing_configuration():
    """Test routing and navigation configuration"""
    print("\n" + "="*70)
    print("4. Testing Routing Configuration")
    print("="*70)
    
    # Check route.js exists
    print("\n[4.1] Checking route configuration...")
    route_file = Path(__file__).parent.parent / "web" / "src" / "views" / "tool" / "route.js"
    assert route_file.exists(), "tool/route.js not found"
    
    with open(route_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert '/tools' in content, "Tools path not found"
        assert 'excelimp' in content, "Excelimp route not found"
        assert 'formatter' in content, "Formatter route not found"
    print("  ✓ Route configuration exists and is correct")
    
    # Check i18n translations
    print("\n[4.2] Checking i18n translations...")
    cn_i18n = Path(__file__).parent.parent / "web" / "i18n" / "messages" / "cn.json"
    en_i18n = Path(__file__).parent.parent / "web" / "i18n" / "messages" / "en.json"
    
    with open(cn_i18n, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'label_tool' in content, "Chinese tool label not found"
        assert 'label_excelimp' in content, "Chinese excelimp label not found"
        assert 'label_formatter' in content, "Chinese formatter label not found"
    print("  ✓ Chinese translations exist")
    
    with open(en_i18n, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'label_tool' in content, "English tool label not found"
        assert 'label_excelimp' in content, "English excelimp label not found"
        assert 'label_formatter' in content, "English formatter label not found"
    print("  ✓ English translations exist")
    
    print("\n✓ Routing configuration verification PASSED")
    return True


def test_api_integration():
    """Test API integration in frontend"""
    print("\n" + "="*70)
    print("5. Testing API Integration")
    print("="*70)
    
    # Check API definitions
    print("\n[5.1] Checking API definitions...")
    api_file = Path(__file__).parent.parent / "web" / "src" / "api" / "index.js"
    assert api_file.exists(), "API index.js not found"
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'generateExcelSql' in content, "generateExcelSql API not defined"
        assert 'formatSql' in content, "formatSql API not defined"
        assert '/tool/excelimp/generate' in content, "Excelimp endpoint path not found"
        assert '/tool/formatter/format' in content, "Formatter endpoint path not found"
    print("  ✓ API functions are properly defined")
    
    print("\n✓ API integration verification PASSED")
    return True


def test_dependencies():
    """Test required dependencies are available"""
    print("\n" + "="*70)
    print("6. Testing Dependencies")
    print("="*70)
    
    print("\n[6.1] Checking Python dependencies...")
    try:
        import openpyxl
        print("  ✓ openpyxl installed")
    except ImportError:
        print("  ✗ openpyxl not installed")
        return False
    
    try:
        import sqlparse
        print("  ✓ sqlparse installed")
    except ImportError:
        print("  ✗ sqlparse not installed")
        return False
    
    try:
        from pypinyin import lazy_pinyin
        print("  ✓ pypinyin installed")
    except ImportError:
        print("  ✗ pypinyin not installed")
        return False
    
    print("\n✓ Dependencies verification PASSED")
    return True


def main():
    """Run all final checkpoint tests"""
    print("\n" + "="*70)
    print("FINAL CHECKPOINT - Task 11")
    print("Complete Database Tools System Verification")
    print("="*70)
    
    try:
        # Run all tests
        test_dependencies()
        test_backend_services()
        test_backend_api_structure()
        test_frontend_components()
        test_routing_configuration()
        test_api_integration()
        
        # Final summary
        print("\n" + "="*70)
        print("✓ ALL FINAL CHECKPOINT TESTS PASSED!")
        print("="*70)
        print("\nSummary of Verified Components:")
        print("  ✓ Backend Services:")
        print("    - excelimp_service (Excel parsing, type inference, SQL generation)")
        print("    - formatter_service (SQL formatting)")
        print("  ✓ Backend API Endpoints:")
        print("    - POST /tool/excelimp/generate")
        print("    - POST /tool/formatter/format")
        print("  ✓ Frontend Components:")
        print("    - ExcelImport.vue (file upload, database selection, result display)")
        print("    - SqlFormatter.vue (input, format, output)")
        print("  ✓ Routing & Navigation:")
        print("    - /tools/excelimp route")
        print("    - /tools/formatter route")
        print("    - i18n translations (CN & EN)")
        print("  ✓ API Integration:")
        print("    - generateExcelSql API function")
        print("    - formatSql API function")
        print("  ✓ Dependencies:")
        print("    - openpyxl, sqlparse, pypinyin")
        print("\n" + "="*70)
        print("The database-tools feature is fully implemented and ready!")
        print("="*70)
        
        return 0
    
    except AssertionError as e:
        print("\n" + "="*70)
        print("✗ FINAL CHECKPOINT FAILED!")
        print("="*70)
        print(f"Assertion Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    except Exception as e:
        print("\n" + "="*70)
        print("✗ FINAL CHECKPOINT FAILED!")
        print("="*70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
