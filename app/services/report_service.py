from typing import Tuple, Optional, List
from app.models.report import ReportConfig, ReportGeneration
from app.models.conn import DBConnection
from app.log import logger


class ReportService:
    """报表配置服务"""

    @staticmethod
    async def create_config(
        system_name: str,
        report_name: str,
        sql_statement: str,
        db_connection_id: int,
        maintainer: str
    ) -> ReportConfig:
        """
        创建报表配置
        """
        # 验证SQL安全性
        is_valid, message = ReportService.validate_sql(sql_statement)
        if not is_valid:
            raise ValueError(message)

        # 验证数据库连接是否存在
        db_conn = await DBConnection.get_or_none(id=db_connection_id)
        if not db_conn:
            raise ValueError("数据库连接不存在")

        # 创建报表配置
        config = await ReportConfig.create(
            system_name=system_name,
            report_name=report_name,
            sql_statement=sql_statement,
            db_connection_id=db_connection_id,
            maintainer=maintainer
        )
        logger.info(f"创建报表配置成功: {config.id} - {config.report_name}")
        return config

    @staticmethod
    async def update_config(
        config_id: int,
        user: str,
        is_admin: bool,
        **update_data
    ) -> ReportConfig:
        """
        更新报表配置
        """
        config = await ReportConfig.get_or_none(id=config_id)
        if not config:
            raise ValueError("报表配置不存在")

        # 权限验证
        if not ReportService.check_permission(config, user, is_admin, "edit"):
            raise PermissionError("无权限编辑此报表配置")

        # 如果更新SQL，需要验证安全性
        if "sql_statement" in update_data:
            is_valid, message = ReportService.validate_sql(update_data["sql_statement"])
            if not is_valid:
                raise ValueError(message)

        # 更新字段
        for field, value in update_data.items():
            if value is not None and hasattr(config, field):
                setattr(config, field, value)

        await config.save()
        logger.info(f"更新报表配置成功: {config.id}")
        return config

    @staticmethod
    async def delete_config(config_id: int, user: str, is_admin: bool) -> bool:
        """
        删除报表配置（软删除）
        """
        config = await ReportConfig.get_or_none(id=config_id)
        if not config:
            raise ValueError("报表配置不存在")

        # 权限验证
        if not ReportService.check_permission(config, user, is_admin, "delete"):
            raise PermissionError("无权限删除此报表配置")

        # 执行软删除
        await config.soft_delete()
        logger.info(f"删除报表配置成功: {config.id}")
        return True

    @staticmethod
    async def get_config_list(
        page: int = 1,
        page_size: int = 10,
        system_name: Optional[str] = None,
        report_name: Optional[str] = None
    ) -> Tuple[List[ReportConfig], int]:
        """
        获取报表配置列表
        """
        query = ReportConfig.filter_active()

        # 搜索条件
        if system_name:
            query = query.filter(system_name__icontains=system_name)
        if report_name:
            query = query.filter(report_name__icontains=report_name)

        # 总数
        total = await query.count()

        # 分页
        items = await query.offset((page - 1) * page_size).limit(page_size).all()

        return items, total

    @staticmethod
    def check_permission(
        config: ReportConfig,
        user: str,
        is_admin: bool,
        action: str
    ) -> bool:
        """
        检查权限
        :param config: 报表配置对象
        :param user: 当前用户
        :param is_admin: 是否为管理员
        :param action: 操作类型 (edit, delete)
        :return: 是否有权限
        """
        # 管理员拥有所有权限
        if is_admin:
            return True

        # 普通用户只能操作自己维护的报表
        return config.maintainer == user

    @staticmethod
    def validate_sql(sql_statement: str) -> Tuple[bool, str]:
        """
        验证SQL安全性
        :param sql_statement: SQL语句
        :return: (是否有效, 错误消息)
        """
        # 禁止的危险关键字
        forbidden_keywords = [
            "DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT",
            "ALTER", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
        ]

        # 转换为大写进行匹配
        sql_upper = sql_statement.upper()

        # 检查是否包含危险关键字
        for keyword in forbidden_keywords:
            # 使用单词边界匹配，避免误判
            if f" {keyword} " in sql_upper or sql_upper.startswith(f"{keyword} "):
                return False, f"SQL语句包含禁止的关键字: {keyword}"

        # 检查是否为SELECT语句
        if not sql_upper.strip().startswith("SELECT"):
            return False, "只允许执行SELECT查询语句"

        return True, ""

    @staticmethod
    async def get_system_name_options() -> List[str]:
        """
        获取系统名称选项列表
        """
        # 后台代码写死，后续改为从字典表获取
        return [
            "仓储中心",
            "订单中心",
            "SIM卡中心",
            "壹好车服"
        ]
