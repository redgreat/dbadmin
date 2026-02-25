"""
Tests for field name generation - Task 2.2
Tests the _generate_field_names and _convert_to_sql_identifier functions
"""
import sys
from pathlib import Path

# Add parent directory to path to import from app.services
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.excelimp_service import _generate_field_names, _convert_to_sql_identifier


class TestConvertToSqlIdentifier:
    """Tests for _convert_to_sql_identifier helper function"""
    
    def test_basic_english(self):
        """Test basic English text remains unchanged"""
        assert _convert_to_sql_identifier("Name") == "Name"
        assert _convert_to_sql_identifier("age") == "age"
        assert _convert_to_sql_identifier("UserID") == "UserID"
    
    def test_spaces_to_underscores(self):
        """Test spaces are converted to underscores"""
        assert _convert_to_sql_identifier("First Name") == "First_Name"
        assert _convert_to_sql_identifier("User ID") == "User_ID"
    
    def test_hyphens_to_underscores(self):
        """Test hyphens are converted to underscores"""
        assert _convert_to_sql_identifier("user-id") == "user_id"
        assert _convert_to_sql_identifier("first-name") == "first_name"
    
    def test_chinese_to_pinyin(self):
        """Test Chinese characters are converted to pinyin"""
        assert _convert_to_sql_identifier("姓名") == "xingming"
        assert _convert_to_sql_identifier("年龄") == "nianling"
        assert _convert_to_sql_identifier("城市") == "chengshi"
    
    def test_mixed_chinese_english(self):
        """Test mixed Chinese and English text"""
        result = _convert_to_sql_identifier("用户Name")
        assert "yonghu" in result.lower()
        assert "name" in result.lower()
    
    def test_special_characters_removed(self):
        """Test special characters are removed"""
        assert _convert_to_sql_identifier("Name!") == "Name"
        assert _convert_to_sql_identifier("Age@") == "Age"
        assert _convert_to_sql_identifier("City#") == "City"
    
    def test_starts_with_number(self):
        """Test identifiers starting with numbers get col_ prefix"""
        assert _convert_to_sql_identifier("123abc") == "col_123abc"
        assert _convert_to_sql_identifier("1st_place") == "col_1st_place"
    
    def test_empty_string(self):
        """Test empty string returns empty"""
        assert _convert_to_sql_identifier("") == ""
        assert _convert_to_sql_identifier("   ") == ""
    
    def test_only_special_chars(self):
        """Test string with only special characters"""
        assert _convert_to_sql_identifier("!!!") == ""
        assert _convert_to_sql_identifier("@#$") == ""


