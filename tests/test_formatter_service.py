"""
Tests for formatter_service - SQL formatting functionality
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.services.formatter_service import format_sql


def test_format_single_sql_statement():
    """Test formatting a single SQL statement with sqlparse library"""
    raw_sql = "select * from users where id=1 and name='test'"
    formatted = format_sql(raw_sql)
    
    # Verify keywords are uppercase
    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "WHERE" in formatted
    assert "AND" in formatted
    
    # Verify it's formatted (has newlines for readability)
    assert "\n" in formatted


def test_format_with_keyword_uppercase():
    """Test that formatting options include keyword uppercase"""
    raw_sql = "select id, name from users"
    formatted = format_sql(raw_sql)
    
    # Keywords should be uppercase
    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "select" not in formatted
    assert "from" not in formatted


def test_format_with_indentation():
    """Test that formatting includes proper indentation"""
    raw_sql = "select id, name from users where status='active' and role='admin'"
    formatted = format_sql(raw_sql)
    
    # Should have indentation (spaces at start of lines)
    lines = formatted.split('\n')
    # At least one line should have leading spaces (indentation)
    has_indentation = any(line.startswith(' ') for line in lines if line)
    assert has_indentation


def test_format_multiple_sql_statements():
    """Test handling multiple SQL statements separated by semicolons"""
    raw_sql = """
    select * from users where id=1;
    update users set name='test' where id=2;
    delete from users where id=3;
    """
    formatted = format_sql(raw_sql)
    
    # All statements should be formatted
    assert "SELECT" in formatted
    assert "UPDATE" in formatted
    assert "DELETE" in formatted
    assert "FROM" in formatted
    assert "WHERE" in formatted
    assert "SET" in formatted
    
    # Should maintain semicolons
    assert ";" in formatted


def test_format_empty_string():
    """Test handling empty string input"""
    assert format_sql("") == ""
    assert format_sql("   ") == "   "


def test_format_complex_query():
    """Test formatting a complex query with joins and subqueries"""
    raw_sql = """
    select u.id, u.name, o.order_id from users u 
    inner join orders o on u.id=o.user_id 
    where u.status='active' and o.total > 100
    """
    formatted = format_sql(raw_sql)
    
    # Verify keywords are uppercase
    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "INNER JOIN" in formatted
    assert "ON" in formatted
    assert "WHERE" in formatted
    assert "AND" in formatted


def test_format_create_table_statement():
    """Test formatting CREATE TABLE statement"""
    raw_sql = "create table users (id int primary key, name varchar(100), email varchar(255))"
    formatted = format_sql(raw_sql)
    
    # Keywords should be uppercase
    assert "CREATE TABLE" in formatted
    assert "PRIMARY KEY" in formatted


def test_format_insert_statement():
    """Test formatting INSERT statement"""
    raw_sql = "insert into users (id, name, email) values (1, 'test', 'test@example.com')"
    formatted = format_sql(raw_sql)
    
    # Keywords should be uppercase
    assert "INSERT INTO" in formatted
    assert "VALUES" in formatted
