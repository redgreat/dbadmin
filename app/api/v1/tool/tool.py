from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Literal

from app.services.excelimp_service import generate_sql
from app.services.formatter_service import format_sql

router = APIRouter()


@router.post("/excelimp/generate")
async def generate_excel_sql(
    file: UploadFile = File(...),
    db_type: Literal["mysql", "postgresql"] = Form(...)
):
    """
    从Excel文件生成用于创建临时表和插入数据的SQL语句
    
    参数:
        file: Excel文件（.xlsx或.xls）
        db_type: 数据库类型（mysql或postgresql）
    
    返回:
        生成的SQL语句字符串
    """
    # 验证文件扩展名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 和 .xls 格式的Excel文件")
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 验证文件大小（最大10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=400, 
                detail=f"文件大小超过限制（最大10MB），当前文件大小: {len(content) / 1024 / 1024:.2f}MB"
            )
        
        # 验证文件不为空
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 生成SQL
        sql_result = generate_sql(content, file.filename, db_type)
        
        return {"sql": sql_result}
    
    except HTTPException:
        # 原样重新抛出HTTP异常
        raise
    except ValueError as e:
        # 使用友好的消息处理Excel解析错误
        error_msg = str(e)
        if "没有找到工作表" in error_msg:
            raise HTTPException(status_code=400, detail="Excel文件格式错误：无法读取工作表")
        elif "没有找到列名" in error_msg:
            raise HTTPException(status_code=400, detail="Excel文件格式错误：第一行应包含列名")
        elif "没有找到数据行" in error_msg:
            raise HTTPException(status_code=400, detail="Excel文件格式错误：文件中没有数据行")
        else:
            raise HTTPException(status_code=400, detail=f"Excel文件解析错误: {error_msg}")
    except Exception as e:
        # 处理其他意外错误
        raise HTTPException(status_code=500, detail=f"处理Excel文件时出错: {str(e)}")


@router.post("/formatter/format")
async def format_sql_statement(
    sql: str = Form(...),
    keyword_case: str = Form("upper"),
    indent_width: int = Form(2)
):
    """
    格式化SQL语句以提高可读性，支持自定义选项
    
    参数:
        sql: 原始SQL语句
        keyword_case: 关键字大小写风格 - 'upper', 'lower', 或 'capitalize'（默认: 'upper'）
        indent_width: 缩进空格数（默认: 2，范围: 0-8）
    
    返回:
        格式化后的SQL语句
    """
    # 验证keyword_case
    valid_cases = ["upper", "lower", "capitalize"]
    if keyword_case not in valid_cases:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的关键字大小写选项。有效值: {', '.join(valid_cases)}"
        )
    
    # 验证indent_width
    if indent_width < 0 or indent_width > 8:
        raise HTTPException(
            status_code=400, 
            detail="缩进宽度必须在0到8之间"
        )
    
    try:
        formatted_sql = format_sql(sql, keyword_case=keyword_case, indent_width=indent_width)
        return {"sql": formatted_sql}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"格式化SQL时出错: {str(e)}")
