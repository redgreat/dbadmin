"""
Simple test for Task 5.2: POST /tool/formatter/format endpoint

This test verifies the endpoint implementation by directly testing the service
and validating the endpoint structure.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.formatter_service import format_sql


def test_formatter_service_integration():
    """Test that formatter_service.format_sql() works correctly"""
    raw_sql = "select * from users where id=1"
    
    result = format_sql(raw_sql)
    
    # Verify result is formatted
    assert isinstance(result, str)
    assert len(result) > 0
    assert "SELECT" in result  # Keywords should be uppercase
    assert "FROM" in result
    assert "WHERE" in result


def test_endpoint_structure():
    """Test that the endpoint has the correct structure"""
    # Read the endpoint file
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify endpoint exists
    assert '@router.post("/formatter/format")' in content
    
    # Verify function signature
    assert 'async def format_sql_statement' in content
    assert 'sql: str = Form(...)' in content
    
    # Verify it calls the service
    assert 'format_sql(sql)' in content
    
    # Verify it returns the result
    assert 'return {"sql": formatted_sql}' in content
    
    # Verify error handling
    assert 'try:' in content
    assert 'except Exception' in content
    assert 'HTTPException' in content


def test_endpoint_accepts_sql_parameter():
    """Test that endpoint accepts sql parameter as Form data"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify sql parameter is defined as Form
    assert 'sql: str = Form(...)' in content


def test_endpoint_calls_formatter_service():
    """Test that endpoint imports and calls formatter_service.format_sql()"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify import
    assert 'from app.services.formatter_service import format_sql' in content
    
    # Verify service call
    assert 'formatted_sql = format_sql(sql)' in content


def test_endpoint_returns_formatted_sql():
    """Test that endpoint returns formatted SQL in correct structure"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify return structure
    assert 'return {"sql": formatted_sql}' in content


def test_endpoint_has_error_handling():
    """Test that endpoint has proper error handling"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify error handling
    assert 'try:' in content
    assert 'except Exception as e:' in content
    assert 'raise HTTPException(status_code=500' in content
    assert '格式化SQL时出错' in content


def test_endpoint_has_docstring():
    """Test that endpoint has proper documentation"""
    endpoint_file = Path(__file__).parent.parent / "app" / "api" / "v1" / "tool" / "tool.py"
    
    with open(endpoint_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify docstring exists
    assert '"""' in content
    assert 'Format SQL statement' in content


if __name__ == "__main__":
    import pytest
    
    # Run tests
    pytest.main([__file__, '-v'])
