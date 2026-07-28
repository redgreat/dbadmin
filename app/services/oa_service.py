from collections.abc import Sequence
from datetime import datetime
from typing import Any

import aiomysql

from app.models.conn import DBConnection
from app.services.db_pool import db_pool

OA_CONN_ALIAS = "OA_CONN"
FCC_CONN_ALIAS = "FCC_CONN"


class OAPositiveTimeService:
    """OA转正时间维护服务"""

    async def validate_positive_time(self, codes: Sequence[str]) -> dict[str, Any]:
        normalized_codes = self._normalize_codes(codes)
        if not normalized_codes:
            raise ValueError("人员工号不能为空")

        oa_conn_id = await self._get_conn_id(OA_CONN_ALIAS, "mysql")
        fcc_conn_id = await self._get_conn_id(FCC_CONN_ALIAS, "sqlserver")

        oa_rows, not_found_codes = await self._fetch_oa_positive_times(oa_conn_id, normalized_codes)
        fcc_rows = await self._fetch_fcc_positive_times(fcc_conn_id, normalized_codes)

        return {
            "codes": normalized_codes,
            "oa_conn_alias": OA_CONN_ALIAS,
            "fcc_conn_alias": FCC_CONN_ALIAS,
            "rows": self._merge_rows(normalized_codes, oa_rows, fcc_rows),
            "not_found_codes": not_found_codes,
        }

    async def update_positive_time(self, codes: Sequence[str], positive_time: datetime) -> dict[str, Any]:
        normalized_codes = self._normalize_codes(codes)
        if not normalized_codes:
            raise ValueError("人员工号不能为空")
        if not positive_time:
            raise ValueError("转正时间不能为空")

        oa_conn_id = await self._get_conn_id(OA_CONN_ALIAS, "mysql")
        fcc_conn_id = await self._get_conn_id(FCC_CONN_ALIAS, "sqlserver")

        oa_users = await self._fetch_oa_users(oa_conn_id, normalized_codes)
        user_ids = [row["Id"] for row in oa_users]
        found_codes = [row["Code"] for row in oa_users]
        not_found_codes = [code for code in normalized_codes if code not in set(found_codes)]

        if not user_ids:
            raise ValueError("未在OA库找到可修改的人员")

        mysql_time = positive_time.strftime("%Y-%m-%d %H:%M:%S")
        json_time = positive_time.strftime("%Y-%m-%dT%H:%M:%S")

        oa_affected = await self._update_oa_positive_time(oa_conn_id, user_ids, mysql_time, json_time)
        fcc_affected = await self._update_fcc_positive_time(fcc_conn_id, found_codes, mysql_time)
        validation = await self.validate_positive_time(normalized_codes)

        return {
            "updated_codes": found_codes,
            "not_found_codes": not_found_codes,
            "positive_time": mysql_time,
            "oa_affected": oa_affected,
            "fcc_affected": fcc_affected,
            "validation": validation,
        }

    async def validate_entry_time(self, codes: Sequence[str]) -> dict[str, Any]:
        normalized_codes = self._normalize_codes(codes)
        if not normalized_codes:
            raise ValueError("人员工号不能为空")

        oa_conn_id = await self._get_conn_id(OA_CONN_ALIAS, "mysql")
        fcc_conn_id = await self._get_conn_id(FCC_CONN_ALIAS, "sqlserver")

        oa_rows, not_found_codes = await self._fetch_oa_entry_times(oa_conn_id, normalized_codes)
        fcc_rows = await self._fetch_fcc_entry_times(fcc_conn_id, normalized_codes)

        return {
            "codes": normalized_codes,
            "oa_conn_alias": OA_CONN_ALIAS,
            "fcc_conn_alias": FCC_CONN_ALIAS,
            "rows": self._merge_rows(normalized_codes, oa_rows, fcc_rows),
            "not_found_codes": not_found_codes,
        }

    async def update_entry_time(self, codes: Sequence[str], entry_time: datetime) -> dict[str, Any]:
        normalized_codes = self._normalize_codes(codes)
        if not normalized_codes:
            raise ValueError("人员工号不能为空")
        if not entry_time:
            raise ValueError("入职时间不能为空")

        oa_conn_id = await self._get_conn_id(OA_CONN_ALIAS, "mysql")
        fcc_conn_id = await self._get_conn_id(FCC_CONN_ALIAS, "sqlserver")

        oa_users = await self._fetch_oa_users(oa_conn_id, normalized_codes)
        user_ids = [row["Id"] for row in oa_users]
        found_codes = [row["Code"] for row in oa_users]
        not_found_codes = [code for code in normalized_codes if code not in set(found_codes)]

        if not user_ids:
            raise ValueError("未在OA库找到可修改的人员")

        mysql_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")
        date_value = entry_time.strftime("%Y-%m-%d")

        oa_affected = await self._update_oa_entry_time(oa_conn_id, user_ids, found_codes, mysql_time, date_value)
        fcc_affected = await self._update_fcc_entry_time(fcc_conn_id, found_codes, mysql_time)
        validation = await self.validate_entry_time(normalized_codes)

        return {
            "updated_codes": found_codes,
            "not_found_codes": not_found_codes,
            "entry_time": mysql_time,
            "oa_affected": oa_affected,
            "fcc_affected": fcc_affected,
            "validation": validation,
        }

    def _normalize_codes(self, codes: Sequence[str]) -> list[str]:
        seen = set()
        result = []
        for code in codes:
            value = (code or "").strip()
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    async def _get_conn_id(self, alias: str, db_type: str) -> int:
        conn = await DBConnection.get_or_none(alias=alias, db_type=db_type)
        if not conn:
            raise ValueError(f"未找到数据库连接: {alias}")
        return conn.id

    def _mysql_in_clause(self, values: Sequence[Any]) -> str:
        return ",".join(["%s"] * len(values))

    def _sqlserver_in_clause(self, values: Sequence[Any]) -> str:
        return ",".join(["?"] * len(values))

    async def _fetch_oa_users(self, conn_id: int, codes: Sequence[str]) -> list[dict[str, Any]]:
        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("OA_CONN 必须是 MySQL 连接")

        placeholders = self._mysql_in_clause(codes)
        sql = (
            "SELECT Id, Code, PositiveTime "
            "FROM oa_hrcenter.membership_userbaseinfo "
            f"WHERE Code IN ({placeholders}) AND Deleted=0"
        )
        async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, tuple(codes))
            rows = await cur.fetchall()
        return list(rows or [])

    async def _fetch_oa_positive_times(self, conn_id: int, codes: Sequence[str]) -> tuple[list[dict[str, Any]], list[str]]:
        users = await self._fetch_oa_users(conn_id, codes)
        user_ids = [row["Id"] for row in users]
        found_codes = [row["Code"] for row in users]
        found_code_set = set(found_codes)
        not_found_codes = [code for code in codes if code not in found_code_set]
        if not user_ids:
            return [], not_found_codes

        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("OA_CONN 必须是 MySQL 连接")

        id_placeholders = self._mysql_in_clause(user_ids)
        queries = [
            (
                "check_userbaseinfo",
                "SELECT Id AS user_id, PositiveTime AS positive_time "
                "FROM oa_hrcenter.check_userbaseinfo "
                f"WHERE Id IN ({id_placeholders})",
            ),
            (
                "check_userinfobyday",
                "SELECT Id AS user_id, PositiveTime AS positive_time "
                "FROM oa_hrcenter.check_userinfobyday "
                f"WHERE Id IN ({id_placeholders})",
            ),
            (
                "membership_userbaseinfo",
                "SELECT Id AS user_id, PositiveTime AS positive_time "
                "FROM oa_hrcenter.membership_userbaseinfo "
                f"WHERE Id IN ({id_placeholders}) AND Deleted=0",
            ),
            (
                "membership_positiveconfirm",
                "SELECT UserBaseInfoId AS user_id, "
                "JSON_UNQUOTE(JSON_EXTRACT(PositiveJSON, '$.PositiveTime')) AS positive_time "
                "FROM membership_positiveconfirm "
                f"WHERE UserBaseInfoId IN ({id_placeholders})",
            ),
        ]

        code_by_id = {row["Id"]: row["Code"] for row in users}
        rows: list[dict[str, Any]] = []
        seen_tables_by_user_id: dict[str, set[str]] = {user_id: set() for user_id in user_ids}
        async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            for table_name, sql in queries:
                await cur.execute(sql, tuple(user_ids))
                for row in await cur.fetchall():
                    seen_tables_by_user_id.setdefault(row["user_id"], set()).add(table_name)
                    rows.append(
                        {
                            "source": "OA",
                            "table": table_name,
                            "code": code_by_id.get(row["user_id"]),
                            "user_id": row["user_id"],
                            "positive_time": self._format_value(row.get("positive_time")),
                        }
                    )
        for user_id in user_ids:
            if "membership_positiveconfirm" not in seen_tables_by_user_id.get(user_id, set()):
                rows.append(
                    {
                        "source": "OA",
                        "table": "membership_positiveconfirm",
                        "code": code_by_id.get(user_id),
                        "user_id": user_id,
                        "positive_time": None,
                    }
                )
        return rows, not_found_codes

    async def _fetch_fcc_positive_times(self, conn_id: int, codes: Sequence[str]) -> list[dict[str, Any]]:
        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("FCC_CONN 连接池不存在")

        placeholders = self._sqlserver_in_clause(codes)
        sql = (
            "SELECT Id, Code, PositiveTime "
            "FROM MemberShip_UserBaseInfo "
            f"WHERE Code IN ({placeholders}) AND Deleted=0"
        )
        rows: list[dict[str, Any]] = []
        async with pool.acquire() as conn, conn.cursor() as cur:
            await cur.execute(sql, tuple(codes))
            columns = [col[0] for col in cur.description]
            for row in await cur.fetchall():
                data = dict(zip(columns, row))
                rows.append(
                    {
                        "source": "FCC",
                        "table": "MemberShip_UserBaseInfo",
                        "code": data.get("Code"),
                        "user_id": self._format_value(data.get("Id")),
                        "positive_time": self._format_value(data.get("PositiveTime")),
                    }
                )
        return rows

    async def _fetch_oa_entry_times(self, conn_id: int, codes: Sequence[str]) -> tuple[list[dict[str, Any]], list[str]]:
        users = await self._fetch_oa_users(conn_id, codes)
        user_ids = [row["Id"] for row in users]
        found_codes = {row["Code"] for row in users}
        not_found_codes = [code for code in codes if code not in found_codes]
        if not user_ids:
            return [], not_found_codes

        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("OA_CONN 必须是 MySQL 连接")

        id_placeholders = self._mysql_in_clause(user_ids)
        code_placeholders = self._mysql_in_clause(found_codes)
        queries = [
            (
                "membership_userbaseinfo",
                "SELECT Id AS user_id, Code AS code, EntryTime AS entry_time "
                "FROM oa_hrcenter.membership_userbaseinfo "
                f"WHERE Id IN ({id_placeholders}) AND Deleted=0",
                tuple(user_ids),
            ),
            (
                "check_userinfobyday",
                "SELECT Id AS user_id, Code AS code, EntryTime AS entry_time "
                "FROM oa_hrcenter.check_userinfobyday "
                f"WHERE Id IN ({id_placeholders})",
                tuple(user_ids),
            ),
            (
                "tb_entryinfo",
                "SELECT Id AS user_id, Code AS code, EntryTime AS entry_time "
                "FROM oa_hrcenter.tb_entryinfo "
                f"WHERE Code IN ({code_placeholders}) AND Deleted=0",
                tuple(found_codes),
            ),
        ]

        rows: list[dict[str, Any]] = []
        async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
            for table_name, sql, params in queries:
                await cur.execute(sql, params)
                for row in await cur.fetchall():
                    rows.append(
                        {
                            "source": "OA",
                            "table": table_name,
                            "code": row.get("code"),
                            "user_id": row.get("user_id"),
                            "entry_time": self._format_value(row.get("entry_time")),
                        }
                    )
        return rows, not_found_codes

    async def _fetch_fcc_entry_times(self, conn_id: int, codes: Sequence[str]) -> list[dict[str, Any]]:
        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("FCC_CONN 连接池不存在")

        placeholders = self._sqlserver_in_clause(codes)
        sql = (
            "SELECT Id, Code, EntryTime "
            "FROM MemberShip_UserBaseInfo "
            f"WHERE Code IN ({placeholders}) AND Deleted=0"
        )
        rows: list[dict[str, Any]] = []
        async with pool.acquire() as conn, conn.cursor() as cur:
            await cur.execute(sql, tuple(codes))
            columns = [col[0] for col in cur.description]
            for row in await cur.fetchall():
                data = dict(zip(columns, row))
                rows.append(
                    {
                        "source": "FCC",
                        "table": "MemberShip_UserBaseInfo",
                        "code": data.get("Code"),
                        "user_id": self._format_value(data.get("Id")),
                        "entry_time": self._format_value(data.get("EntryTime")),
                    }
                )
        return rows

    async def _update_oa_positive_time(
        self,
        conn_id: int,
        user_ids: Sequence[str],
        mysql_time: str,
        json_time: str,
    ) -> dict[str, int]:
        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("OA_CONN 必须是 MySQL 连接")

        placeholders = self._mysql_in_clause(user_ids)
        statements = [
            (
                "check_userbaseinfo",
                f"UPDATE oa_hrcenter.check_userbaseinfo SET PositiveTime=%s WHERE Id IN ({placeholders})",
                tuple([mysql_time, *user_ids]),
            ),
            (
                "check_userinfobyday",
                f"UPDATE oa_hrcenter.check_userinfobyday SET PositiveTime=%s WHERE Id IN ({placeholders})",
                tuple([mysql_time, *user_ids]),
            ),
            (
                "membership_userbaseinfo",
                f"UPDATE oa_hrcenter.membership_userbaseinfo SET PositiveTime=%s WHERE Id IN ({placeholders}) AND Deleted=0",
                tuple([mysql_time, *user_ids]),
            ),
            (
                "membership_positiveconfirm",
                "UPDATE membership_positiveconfirm "
                "SET PositiveJSON = JSON_SET(PositiveJSON, '$.PositiveTime', %s) "
                f"WHERE UserBaseInfoId IN ({placeholders})",
                tuple([json_time, *user_ids]),
            ),
        ]

        affected: dict[str, int] = {}
        async with pool.acquire() as conn, conn.cursor() as cur:
            try:
                await conn.begin()
                for table_name, sql, params in statements:
                    await cur.execute(sql, params)
                    affected[table_name] = cur.rowcount or 0
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
        return affected

    async def _update_fcc_positive_time(self, conn_id: int, codes: Sequence[str], positive_time: str) -> int:
        if not codes:
            return 0

        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("FCC_CONN 连接池不存在")

        placeholders = self._sqlserver_in_clause(codes)
        sql = (
            "UPDATE MemberShip_UserBaseInfo "
            f"SET PositiveTime=? WHERE Code IN ({placeholders}) AND Deleted=0"
        )
        async with pool.acquire() as conn, conn.cursor() as cur:
            try:
                await cur.execute(sql, tuple([positive_time, *codes]))
                affected = cur.rowcount or 0
                await conn.commit()
                return affected
            except Exception:
                await conn.rollback()
                raise

    async def _update_oa_entry_time(
        self,
        conn_id: int,
        user_ids: Sequence[str],
        codes: Sequence[str],
        mysql_time: str,
        date_value: str,
    ) -> dict[str, int]:
        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("OA_CONN 必须是 MySQL 连接")

        id_placeholders = self._mysql_in_clause(user_ids)
        code_placeholders = self._mysql_in_clause(codes)
        statements = [
            (
                "membership_userbaseinfo",
                f"UPDATE oa_hrcenter.membership_userbaseinfo SET EntryTime=%s WHERE Id IN ({id_placeholders}) AND Deleted=0",
                tuple([mysql_time, *user_ids]),
            ),
            (
                "check_userinfobyday",
                f"UPDATE oa_hrcenter.check_userinfobyday SET EntryTime=%s WHERE Id IN ({id_placeholders})",
                tuple([mysql_time, *user_ids]),
            ),
            (
                "tb_entryinfo",
                f"UPDATE oa_hrcenter.tb_entryinfo SET EntryTime=%s WHERE Code IN ({code_placeholders}) AND Deleted=0",
                tuple([date_value, *codes]),
            ),
        ]

        affected: dict[str, int] = {}
        async with pool.acquire() as conn, conn.cursor() as cur:
            try:
                await conn.begin()
                for table_name, sql, params in statements:
                    await cur.execute(sql, params)
                    affected[table_name] = cur.rowcount or 0
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
        return affected

    async def _update_fcc_entry_time(self, conn_id: int, codes: Sequence[str], entry_time: str) -> int:
        if not codes:
            return 0

        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("FCC_CONN 连接池不存在")

        placeholders = self._sqlserver_in_clause(codes)
        sql = (
            "UPDATE MemberShip_UserBaseInfo "
            f"SET EntryTime=? WHERE Code IN ({placeholders}) AND Deleted=0"
        )
        async with pool.acquire() as conn, conn.cursor() as cur:
            try:
                await cur.execute(sql, tuple([entry_time, *codes]))
                affected = cur.rowcount or 0
                await conn.commit()
                return affected
            except Exception:
                await conn.rollback()
                raise

    def _merge_rows(
        self,
        codes: Sequence[str],
        oa_rows: Sequence[dict[str, Any]],
        fcc_rows: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        order = {code: index for index, code in enumerate(codes)}
        rows = [*oa_rows, *fcc_rows]
        return sorted(rows, key=lambda row: (order.get(row.get("code"), len(order)), row.get("source"), row.get("table")))

    def _format_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)


oa_positive_time_service = OAPositiveTimeService()
