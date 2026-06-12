from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Literal
import asyncio
import uuid
from typing import Optional

from app.schemas.base import Success
from app.services.excelimp_service import generate_sql, submit_and_generate, get_progress
from app.services.formatter_service import format_sql
from app.models.admin import User
from app.utils.audit_log import create_operation_audit_log
from app.core.dependency import DependAuth
from app.controllers.conn import conn_controller
from app.services.conn_permission_service import ensure_conn_access

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
async def submit_excel_sql(
    file: UploadFile = File(...),
    target_conn_id: Optional[int] = Form(None),
    db_type: str = Form("mysql"),
    current_user: User = DependAuth,
):
    """
    异步上传Excel文件并生成SQL，返回任务标识
    
    参数:
        file: Excel文件（.xlsx或.xls）
        target_conn_id: 目标连接ID（连接管理中的连接，可选）
    
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

        # 配置连接时由连接决定db_type；未配置时使用默认mysql生成SQL
        if target_conn_id:
            await ensure_conn_access(current_user, target_conn_id, "使用该目标连接")
            conn_info = await conn_controller.get_decrypted_connection(target_conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail="目标连接不存在或不可用")
            db_type = conn_info.get("db_type")
            if db_type not in ("mysql", "postgresql"):
                raise HTTPException(status_code=400, detail=f"目标连接类型不支持: {db_type}")
        elif db_type not in ("mysql", "postgresql"):
            db_type = "mysql"
        
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
            await create_operation_audit_log(
                user_id=current_user.id,
                username=current_user.username,
                module="日常工具",
                summary=f"Excel临时表SQL生成: {file.filename} ({file_key})",
                method="POST",
                path="/api/v1/tool/excelimp/submit",
                status=200,
                skip_request_body=True,
                response_body={"file_key": file_key},
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


@router.post("/passwordgen/save", summary="保存密码生成记录")
async def save_password_history(
    passwords: str = Form(...),
    length: int = Form(...),
    char_types: str = Form(""),
    exclude_chars: str = Form(""),
    count: int = Form(1),
    current_user: User = DependAuth,
):
    from app.models.password import PasswordHistory
    import json

    try:
        password_list = json.loads(passwords)
        if not isinstance(password_list, list):
            raise HTTPException(status_code=400, detail="passwords must be a JSON array")
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="passwords must be a valid JSON array")

    try:
        char_types_list = json.loads(char_types) if char_types else []
    except (json.JSONDecodeError, TypeError):
        char_types_list = []

    records = []
    for pwd in password_list:
        record = await PasswordHistory.create(
            password=pwd,
            length=length,
            char_types=char_types_list,
            exclude_chars=exclude_chars,
            count=count,
        )
        records.append(record)

    return Success(data={"count": len(records)}, msg=f"已保存 {len(records)} 条密码记录")


@router.get("/passwordgen/history", summary="获取密码生成历史")
async def get_password_history(
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页数量"),
):
    from app.models.password import PasswordHistory
    from app.schemas.base import SuccessExtra

    total = await PasswordHistory.all().count()
    records = await PasswordHistory.all().order_by("-created_at").offset((page - 1) * page_size).limit(page_size)
    data = [await r.to_dict() for r in records]

    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.delete("/passwordgen/history", summary="删除密码生成历史")
async def delete_password_history(
    ids: str = Query("", description="要删除的记录ID，逗号分隔。为空则清空全部"),
    current_user: User = DependAuth,
):
    from app.models.password import PasswordHistory

    if ids.strip():
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            await PasswordHistory.filter(id__in=id_list).delete()
            return Success(msg=f"已删除 {len(id_list)} 条记录")
        return Success(msg="没有需要删除的记录")
    else:
        cnt = await PasswordHistory.all().count()
        await PasswordHistory.all().delete()
        return Success(msg=f"已清空全部 {cnt} 条历史记录")
