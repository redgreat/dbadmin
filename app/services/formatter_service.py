"""
SQL格式化服务 - 格式化SQL语句以提高可读性
"""
import sqlparse
from typing import Literal, Optional


def format_sql(
    sql: str,
    keyword_case: Literal["upper", "lower", "capitalize"] = "upper",
    indent_width: int = 2,
    reindent: bool = True
) -> str:
    """
    使用sqlparse库格式化SQL语句，支持自定义选项
    
    参数:
        sql: 原始SQL语句
        keyword_case: 关键字大小写风格 - 'upper', 'lower', 或 'capitalize'
        indent_width: 缩进空格数（默认: 2）
        reindent: 是否重新缩进SQL（默认: True）
    
    返回:
        格式化后的SQL语句
    """
    if not sql or not sql.strip():
        return sql
    
    # 验证indent_width
    if indent_width < 0 or indent_width > 8:
        indent_width = 2  # 如果无效则默认为2
    
    # sqlparse要求indent_width为正数，所以特殊处理0的情况
    if indent_width == 0:
        # 当indent_width为0时不重新缩进
        formatted = sqlparse.format(
            sql,
            reindent=False,
            keyword_case=keyword_case,
            wrap_after=80
        )
    else:
        # 使用sqlparse格式化SQL
        formatted = sqlparse.format(
            sql,
            reindent=reindent,
            keyword_case=keyword_case,
            indent_width=indent_width,
            wrap_after=80
        )
    
    return formatted
