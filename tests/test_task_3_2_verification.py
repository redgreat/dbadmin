"""
Verification tests for Task 3.2: INSERT Statement Generation
Tests all requirements:
1. Generate batch INSERT statements (500 rows per batch)
2. Correctly handle string escaping and NULL values
3. Support both MySQL and PostgreSQL syntax
4. Optimize SQL output for large datasets
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.excelimp_service import (
    _generate_insert_statements,
    _format_value
)


class TestTask32Requirements:
    """Verification tests for Task 3.2 requirements"""
    
    def test_requirement_1_batch_generation_500_rows(self):
        """
        Requirement 1: Generate batch INSERT statements (500 rows per batch)
        Verify that data is split into batches of 500 rows
        """
        # Create 1200 rows to test batching
        data_rows = [[i, f"Name{i}"] for i in range(1200)]
        
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name"],
            data_rows,
            "mysql",
            batch_size=500
        )
        
        # Should have 3 INSERT statements (500 + 500 + 200)
        insert_count = sql.count("INSERT INTO test_table")
        assert insert_count == 3, f"Expected 3 INSERT statements, got {insert_count}"
        
        # Verify each batch is separate
        statements = sql.split("INSERT INTO test_table")
        statements = [s for s in statements if s.strip()]  # Remove empty
        
        assert len(statements) == 3
        
        # First batch should have 500 rows
        first_batch = statements[0]
        first_batch_rows = first_batch.count("(0,") + first_batch.count("(1,") + first_batch.count("(2,")
        assert first_batch_rows > 0, "First batch should contain rows"
    
    def test_requirement_2a_string_escaping(self):
        """
        Requirement 2a: Correctly handle string escaping
        Test that single quotes in strings are properly escaped
        """
        # Test single quote escaping
        assert _format_value("O'Brien") == "'O''Brien'"
        assert _format_value("It's a test") == "'It''s a test'"
        assert _format_value("Multiple ' quotes ' here") == "'Multiple '' quotes '' here'"
        
        # Test in INSERT statement
        sql = _generate_insert_statements(
            "test_table",
            ["name"],
            [["O'Brien"], ["It's working"]],
            "mysql"
        )
        
        assert "'O''Brien'" in sql
        assert "'It''s working'" in sql
    
    def test_requirement_2b_null_value_handling(self):
        """
        Requirement 2b: Correctly handle NULL values
        Test that None values are converted to SQL NULL
        """
        # Test NULL formatting
        assert _format_value(None) == "NULL"
        
        # Test in INSERT statement
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name", "age"],
            [[1, None, 25], [2, "Bob", None], [None, None, None]],
            "mysql"
        )
        
        assert "(1, NULL, 25)" in sql
        assert "(2, 'Bob', NULL)" in sql
        assert "(NULL, NULL, NULL)" in sql
    
    def test_requirement_3a_mysql_syntax(self):
        """
        Requirement 3a: Support MySQL syntax
        Verify INSERT statements work for MySQL
        """
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name", "active"],
            [[1, "Alice", True], [2, "Bob", False]],
            "mysql"
        )
        
        # Check basic INSERT structure
        assert "INSERT INTO test_table" in sql
        assert "(id, name, active)" in sql
        assert "VALUES" in sql
        
        # Check boolean handling
        assert "TRUE" in sql or "FALSE" in sql
    
    def test_requirement_3b_postgresql_syntax(self):
        """
        Requirement 3b: Support PostgreSQL syntax
        Verify INSERT statements work for PostgreSQL
        """
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name", "active"],
            [[1, "Alice", True], [2, "Bob", False]],
            "postgresql"
        )
        
        # Check basic INSERT structure (same as MySQL for INSERT)
        assert "INSERT INTO test_table" in sql
        assert "(id, name, active)" in sql
        assert "VALUES" in sql
        
        # Check boolean handling
        assert "TRUE" in sql or "FALSE" in sql
    
    def test_requirement_4_large_dataset_optimization(self):
        """
        Requirement 4: Optimize large data SQL output
        Verify that large datasets are handled efficiently with batching
        """
        # Create a large dataset (2000 rows)
        data_rows = [[i, f"Name{i}", f"email{i}@example.com"] for i in range(2000)]
        
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name", "email"],
            data_rows,
            "mysql",
            batch_size=500
        )
        
        # Should have 4 INSERT statements (500 + 500 + 500 + 500)
        insert_count = sql.count("INSERT INTO test_table")
        assert insert_count == 4, f"Expected 4 INSERT statements for 2000 rows, got {insert_count}"
        
        # Verify SQL is not empty and contains expected data
        assert len(sql) > 0
        assert "Name0" in sql  # First row
        assert "Name1999" in sql  # Last row
    
    def test_comprehensive_data_types(self):
        """
        Comprehensive test: Verify all data types are handled correctly
        """
        from datetime import date, datetime
        
        data_rows = [
            [1, "Alice", 25, 1.75, True, date(2024, 1, 1), datetime(2024, 1, 1, 10, 30), None],
            [2, "Bob's", 30, 1.80, False, date(2024, 1, 2), datetime(2024, 1, 2, 14, 45), "test"],
        ]
        
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name", "age", "height", "active", "birth_date", "created_at", "notes"],
            data_rows,
            "mysql"
        )
        
        # Verify all data types are formatted correctly
        assert "(1, 'Alice', 25, 1.75, TRUE, '2024-01-01', '2024-01-01 10:30:00', NULL)" in sql
        assert "(2, 'Bob''s', 30, 1.8, FALSE, '2024-01-02', '2024-01-02 14:45:00', 'test')" in sql
    
    def test_edge_case_empty_strings(self):
        """
        Edge case: Handle empty strings correctly
        """
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name"],
            [[1, ""], [2, "   "]],
            "mysql"
        )
        
        assert "(1, '')" in sql
        assert "(2, '   ')" in sql
    
    def test_edge_case_special_characters(self):
        """
        Edge case: Handle special characters in strings
        """
        data_rows = [
            ["Line1\nLine2"],  # Newline
            ["Tab\there"],  # Tab
            ["Quote's and \"double\""],  # Mixed quotes
        ]
        
        sql = _generate_insert_statements(
            "test_table",
            ["text"],
            data_rows,
            "mysql"
        )
        
        # Single quotes should be escaped
        assert "'Quote''s and \"double\"'" in sql
    
    def test_edge_case_row_length_mismatch(self):
        """
        Edge case: Handle rows with different lengths than field names
        """
        # Row shorter than field names
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name", "age"],
            [[1, "Alice"]],  # Missing age
            "mysql"
        )
        
        # Should pad with NULL
        assert "(1, 'Alice', NULL)" in sql
        
        # Row longer than field names
        sql = _generate_insert_statements(
            "test_table",
            ["id", "name"],
            [[1, "Alice", 25, "extra"]],  # Extra values
            "mysql"
        )
        
        # Should truncate to field count
        assert "(1, 'Alice')" in sql
        assert "25" not in sql or sql.count("25") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
