from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 添加仓储中心父菜单
        INSERT INTO "menu" ("created_at", "updated_at", "name", "remark", "menu_type", "icon", "path", "order", "parent_id", "is_hidden", "component", "keepalive", "redirect")
        VALUES (CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '仓储中心', NULL, 'catalog', 'mdi:warehouse', '/wms', 50, 0, FALSE, 'Layout', TRUE, NULL);

        -- 添加单据删除恢复子菜单（假设父菜单ID为上一个插入的ID，实际需要根据数据库调整）
        -- 注意：这里使用子查询获取父菜单ID
        INSERT INTO "menu" ("created_at", "updated_at", "name", "remark", "menu_type", "icon", "path", "order", "parent_id", "is_hidden", "component", "keepalive", "redirect")
        SELECT CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '单据删除', NULL, 'menu', 'mdi:delete-variant', '/wms/wms-delete', 1, m.id, FALSE, '/wms/wms-delete/index', TRUE, NULL
        FROM "menu" m WHERE m.name = '仓储中心' AND m.path = '/wms' LIMIT 1;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 删除单据删除恢复菜单
        DELETE FROM "menu" WHERE "name" = '单据删除' AND "path" = '/wms/wms-delete';

        -- 删除仓储中心父菜单
        DELETE FROM "menu" WHERE "name" = '仓储中心' AND "path" = '/wms';
    """
