from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 创建 menu_api 表
        CREATE TABLE IF NOT EXISTS "menu_api" (
            "id" SERIAL PRIMARY KEY,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "menu_id" INT NOT NULL REFERENCES "menu" ("id") ON DELETE CASCADE,
            "api_id" INT NOT NULL REFERENCES "api" ("id") ON DELETE CASCADE,
            CONSTRAINT "menu_api_menu_id_api_id_uniq" UNIQUE ("menu_id", "api_id")
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS "menu_api_menu_id_idx" ON "menu_api" ("menu_id");
        CREATE INDEX IF NOT EXISTS "menu_api_api_id_idx" ON "menu_api" ("api_id");
        
        -- 删除 role_api 表（如果存在）
        DROP TABLE IF EXISTS "role_api";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- 删除 menu_api 表
        DROP TABLE IF EXISTS "menu_api";
        
        -- 重新创建 role_api 表
        CREATE TABLE IF NOT EXISTS "role_api" (
            "id" SERIAL PRIMARY KEY,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "role_id" INT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
            "api_id" INT NOT NULL REFERENCES "api" ("id") ON DELETE CASCADE,
            CONSTRAINT "role_api_role_id_api_id_uniq" UNIQUE ("role_id", "api_id")
        );
        
        CREATE INDEX IF NOT EXISTS "role_api_role_id_idx" ON "role_api" ("role_id");
        CREATE INDEX IF NOT EXISTS "role_api_api_id_idx" ON "role_api" ("api_id");
    """
