"""
Excel导入服务 - 从Excel文件生成SQL语句
"""
from io import BytesIO
from datetime import datetime, date
from typing import List, Tuple, Any, Literal
import openpyxl
from openpyxl.worksheet.worksheet import Worksheet
from pypinyin import lazy_pinyin, Style


def generate_sql(content: bytes, filename: str, db_type: Literal["mysql", "postgresql"]) -> str:
    """
    从Excel文件内容生成SQL语句
    
    参数:
        content: Excel文件内容（字节）
        filename: 原始文件名
        db_type: 数据库类型（mysql或postgresql）
    
    返回:
        生成的SQL语句字符串
    """
    # 解析Excel文件
    workbook = openpyxl.load_workbook(BytesIO(content), data_only=True)
    sheet = workbook.active
    
    if not sheet:
        raise ValueError("Excel文件中没有找到工作表")
    
    # 提取列名和数据行
    columns, data_rows = _parse_sheet(sheet)
    
    if not columns:
        raise ValueError("Excel文件中没有找到列名（第一行）")
    
    if not data_rows:
        raise ValueError("Excel文件中没有找到数据行")
    
    # 生成英文字段名
    field_names = _generate_field_names(columns)
    
    # 推断数据类型
    field_types = _infer_field_types(data_rows, db_type)
    
    # 生成带时间戳的表名
    table_name = _generate_table_name()
    
    # 生成CREATE TABLE语句
    create_table_sql = _generate_create_table(table_name, field_names, field_types, db_type)
    
    # 生成INSERT语句
    insert_sql = _generate_insert_statements(table_name, field_names, data_rows, db_type)
    
    # 合并所有SQL语句
    return f"{create_table_sql}\n\n{insert_sql}"


def _parse_sheet(sheet: Worksheet) -> Tuple[List[str], List[List[Any]]]:
    """
    解析Excel工作表，提取列名和数据行
    
    返回:
        元组 (列名列表, 数据行列表)
    """
    rows = list(sheet.iter_rows(values_only=True))
    
    if not rows:
        return [], []
    
    # 第一行是列名
    columns = [str(cell) if cell is not None else f"column_{i+1}" for i, cell in enumerate(rows[0])]
    
    # 其余行是数据
    data_rows = []
    for row in rows[1:]:
        # 跳过空行
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        data_rows.append(list(row))
    
    return columns, data_rows


def _generate_field_names(columns: List[str]) -> List[str]:
    """
    从列名生成有效的SQL字段名
    将中文字符转换为拼音，确保符合SQL标识符规范
    通过添加数字后缀处理重复字段名
    """
    field_names = []
    seen = {}
    
    for col in columns:
        col = col.strip()
        
        # 将中文字符转换为拼音
        field_name = _convert_to_sql_identifier(col)
        
        # 如果转换后为空，使用默认名称
        if not field_name:
            field_name = f"column_{len(field_names) + 1}"
        
        # 通过添加数字后缀处理重复字段名
        original_name = field_name
        counter = 1
        while field_name in seen:
            field_name = f"{original_name}_{counter}"
            counter += 1
        
        seen[field_name] = True
        field_names.append(field_name)
    
    return field_names


def _convert_to_sql_identifier(text: str) -> str:
    """
    将文本转换为有效的SQL标识符
    - 将中文字符转换为拼音
    - 将空格和连字符替换为下划线
    - 移除或替换特殊字符
    - 确保以字母或下划线开头
    """
    # 先去除空白字符
    text = text.strip()
    
    if not text:
        return ""
    
    result = []
    
    for char in text:
        if char.isascii():
            # ASCII字符 - 直接处理
            if char.isalnum():
                result.append(char)
            elif char in (' ', '-'):
                result.append('_')
            elif char == '_':
                result.append('_')
            # 跳过其他特殊字符
        else:
            # 非ASCII字符（可能是中文）- 转换为拼音
            pinyin_list = lazy_pinyin(char, style=Style.NORMAL)
            if pinyin_list:
                result.append(pinyin_list[0])
    
    field_name = ''.join(result)
    
    # 确保以字母或下划线开头
    if field_name and not (field_name[0].isalpha() or field_name[0] == '_'):
        field_name = f"col_{field_name}"
    
    return field_name


def _infer_field_types(data_rows: List[List[Any]], db_type: Literal["mysql", "postgresql"]) -> List[str]:
    """
    根据数据推断每列的SQL数据类型
    """
    if not data_rows:
        return []
    
    num_columns = len(data_rows[0])
    field_types = []
    
    for col_idx in range(num_columns):
        # 收集该列的所有值
        values = [row[col_idx] if col_idx < len(row) else None for row in data_rows]
        
        # 推断类型
        field_type = _infer_column_type(values, db_type)
        field_types.append(field_type)
    
    return field_types


