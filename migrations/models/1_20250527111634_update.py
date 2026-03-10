from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


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


MODELS_STATE = (
    "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"
    "MQbYp7NxuYz5EM7GZTJ22qRHusu1Pf8fp6pxYA=="
)
