from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "excel_import_task" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "task_name" VARCHAR(100) NOT NULL,
    "filename" VARCHAR(255) NOT NULL,
    "file_path" VARCHAR(500) NOT NULL,
    "file_size" BIGINT NOT NULL,
    "db_type" VARCHAR(20) NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'pending',
    "progress" INT NOT NULL DEFAULT 0,
    "message" VARCHAR(500),
    "sql_file_path" VARCHAR(500),
    "sql_file_size" BIGINT,
    "error_message" TEXT,
    "started_at" TIMESTAMPTZ,
    "completed_at" TIMESTAMPTZ,
    "user_id" BIGINT,
    "username" VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS "idx_excel_impor_created_ef3bcd" ON "excel_import_task" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_updated_ea68aa" ON "excel_import_task" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_task_na_000ed0" ON "excel_import_task" ("task_name");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_status_11ba33" ON "excel_import_task" ("status");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_started_b04d18" ON "excel_import_task" ("started_at");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_complet_64e48d" ON "excel_import_task" ("completed_at");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_user_id_9517b1" ON "excel_import_task" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_status_102e5c" ON "excel_import_task" ("status", "created_at");
CREATE INDEX IF NOT EXISTS "idx_excel_impor_user_id_0fc798" ON "excel_import_task" ("user_id", "status");
COMMENT ON COLUMN "excel_import_task"."task_name" IS '任务名称';
COMMENT ON COLUMN "excel_import_task"."filename" IS '原始文件名';
COMMENT ON COLUMN "excel_import_task"."file_path" IS '文件存储路径';
COMMENT ON COLUMN "excel_import_task"."file_size" IS '文件大小(字节)';
COMMENT ON COLUMN "excel_import_task"."db_type" IS '数据库类型(mysql/postgresql)';
COMMENT ON COLUMN "excel_import_task"."status" IS '任务状态(pending/processing/completed/failed)';
COMMENT ON COLUMN "excel_import_task"."progress" IS '进度百分比(0-100)';
COMMENT ON COLUMN "excel_import_task"."message" IS '进度消息';
COMMENT ON COLUMN "excel_import_task"."sql_file_path" IS '生成的SQL文件路径';
COMMENT ON COLUMN "excel_import_task"."sql_file_size" IS 'SQL文件大小(字节)';
COMMENT ON COLUMN "excel_import_task"."error_message" IS '错误信息';
COMMENT ON COLUMN "excel_import_task"."started_at" IS '开始处理时间';
COMMENT ON COLUMN "excel_import_task"."completed_at" IS '完成时间';
COMMENT ON COLUMN "excel_import_task"."user_id" IS '创建用户ID';
COMMENT ON COLUMN "excel_import_task"."username" IS '创建用户名';
COMMENT ON TABLE "excel_import_task" IS 'Excel导入任务模型';
        ALTER TABLE "task_log" ALTER COLUMN "task_id" TYPE INT USING "task_id"::INT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "task_log" ALTER COLUMN "task_id" TYPE INT USING "task_id"::INT;
        DROP TABLE IF EXISTS "excel_import_task";"""


MODELS_STATE = (
    "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"
    "AlolmXlzIUD1YMujuzoGR5efg/d3ga7w=="
)