class TestGenerateFieldNames:
    """Tests for _generate_field_names function - Task 2.2"""
    
    def test_basic_english_names(self):
        """Test basic English field names remain unchanged"""
        columns = ["Name", "Age", "City"]
        field_names = _generate_field_names(columns)
        
        assert field_names == ["Name", "Age", "City"]
    
    def test_spaces_converted(self):
        """Test field names with spaces are converted to underscores"""
        columns = ["First Name", "Last Name", "Email Address"]
        field_names = _generate_field_names(columns)
        
        assert field_names == ["First_Name", "Last_Name", "Email_Address"]
    
    def test_chinese_to_pinyin(self):
        """Test Chinese column names are converted to pinyin"""
        columns = ["姓名", "年龄", "城市"]
        field_names = _generate_field_names(columns)
        
        assert field_names == ["xingming", "nianling", "chengshi"]
    
    def test_mixed_chinese_english(self):
        """Test mixed Chinese and English column names"""
        columns = ["用户ID", "姓名Name", "Age年龄"]
        field_names = _generate_field_names(columns)
        
        # Should contain both pinyin and English parts
        assert len(field_names) == 3
        assert all(name for name in field_names)  # All non-empty
    
    def test_duplicate_names(self):
        """Test handling of duplicate field names with numeric suffixes"""
        columns = ["Name", "Name", "Name"]
        field_names = _generate_field_names(columns)
        
        assert len(field_names) == 3
        assert len(set(field_names)) == 3  # All unique
        assert field_names[0] == "Name"
        assert field_names[1] == "Name_1"
        assert field_names[2] == "Name_2"
    
    def test_duplicate_chinese_names(self):
        """Test handling of duplicate Chinese field names"""
        columns = ["姓名", "姓名", "姓名"]
        field_names = _generate_field_names(columns)
        
        assert len(field_names) == 3
        assert len(set(field_names)) == 3  # All unique
        assert field_names[0] == "xingming"
        assert field_names[1] == "xingming_1"
        assert field_names[2] == "xingming_2"
    
    def test_special_characters(self):
        """Test field names with special characters"""
        columns = ["Name!", "Age@", "City#"]
        field_names = _generate_field_names(columns)
        
        # Special chars should be removed
        assert field_names == ["Name", "Age", "City"]
    
    def test_empty_column_names(self):
        """Test handling of empty column names"""
        columns = ["Name", "", "Age"]
        field_names = _generate_field_names(columns)
        
        assert field_names[0] == "Name"
        assert field_names[1] == "column_2"  # Default name for empty
        assert field_names[2] == "Age"
    
    def test_whitespace_only_names(self):
        """Test handling of whitespace-only column names"""
        columns = ["Name", "   ", "Age"]
        field_names = _generate_field_names(columns)
        
        assert field_names[0] == "Name"
        assert field_names[1] == "column_2"  # Default name for whitespace
        assert field_names[2] == "Age"
    
    def test_sql_identifier_compliance(self):
        """Test that all generated names are valid SQL identifiers"""
        columns = ["姓名", "First Name", "Age!", "123", "用户-ID"]
        field_names = _generate_field_names(columns)
        
        for name in field_names:
            # Must start with letter or underscore
            assert name[0].isalpha() or name[0] == '_'
            # Must contain only alphanumeric and underscores
            assert all(c.isalnum() or c == '_' for c in name)
    
    def test_complex_chinese_names(self):
        """Test complex Chinese column names"""
        columns = ["用户姓名", "出生日期", "联系电话", "电子邮箱"]
        field_names = _generate_field_names(columns)
        
        # Should all be converted to pinyin
        assert len(field_names) == 4
        assert all(name.isascii() for name in field_names)
        assert all(name[0].isalpha() or name[0] == '_' for name in field_names)
    
    def test_numbers_in_names(self):
        """Test column names starting with numbers"""
        columns = ["123Name", "456Age", "789City"]
        field_names = _generate_field_names(columns)
        
        # Should all start with col_ prefix
        assert all(name.startswith("col_") for name in field_names)
    
    def test_underscores_preserved(self):
        """Test that underscores in column names are preserved"""
        columns = ["first_name", "last_name", "user_id"]
        field_names = _generate_field_names(columns)
        
        assert field_names == ["first_name", "last_name", "user_id"]
    
    def test_real_world_example(self):
        """Test a real-world example with mixed column types"""
        columns = [
            "员工编号",      # Employee ID
            "姓名",          # Name
            "部门",          # Department
            "入职日期",      # Join Date
            "Salary",        # English
            "备注 Notes"     # Mixed
        ]
        field_names = _generate_field_names(columns)
        
        # All should be valid SQL identifiers
        assert len(field_names) == 6
        assert all(name for name in field_names)  # All non-empty
        assert len(set(field_names)) == 6  # All unique
        
        # Check specific conversions
        assert field_names[0] == "yuangongbianhao"  # 员工编号
        assert field_names[1] == "xingming"  # 姓名
        assert field_names[2] == "bumen"  # 部门
        assert field_names[3] == "ruzhiriqi"  # 入职日期
        assert field_names[4] == "Salary"  # English unchanged
        # field_names[5] should contain both pinyin and English


if __name__ == "__main__":
    import pytest
    
    # Run tests
    exit_code = pytest.main([__file__, "-v"])
    sys.exit(exit_code)
