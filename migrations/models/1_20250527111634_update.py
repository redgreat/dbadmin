from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "db_connection" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(100) NOT NULL,
    "db_type" VARCHAR(20) NOT NULL,
    "host" VARCHAR(255) NOT NULL,
    "port" INT NOT NULL,
    "username" VARCHAR(100) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "database" VARCHAR(100) NOT NULL,
    "params" TEXT,
    "status" BOOL NOT NULL  DEFAULT False,
    "remark" TEXT
);
CREATE INDEX IF NOT EXISTS "idx_db_connecti_created_7a8c38" ON "db_connection" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_db_connecti_updated_969859" ON "db_connection" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_db_connecti_name_5b2d04" ON "db_connection" ("name");
CREATE INDEX IF NOT EXISTS "idx_db_connecti_db_type_e8b8d1" ON "db_connection" ("db_type");
CREATE INDEX IF NOT EXISTS "idx_db_connecti_status_9d8cd9" ON "db_connection" ("status");
COMMENT ON COLUMN "db_connection"."name" IS '连接名称';
COMMENT ON COLUMN "db_connection"."db_type" IS '数据库类型';
COMMENT ON COLUMN "db_connection"."host" IS '主机地址';
COMMENT ON COLUMN "db_connection"."port" IS '端口';
COMMENT ON COLUMN "db_connection"."username" IS '用户名';
COMMENT ON COLUMN "db_connection"."password" IS '密码(加密)';
COMMENT ON COLUMN "db_connection"."database" IS '数据库名';
COMMENT ON COLUMN "db_connection"."params" IS '连接参数';
COMMENT ON COLUMN "db_connection"."status" IS '连接状态';
COMMENT ON COLUMN "db_connection"."remark" IS '备注';
COMMENT ON TABLE "db_connection" IS '数据库连接模型';
        CREATE TABLE IF NOT EXISTS "task" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "type" VARCHAR(20) NOT NULL,
    "cron" VARCHAR(100) NOT NULL,
    "command" TEXT NOT NULL,
    "work_dir" VARCHAR(255) NOT NULL  DEFAULT '/home/app',
    "run_user" VARCHAR(50) NOT NULL  DEFAULT 'appuser',
    "env_vars" TEXT,
    "args" TEXT,
    "timeout" INT NOT NULL  DEFAULT 3600,
    "max_retries" INT NOT NULL  DEFAULT 3,
    "status" BOOL NOT NULL  DEFAULT True,
    "remark" TEXT,
    "last_run_time" TIMESTAMPTZ,
    "next_run_time" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "task"."name" IS '任务名称';
COMMENT ON COLUMN "task"."type" IS '任务类型：shell, python, http';
COMMENT ON COLUMN "task"."cron" IS 'Cron表达式';
COMMENT ON COLUMN "task"."command" IS '执行命令或函数';
COMMENT ON COLUMN "task"."work_dir" IS '执行目录';
COMMENT ON COLUMN "task"."run_user" IS '执行用户';
COMMENT ON COLUMN "task"."env_vars" IS '环境变量，格式：KEY=VALUE，每行一个';
COMMENT ON COLUMN "task"."args" IS '参数，JSON格式';
COMMENT ON COLUMN "task"."timeout" IS '超时时间(秒)，0表示不限制';
COMMENT ON COLUMN "task"."max_retries" IS '最大重试次数';
COMMENT ON COLUMN "task"."status" IS '任务状态：true启用，false禁用';
COMMENT ON COLUMN "task"."remark" IS '备注';
COMMENT ON COLUMN "task"."last_run_time" IS '上次执行时间';
COMMENT ON COLUMN "task"."next_run_time" IS '下次执行时间';
COMMENT ON COLUMN "task"."created_at" IS '创建时间';
COMMENT ON COLUMN "task"."updated_at" IS '更新时间';
COMMENT ON TABLE "task" IS '定时任务模型';
        CREATE TABLE IF NOT EXISTS "task_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(20) NOT NULL,
    "start_time" TIMESTAMPTZ NOT NULL,
    "end_time" TIMESTAMPTZ,
    "duration" INT,
    "output" TEXT,
    "error" TEXT,
    "retry_count" INT NOT NULL  DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "task_id" INT NOT NULL REFERENCES "task" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "task_log"."status" IS '执行状态：success, failed, timeout, running';
COMMENT ON COLUMN "task_log"."start_time" IS '开始时间';
COMMENT ON COLUMN "task_log"."end_time" IS '结束时间';
COMMENT ON COLUMN "task_log"."duration" IS '执行时长(秒)';
COMMENT ON COLUMN "task_log"."output" IS '执行输出';
COMMENT ON COLUMN "task_log"."error" IS '错误信息';
COMMENT ON COLUMN "task_log"."retry_count" IS '重试次数';
COMMENT ON COLUMN "task_log"."created_at" IS '创建时间';
COMMENT ON COLUMN "task_log"."task_id" IS '关联的任务';
COMMENT ON TABLE "task_log" IS '任务执行日志模型';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "db_connection";
        DROP TABLE IF EXISTS "task";
        DROP TABLE IF EXISTS "task_log";"""
