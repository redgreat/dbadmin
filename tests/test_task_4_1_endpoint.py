"""
Test for Task 4.1: POST /tool/excelimp/generate endpoint

This test verifies that the endpoint:
1. Accepts file upload (multipart/form-data)
2. Accepts database type parameter (mysql or postgresql)
3. Calls excelimp_service.generate_sql()
4. Returns generated SQL string
"""
import io
import sys
from pathlib import Path
from openpyxl import Workbook

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.v1.tool.tool import generate_excel_sql
from fastapi import UploadFile
from unittest.mock import Mock, patch


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


async def test_endpoint_accepts_file_upload():
    """Test that endpoint accepts file upload (multipart/form-data)"""
    excel_content = create_test_excel()
    
    # Create mock UploadFile
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xlsx"
    mock_file.read = Mock(return_value=excel_content)
    
    # Call endpoint
    result = await generate_excel_sql(file=mock_file, db_type="mysql")
    
    # Verify result
    assert "sql" in result
    assert isinstance(result["sql"], str)
    assert len(result["sql"]) > 0


async def test_endpoint_accepts_db_type_mysql():
    """Test that endpoint accepts database type parameter - MySQL"""
    excel_content = create_test_excel()
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xlsx"
    mock_file.read = Mock(return_value=excel_content)
    
    result = await generate_excel_sql(file=mock_file, db_type="mysql")
    
    assert "sql" in result
    assert "ENGINE=InnoDB" in result["sql"]  # MySQL specific


async def test_endpoint_accepts_db_type_postgresql():
    """Test that endpoint accepts database type parameter - PostgreSQL"""
    excel_content = create_test_excel()
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xlsx"
    mock_file.read = Mock(return_value=excel_content)
    
    result = await generate_excel_sql(file=mock_file, db_type="postgresql")
    
    assert "sql" in result
    # PostgreSQL doesn't have ENGINE clause
    assert "ENGINE" not in result["sql"]


async def test_endpoint_calls_generate_sql_service():
    """Test that endpoint calls excelimp_service.generate_sql()"""
    excel_content = create_test_excel()
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xlsx"
    mock_file.read = Mock(return_value=excel_content)
    
    # Patch the generate_sql service to verify it's called
    with patch('app.api.v1.tool.tool.generate_sql') as mock_generate:
        mock_generate.return_value = "CREATE TABLE tmp_test..."
        
        result = await generate_excel_sql(file=mock_file, db_type="mysql")
        
        # Verify service was called with correct parameters
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args[0]
        assert call_args[0] == excel_content  # content
        assert call_args[1] == "test.xlsx"  # filename
        assert call_args[2] == "mysql"  # db_type


async def test_endpoint_returns_sql_string():
    """Test that endpoint returns generated SQL string"""
    excel_content = create_test_excel()
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xlsx"
    mock_file.read = Mock(return_value=excel_content)
    
    result = await generate_excel_sql(file=mock_file, db_type="mysql")
    
    # Verify response structure
    assert isinstance(result, dict)
    assert "sql" in result
    assert isinstance(result["sql"], str)
    assert len(result["sql"]) > 0
    
    # Verify SQL contains expected elements
    sql = result["sql"]
    assert "CREATE TABLE" in sql
    assert "tmp_" in sql  # Temporary table name
    assert "INSERT INTO" in sql


async def test_endpoint_validates_file_extension_xlsx():
    """Test that endpoint accepts .xlsx files"""
    excel_content = create_test_excel()
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xlsx"
    mock_file.read = Mock(return_value=excel_content)
    
    result = await generate_excel_sql(file=mock_file, db_type="mysql")
    assert "sql" in result


async def test_endpoint_validates_file_extension_xls():
    """Test that endpoint accepts .xls files"""
    excel_content = create_test_excel()
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.xls"
    mock_file.read = Mock(return_value=excel_content)
    
    result = await generate_excel_sql(file=mock_file, db_type="mysql")
    assert "sql" in result


async def test_endpoint_rejects_invalid_file_extension():
    """Test that endpoint rejects non-Excel files"""
    from fastapi import HTTPException
    import pytest
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.txt"
    mock_file.read = Mock(return_value=b"invalid content")
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_excel_sql(file=mock_file, db_type="mysql")
    
    assert exc_info.value.status_code == 400
    assert "仅支持" in exc_info.value.detail


async def test_endpoint_rejects_empty_filename():
    """Test that endpoint rejects files with empty filename"""
    from fastapi import HTTPException
    import pytest
    
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = ""
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_excel_sql(file=mock_file, db_type="mysql")
    
    assert exc_info.value.status_code == 400
    assert "文件名不能为空" in exc_info.value.detail

if __name__ == "__main__":
    import pytest
    import asyncio
    
    # Run async tests
    asyncio.run(test_endpoint_accepts_file_upload())
    asyncio.run(test_endpoint_accepts_db_type_mysql())
    asyncio.run(test_endpoint_accepts_db_type_postgresql())
    asyncio.run(test_endpoint_calls_generate_sql_service())
    asyncio.run(test_endpoint_returns_sql_string())
    asyncio.run(test_endpoint_validates_file_extension_xlsx())
    asyncio.run(test_endpoint_validates_file_extension_xls())
    asyncio.run(test_endpoint_rejects_invalid_file_extension())
    asyncio.run(test_endpoint_rejects_empty_filename())
    
    print("All tests passed!")

