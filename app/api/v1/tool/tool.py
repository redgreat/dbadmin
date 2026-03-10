from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Request
from typing import Literal
import asyncio
import uuid

from app.schemas.base import Success
from app.services.excelimp_service import generate_sql, submit_and_generate, get_progress
from app.services.formatter_service import format_sql
from app.models.admin import AuditLog, User
from app.core.dependency import AuthControl

router = APIRouter(tags=["日常工具"])


@router.post("/excelimp/generate", summary="生成Excel临时表SQL")
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
        max_size = 10 * 1024 * 1024  # 100MB
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

        return Success(data={"sql": sql_result})
    
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


@router.post("/excelimp/submit", summary="异步生成Excel临时表SQL")
async def submit_excel_sql(req: Request, file: UploadFile = File(...), db_type: str = Form(...)):
    """
    异步上传Excel文件并生成SQL，返回任务标识
    
    参数:
        file: Excel文件（.xlsx或.xls）
        db_type: 数据库类型（mysql或postgresql）
    
    返回:
        任务标识file_key，可用于查询进度和下载结果
    """
    # 验证文件扩展名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 和 .xls 格式的Excel文件")
    
    try:
        # 读取文件内容
        content = await file.read()
        
        # 验证文件大小（最大100MB）
        max_size = 100 * 1024 * 1024  # 100MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制（最大100MB），当前文件大小: {len(content) / 1024 / 1024:.2f}MB"
            )
        
        # 验证文件不为空
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="文件内容为空")
        
        # 生成任务标识
        file_key = str(uuid.uuid4())
        
        # 启动后台任务
        async def _runner():
            try:
                await submit_and_generate(
                    content, file.filename, db_type, stamp=file_key
                )
            except Exception:
                return
        
        asyncio.create_task(_runner())
        
        # 记录审计日志
        try:
            token = req.headers.get("token")
            user_obj: User = None
            if token:
                user_obj = await AuthControl.is_authed(token)
            user_id = user_obj.id if user_obj else 0
            username = user_obj.username if user_obj else ""
        except Exception:
            user_id = 0
            username = ""
        
        try:
            await AuditLog.create(
                user_id=user_id,
                username=username,
                module="日常工具",
                summary=f"Excel临时表SQL生成: {file.filename} ({file_key})",
                method="POST",
                path="/api/v1/tool/excelimp/submit",
                status=200,
                response_time=0,
            )
        except Exception:
            pass
        
        return Success(data={"file_key": file_key}, msg="任务已提交，正在后台处理")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交处理失败: {str(e)}")


@router.get("/excelimp/progress", summary="查询Excel临时表SQL生成进度")
async def get_excel_progress(file_key: str = Query(..., description="任务标识")):
    """
    查询SQL生成任务进度
    
    参数:
        file_key: 任务标识
    
    返回:
        任务进度信息，包括阶段、状态、SQL结果等
    """
    data = get_progress(file_key)
    return Success(data=data)


@router.post("/formatter/format", summary="格式化SQL语句")
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
        return Success(data={"sql": formatted_sql})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"格式化SQL时出错: {str(e)}")
