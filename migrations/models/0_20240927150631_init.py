from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "api" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "path" VARCHAR(100) NOT NULL,
    "method" VARCHAR(6) NOT NULL,
    "summary" VARCHAR(500) NOT NULL,
    "tags" VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_api_created_78d19f" ON "api" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_api_updated_643c8b" ON "api" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_api_path_9ed611" ON "api" ("path");
CREATE INDEX IF NOT EXISTS "idx_api_method_a46dfb" ON "api" ("method");
CREATE INDEX IF NOT EXISTS "idx_api_summary_400f73" ON "api" ("summary");
CREATE INDEX IF NOT EXISTS "idx_api_tags_04ae27" ON "api" ("tags");
COMMENT ON COLUMN "api"."path" IS 'API路径';
COMMENT ON COLUMN "api"."method" IS '请求方法';
COMMENT ON COLUMN "api"."summary" IS '请求简介';
COMMENT ON COLUMN "api"."tags" IS 'API标签';
CREATE TABLE IF NOT EXISTS "auditlog" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL,
    "username" VARCHAR(64) NOT NULL  DEFAULT '',
    "module" VARCHAR(64) NOT NULL  DEFAULT '',
    "summary" VARCHAR(128) NOT NULL  DEFAULT '',
    "method" VARCHAR(10) NOT NULL  DEFAULT '',
    "path" VARCHAR(255) NOT NULL  DEFAULT '',
    "status" INT NOT NULL  DEFAULT -1,
    "response_time" INT NOT NULL  DEFAULT 0
);
CREATE INDEX IF NOT EXISTS "idx_auditlog_created_cc33d0" ON "auditlog" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_auditlog_updated_2f871f" ON "auditlog" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_auditlog_user_id_4b93fa" ON "auditlog" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_auditlog_usernam_b187b3" ON "auditlog" ("username");
CREATE INDEX IF NOT EXISTS "idx_auditlog_module_04058b" ON "auditlog" ("module");
CREATE INDEX IF NOT EXISTS "idx_auditlog_summary_3e27da" ON "auditlog" ("summary");
CREATE INDEX IF NOT EXISTS "idx_auditlog_method_4270a2" ON "auditlog" ("method");
CREATE INDEX IF NOT EXISTS "idx_auditlog_path_b99502" ON "auditlog" ("path");
CREATE INDEX IF NOT EXISTS "idx_auditlog_status_2a72d2" ON "auditlog" ("status");
CREATE INDEX IF NOT EXISTS "idx_auditlog_respons_8caa87" ON "auditlog" ("response_time");
COMMENT ON COLUMN "auditlog"."user_id" IS '用户ID';
COMMENT ON COLUMN "auditlog"."username" IS '用户名称';
COMMENT ON COLUMN "auditlog"."module" IS '功能模块';
COMMENT ON COLUMN "auditlog"."summary" IS '请求描述';
COMMENT ON COLUMN "auditlog"."method" IS '请求方法';
COMMENT ON COLUMN "auditlog"."path" IS '请求路径';
COMMENT ON COLUMN "auditlog"."status" IS '状态码';
COMMENT ON COLUMN "auditlog"."response_time" IS '响应时间(单位ms)';
CREATE TABLE IF NOT EXISTS "menu" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL,
    "remark" JSONB,
    "menu_type" VARCHAR(7),
    "icon" VARCHAR(100),
    "path" VARCHAR(100) NOT NULL,
    "order" INT NOT NULL  DEFAULT 0,
    "parent_id" INT NOT NULL  DEFAULT 0,
    "is_hidden" BOOL NOT NULL  DEFAULT False,
    "component" VARCHAR(100) NOT NULL,
    "keepalive" BOOL NOT NULL  DEFAULT True,
    "redirect" VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS "idx_menu_created_b6922b" ON "menu" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_menu_updated_e6b0a1" ON "menu" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_menu_name_b9b853" ON "menu" ("name");
CREATE INDEX IF NOT EXISTS "idx_menu_path_bf95b2" ON "menu" ("path");
CREATE INDEX IF NOT EXISTS "idx_menu_order_606068" ON "menu" ("order");
CREATE INDEX IF NOT EXISTS "idx_menu_parent__bebd15" ON "menu" ("parent_id");
COMMENT ON COLUMN "menu"."name" IS '菜单名称';
COMMENT ON COLUMN "menu"."remark" IS '保留字段';
COMMENT ON COLUMN "menu"."menu_type" IS '菜单类型';
COMMENT ON COLUMN "menu"."icon" IS '菜单图标';
COMMENT ON COLUMN "menu"."path" IS '菜单路径';
COMMENT ON COLUMN "menu"."order" IS '排序';
COMMENT ON COLUMN "menu"."parent_id" IS '父菜单ID';
COMMENT ON COLUMN "menu"."is_hidden" IS '是否隐藏';
COMMENT ON COLUMN "menu"."component" IS '组件';
COMMENT ON COLUMN "menu"."keepalive" IS '存活';
COMMENT ON COLUMN "menu"."redirect" IS '重定向';
CREATE TABLE IF NOT EXISTS "role" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(20) NOT NULL UNIQUE,
    "desc" VARCHAR(500)
);
CREATE INDEX IF NOT EXISTS "idx_role_created_7f5f71" ON "role" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_role_updated_5dd337" ON "role" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_role_name_e5618b" ON "role" ("name");
COMMENT ON COLUMN "role"."name" IS '角色名称';
COMMENT ON COLUMN "role"."desc" IS '角色描述';
CREATE TABLE IF NOT EXISTS "user" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "username" VARCHAR(20) NOT NULL UNIQUE,
    "alias" VARCHAR(30),
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "phone" VARCHAR(20),
    "password" VARCHAR(128),
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_superuser" BOOL NOT NULL  DEFAULT False,
    "last_login" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_user_created_b19d59" ON "user" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_user_updated_dfdb43" ON "user" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_user_usernam_9987ab" ON "user" ("username");
CREATE INDEX IF NOT EXISTS "idx_user_alias_6f9868" ON "user" ("alias");
CREATE INDEX IF NOT EXISTS "idx_user_email_1b4f1c" ON "user" ("email");
CREATE INDEX IF NOT EXISTS "idx_user_phone_4e3ecc" ON "user" ("phone");
CREATE INDEX IF NOT EXISTS "idx_user_is_acti_83722a" ON "user" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_user_is_supe_b8a218" ON "user" ("is_superuser");
CREATE INDEX IF NOT EXISTS "idx_user_last_lo_af118a" ON "user" ("last_login");
COMMENT ON COLUMN "user"."username" IS '用户名称';
COMMENT ON COLUMN "user"."alias" IS '姓名';
COMMENT ON COLUMN "user"."email" IS '邮箱';
COMMENT ON COLUMN "user"."phone" IS '电话';
COMMENT ON COLUMN "user"."password" IS '密码';
COMMENT ON COLUMN "user"."is_active" IS '是否激活';
COMMENT ON COLUMN "user"."is_superuser" IS '是否为超级管理员';
COMMENT ON COLUMN "user"."last_login" IS '最后登录时间';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "role_api" (
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
    "api_id" BIGINT NOT NULL REFERENCES "api" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "role_menu" (
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE,
    "menu_id" BIGINT NOT NULL REFERENCES "menu" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_role" (
    "user_id" BIGINT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" BIGINT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "MQbYp7NxuYz5EM7GZTJ22qRHusu1Pf8fp6pxYA=="
)
