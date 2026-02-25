"""
Test for Task 5.2: POST /tool/formatter/format endpoint

This test verifies that the endpoint:
1. Accepts raw SQL string
2. Calls formatter_service.format_sql()
3. Returns formatted SQL string
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch, Mock
from fastapi import HTTPException
import pytest


async def test_endpoint_accepts_sql_string():
    """Test that endpoint accepts raw SQL string"""
    # Import here to avoid dependency issues
    from app.api.v1.tool.tool import format_sql_statement
    
    raw_sql = "select * from users where id=1"
    
    result = await format_sql_statement(sql=raw_sql)
    
    # Verify result
    assert "sql" in result
    assert isinstance(result["sql"], str)
    assert len(result["sql"]) > 0


async def test_endpoint_calls_format_sql_service():
    """Test that endpoint calls formatter_service.format_sql()"""
    raw_sql = "select * from users where id=1"
    
    # Patch the format_sql service to verify it's called
    with patch('app.api.v1.tool.tool.format_sql') as mock_format:
        mock_format.return_value = "SELECT *\nFROM users\nWHERE id = 1"
        
        result = await format_sql_statement(sql=raw_sql)
        
        # Verify service was called with correct parameters
        mock_format.assert_called_once_with(raw_sql)
        
        # Verify result contains the mocked return value
        assert result["sql"] == "SELECT *\nFROM users\nWHERE id = 1"


async def test_endpoint_returns_formatted_sql():
    """Test that endpoint returns formatted SQL string"""
    raw_sql = "select id,name,email from users where status='active' and role='admin'"
    
    result = await format_sql_statement(sql=raw_sql)
    
    # Verify response structure
    assert isinstance(result, dict)
    assert "sql" in result
    assert isinstance(result["sql"], str)
    assert len(result["sql"]) > 0
    
    # Verify SQL is formatted (keywords uppercase)
    formatted_sql = result["sql"]
    assert "SELECT" in formatted_sql
    assert "FROM" in formatted_sql
    assert "WHERE" in formatted_sql
    assert "AND" in formatted_sql


async def test_endpoint_formats_complex_sql():
    """Test that endpoint formats complex SQL with joins"""
    raw_sql = "select u.id, u.name, o.order_id from users u inner join orders o on u.id=o.user_id where u.status='active'"
    
    result = await format_sql_statement(sql=raw_sql)
    
    formatted_sql = result["sql"]
    
    # Verify keywords are uppercase
    assert "SELECT" in formatted_sql
    assert "FROM" in formatted_sql
    assert "INNER JOIN" in formatted_sql
    assert "ON" in formatted_sql
    assert "WHERE" in formatted_sql


async def test_endpoint_handles_empty_sql():
    """Test that endpoint handles empty SQL string"""
    result = await format_sql_statement(sql="")
    
    assert "sql" in result
    assert result["sql"] == ""


async def test_endpoint_handles_whitespace_only():
    """Test that endpoint handles whitespace-only SQL string"""
    result = await format_sql_statement(sql="   ")
    
    assert "sql" in result
    assert result["sql"] == "   "


async def test_endpoint_formats_multiple_statements():
    """Test that endpoint formats multiple SQL statements"""
    raw_sql = "select * from users; update users set name='test' where id=1; delete from users where id=2;"
    
    result = await format_sql_statement(sql=raw_sql)
    
    formatted_sql = result["sql"]
    
    # Verify all statements are formatted
    assert "SELECT" in formatted_sql
    assert "UPDATE" in formatted_sql
    assert "DELETE" in formatted_sql
    assert "FROM" in formatted_sql
    assert "WHERE" in formatted_sql
    assert "SET" in formatted_sql


async def test_endpoint_handles_error():
    """Test that endpoint handles errors gracefully"""
    from fastapi import HTTPException
    import pytest
    
    # Patch format_sql to raise an exception
    with patch('app.api.v1.tool.tool.format_sql') as mock_format:
        mock_format.side_effect = Exception("Test error")
        
        with pytest.raises(HTTPException) as exc_info:
            await format_sql_statement(sql="select * from users")
        
        assert exc_info.value.status_code == 500
        assert "格式化SQL时出错" in exc_info.value.detail


if __name__ == "__main__":
    import asyncio
    
    # Run async tests
    asyncio.run(test_endpoint_accepts_sql_string())
    asyncio.run(test_endpoint_calls_format_sql_service())
    asyncio.run(test_endpoint_returns_formatted_sql())
    asyncio.run(test_endpoint_formats_complex_sql())
    asyncio.run(test_endpoint_handles_empty_sql())
    asyncio.run(test_endpoint_handles_whitespace_only())
    asyncio.run(test_endpoint_formats_multiple_statements())
    asyncio.run(test_endpoint_handles_error())
    
    print("All tests passed!")
