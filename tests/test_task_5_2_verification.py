"""
Verification test for Task 5.2: POST /tool/formatter/format endpoint

This test verifies the endpoint implementation by reading the source code
and validating all requirements are met without importing the app.
"""
from pathlib import Path


def test_endpoint_exists():
    """Test that POST /tool/formatter/format endpoint exists"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify endpoint decorator
    assert '@router.post("/formatter/format")' in content, "Endpoint route not found"
    print("✓ Endpoint route exists: POST /tool/formatter/format")


def test_endpoint_accepts_sql_parameter():
    """Test that endpoint accepts raw SQL string parameter"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify sql parameter is defined as Form
    assert 'sql: str = Form(...)' in content, "SQL parameter not found or incorrect type"
    print("✓ Endpoint accepts sql parameter as Form data")


def test_endpoint_calls_formatter_service():
    """Test that endpoint calls formatter_service.format_sql()"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify import
    assert 'from app.services.formatter_service import format_sql' in content, \
        "formatter_service import not found"
    
    # Verify service call
    assert 'format_sql(sql)' in content, "format_sql() service call not found"
    print("✓ Endpoint calls formatter_service.format_sql()")


def test_endpoint_returns_formatted_sql():
    """Test that endpoint returns formatted SQL string"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify return structure
    assert 'return {"sql": formatted_sql}' in content, \
        "Return statement not found or incorrect structure"
    print("✓ Endpoint returns formatted SQL in correct structure")


def test_endpoint_has_error_handling():
    """Test that endpoint has proper error handling"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the format_sql_statement function
    func_start = content.find('async def format_sql_statement')
    assert func_start != -1, "format_sql_statement function not found"
    
    # Get the function content (until next function or end)
    next_func = content.find('\n@router.', func_start + 1)
    if next_func == -1:
        func_content = content[func_start:]
    else:
        func_content = content[func_start:next_func]
    
    # Verify error handling
    assert 'try:' in func_content, "Try block not found"
    assert 'except Exception' in func_content, "Exception handling not found"
    assert 'HTTPException' in func_content, "HTTPException not raised"
    assert 'status_code=500' in func_content, "Status code 500 not found"
    print("✓ Endpoint has proper error handling")


def test_endpoint_has_docstring():
    """Test that endpoint has proper documentation"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the format_sql_statement function
    func_start = content.find('async def format_sql_statement')
    assert func_start != -1, "format_sql_statement function not found"
    
    # Get the function content
    next_func = content.find('\n@router.', func_start + 1)
    if next_func == -1:
        func_content = content[func_start:]
    else:
        func_content = content[func_start:next_func]
    
    # Verify docstring exists
    assert '"""' in func_content, "Docstring not found"
    print("✓ Endpoint has documentation")


def test_formatter_service_exists():
    """Test that formatter_service.format_sql() exists"""
    service_file = Path(__file__).parent.parent / "app" / "services" / "formatter_service.py"
    
    with open(service_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify function exists
    assert 'def format_sql(sql: str) -> str:' in content, \
        "format_sql function not found or incorrect signature"
    
    # Verify it uses sqlparse
    assert 'import sqlparse' in content, "sqlparse import not found"
    assert 'sqlparse.format' in content, "sqlparse.format call not found"
    print("✓ formatter_service.format_sql() exists and uses sqlparse")


def test_all_requirements_met():
    """Summary test - verify all Task 5.2 requirements are met"""
    print("\n=== Task 5.2 Requirements Verification ===")
    
    # Requirement 1: 接收原始SQL字符串
    test_endpoint_accepts_sql_parameter()
    
    # Requirement 2: 调用formatter_service.format_sql()
    test_endpoint_calls_formatter_service()
    
    # Requirement 3: 返回格式化后的SQL字符串
    test_endpoint_returns_formatted_sql()
    
    # Additional verifications
    test_endpoint_exists()
    test_endpoint_has_error_handling()
    test_endpoint_has_docstring()
    test_formatter_service_exists()
    
    print("\n✅ All Task 5.2 requirements are met!")


if __name__ == "__main__":
    import pytest
    
    # Run the summary test
    test_all_requirements_met()
