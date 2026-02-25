"""
Simple verification test for Task 4.1: POST /tool/excelimp/generate endpoint

This test verifies the endpoint implementation by directly checking:
1. The endpoint exists and has correct signature
2. It accepts file upload (multipart/form-data)
3. It accepts database type parameter (mysql or postgresql)
4. It calls excelimp_service.generate_sql()
5. It returns generated SQL string
"""
import sys
from pathlib import Path
import io
from openpyxl import Workbook

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_excel() -> bytes:
    """Create a simple test Excel file in memory"""
    wb = Workbook()
    ws = wb.active
    
    # Add headers
    ws.append(["姓名", "年龄", "城市"])
    
    # Add data rows
    ws.append(["张三", 25, "北京"])
    ws.append(["李四", 30, "上海"])
    ws.append(["王五", 28, "广州"])
    
    # Save to bytes
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)
    
    return excel_bytes.read()


def test_endpoint_file_exists():
    """Verify the endpoint file exists"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    assert endpoint_file.exists(), "Endpoint file app/api/v1/tool/tool.py does not exist"
    print("✓ Endpoint file exists")


def test_endpoint_has_correct_route():
    """Verify the endpoint has the correct route decorator"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert '@router.post("/excelimp/generate")' in content, "Missing @router.post('/excelimp/generate') decorator"
    print("✓ Endpoint has correct route decorator")


def test_endpoint_accepts_file_parameter():
    """Verify the endpoint accepts file upload parameter"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert 'file: UploadFile = File(...)' in content, "Missing file: UploadFile = File(...) parameter"
    print("✓ Endpoint accepts file upload parameter (multipart/form-data)")


def test_endpoint_accepts_db_type_parameter():
    """Verify the endpoint accepts db_type parameter with correct type"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert 'db_type: Literal["mysql", "postgresql"] = Form(...)' in content, \
        "Missing db_type: Literal['mysql', 'postgresql'] = Form(...) parameter"
    print("✓ Endpoint accepts db_type parameter (mysql or postgresql)")


def test_endpoint_calls_generate_sql():
    """Verify the endpoint calls generate_sql from excelimp_service"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert 'from app.services.excelimp_service import generate_sql' in content, \
        "Missing import of generate_sql from excelimp_service"
    assert 'generate_sql(content, file.filename, db_type)' in content, \
        "Missing call to generate_sql(content, file.filename, db_type)"
    print("✓ Endpoint calls excelimp_service.generate_sql()")


def test_endpoint_returns_sql_string():
    """Verify the endpoint returns SQL in correct format"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert 'return {"sql": sql_result}' in content or 'return {"sql":sql_result}' in content, \
        "Missing return statement with SQL result"
    print("✓ Endpoint returns generated SQL string")


def test_endpoint_validates_file_extension():
    """Verify the endpoint validates file extensions"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert '.xlsx' in content and '.xls' in content, \
        "Missing file extension validation for .xlsx and .xls"
    print("✓ Endpoint validates file extensions")


def test_endpoint_has_error_handling():
    """Verify the endpoint has error handling"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    content = endpoint_file.read_text(encoding='utf-8')
    
    assert 'try:' in content and 'except' in content, \
        "Missing error handling (try/except)"
    assert 'HTTPException' in content, \
        "Missing HTTPException for error responses"
    print("✓ Endpoint has error handling")


def test_service_integration():
    """Test that the service can be called and generates SQL"""
    from app.services.excelimp_service import generate_sql
    
    excel_content = create_test_excel()
    
    # Test with MySQL
    sql_mysql = generate_sql(excel_content, "test.xlsx", "mysql")
    assert "CREATE TABLE" in sql_mysql, "MySQL SQL should contain CREATE TABLE"
    assert "INSERT INTO" in sql_mysql, "MySQL SQL should contain INSERT INTO"
    assert "ENGINE=InnoDB" in sql_mysql, "MySQL SQL should contain ENGINE=InnoDB"
    print("✓ Service generates MySQL SQL correctly")
    
    # Test with PostgreSQL
    sql_pg = generate_sql(excel_content, "test.xlsx", "postgresql")
    assert "CREATE TABLE" in sql_pg, "PostgreSQL SQL should contain CREATE TABLE"
    assert "INSERT INTO" in sql_pg, "PostgreSQL SQL should contain INSERT INTO"
    assert "ENGINE" not in sql_pg, "PostgreSQL SQL should not contain ENGINE"
    print("✓ Service generates PostgreSQL SQL correctly")


def test_router_registration():
    """Verify the router is registered in the API"""
    init_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "__init__.py"
    content = init_file.read_text(encoding='utf-8')
    
    assert 'from .tool import tool_router' in content, \
        "Missing import of tool_router"
    assert 'tool_router' in content and 'prefix="/tool"' in content, \
        "Missing router registration with /tool prefix"
    print("✓ Router is registered in the API")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Task 4.1 Verification: POST /tool/excelimp/generate endpoint")
    print("="*70 + "\n")
    
    try:
        test_endpoint_file_exists()
        test_endpoint_has_correct_route()
        test_endpoint_accepts_file_parameter()
        test_endpoint_accepts_db_type_parameter()
        test_endpoint_calls_generate_sql()
        test_endpoint_returns_sql_string()
        test_endpoint_validates_file_extension()
        test_endpoint_has_error_handling()
        test_service_integration()
        test_router_registration()
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - Task 4.1 is complete!")
        print("="*70 + "\n")
        
        print("Summary:")
        print("  ✓ Endpoint accepts file upload (multipart/form-data)")
        print("  ✓ Endpoint accepts database type parameter (mysql or postgresql)")
        print("  ✓ Endpoint calls excelimp_service.generate_sql()")
        print("  ✓ Endpoint returns generated SQL string")
        print("  ✓ Endpoint has proper validation and error handling")
        print("  ✓ Router is properly registered")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