def _infer_column_type(values: List[Any], db_type: Literal["mysql", "postgresql"]) -> str:
    """
    根据列的值推断SQL类型
    支持: INT, BIGINT, DECIMAL, VARCHAR, TEXT, DATE, DATETIME
    通过选择最宽松的类型来处理混合类型
    """
    # 过滤掉None值
    non_null_values = [v for v in values if v is not None]
    
    if not non_null_values:
        return "VARCHAR(255)"
    
    # 跟踪类型类别
    has_int = False
    has_float = False
    has_date = False
    has_datetime = False
    has_string = False
    has_bool = False
    
    max_int_value = 0
    max_str_length = 0
    
    for val in non_null_values:
        if isinstance(val, bool):
            has_bool = True
        elif isinstance(val, datetime):
            has_datetime = True
        elif isinstance(val, date):
            has_date = True
        elif isinstance(val, int):
            has_int = True
            max_int_value = max(max_int_value, abs(val))
        elif isinstance(val, float):
            has_float = True
        elif isinstance(val, str):
            # 首先尝试将字符串解析为日期/时间
            date_val = _try_parse_date(val)
            if date_val:
                if isinstance(date_val, datetime):
                    has_datetime = True
                else:
                    has_date = True
            else:
                # 不是日期字符串，作为普通字符串处理
                has_string = True
                max_str_length = max(max_str_length, len(val))
        else:
            # 未知类型，作为字符串处理
            has_string = True
            max_str_length = max(max_str_length, len(str(val)))
    
    # 根据发现的类型确定最终类型
    # 优先级: datetime > date > decimal > bigint > int > varchar/text
    
    if has_datetime:
        # 如果有任何datetime，使用DATETIME（对日期/时间数据最宽松）
        return "DATETIME" if db_type == "mysql" else "TIMESTAMP"
    
    if has_date and not has_string:
        # 纯日期列（没有非日期字符串）
        return "DATE"
    
    if has_string or has_bool:
        # 如果有字符串或布尔值与数字混合，使用字符串类型
        if has_int or has_float or has_date or has_datetime:
            # 混合类型 - 使用字符串
            max_str_length = max(max_str_length, 50)  # 确保合理的最小值
        
        if max_str_length == 0:
            max_str_length = 255
        elif max_str_length < 255:
            max_str_length = min(max_str_length * 2, 255)  # 添加缓冲
        
        if max_str_length > 1000:
            return "TEXT"
        else:
            return f"VARCHAR({max_str_length})"
    
    # 仅数字类型
    if has_float:
        # 如果有任何浮点数，使用DECIMAL（对数字数据最宽松）
        return "DECIMAL(18,2)"
    
    if has_int:
        # 纯整数列
        if max_int_value < 2147483647:  # 2^31 - 1
            return "INT"
        else:
            return "BIGINT"
    
    # 默认回退
    return "VARCHAR(255)"


def _try_parse_date(value: str) -> Any:
    """
    尝试将字符串解析为日期或日期时间
    如果解析失败，返回datetime、date或None
    """
    if not value or not isinstance(value, str):
        return None
    
    value = value.strip()
    
    # 常见的日期/时间格式
    formats = [
        # 日期时间格式
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
        # 日期格式
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            # 检查是否有时间部分
            if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
                # 检查原始字符串是否有时间部分
                if ":" in value:
                    return parsed  # datetime
                else:
                    return parsed.date()  # 仅日期
            else:
                return parsed  # datetime
        except ValueError:
            continue
    
    return None


def _generate_table_name() -> str:
    """
    生成带时间戳的临时表名
    格式: tmp_YYYYMMDD_HHMMSS
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"tmp_{timestamp}"


def _generate_create_table(
    table_name: str,
    field_names: List[str],
    field_types: List[str],
    db_type: Literal["mysql", "postgresql"]
) -> str:
    """
    生成CREATE TABLE语句
    """
    field_definitions = []
    for name, type_ in zip(field_names, field_types):
        field_definitions.append(f"  {name} {type_}")
    
    fields_sql = ",\n".join(field_definitions)
    
    if db_type == "mysql":
        return f"CREATE TABLE {table_name} (\n{fields_sql}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    else:  # postgresql
        return f"CREATE TABLE {table_name} (\n{fields_sql}\n);"


def _generate_insert_statements(
    table_name: str,
    field_names: List[str],
    data_rows: List[List[Any]],
    db_type: Literal["mysql", "postgresql"],
    batch_size: int = 500
) -> str:
    """
    批量生成INSERT语句
    """
    if not data_rows:
        return ""
    
    insert_statements = []
    fields_str = ", ".join(field_names)
    
    for i in range(0, len(data_rows), batch_size):
        batch = data_rows[i:i + batch_size]
        values_list = []
        
        for row in batch:
            # 确保行的长度与字段名相同
            row_values = row + [None] * (len(field_names) - len(row))
            row_values = row_values[:len(field_names)]
            
            # 格式化值
            formatted_values = []
            for val in row_values:
                formatted_values.append(_format_value(val))
            
            values_list.append(f"({', '.join(formatted_values)})")
        
        values_str = ",\n  ".join(values_list)
        insert_sql = f"INSERT INTO {table_name} ({fields_str})\nVALUES\n  {values_str};"
        insert_statements.append(insert_sql)
    
    return "\n\n".join(insert_statements)


def _format_value(val: Any) -> str:
    """
    格式化SQL INSERT语句的值
    处理: None, bool, int, float, date, datetime和字符串
    """
    if val is None:
        return "NULL"
    elif isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    elif isinstance(val, datetime):
        # 格式化datetime为 'YYYY-MM-DD HH:MM:SS'
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    elif isinstance(val, date):
        # 格式化date为 'YYYY-MM-DD'
        return f"'{val.strftime('%Y-%m-%d')}'"
    elif isinstance(val, (int, float)):
        return str(val)
    else:
        # 字符串值 - 转义单引号
        str_val = str(val).replace("'", "''")
        return f"'{str_val}'"
