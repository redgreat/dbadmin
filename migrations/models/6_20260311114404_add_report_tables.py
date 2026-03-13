from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "report_config" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted" SMALLINT NOT NULL DEFAULT 0,
    "deleted_at" TIMESTAMPTZ,
    "system_name" VARCHAR(100) NOT NULL,
    "report_name" VARCHAR(100) NOT NULL,
    "sql_statement" TEXT NOT NULL,
    "maintainer" VARCHAR(100) NOT NULL,
    "db_connection_id" BIGINT NOT NULL REFERENCES "conn" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_report_conf_created_505614" ON "report_config" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_report_conf_updated_bcde1e" ON "report_config" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_report_conf_deleted_c5ce12" ON "report_config" ("deleted");
CREATE INDEX IF NOT EXISTS "idx_report_conf_system__d61695" ON "report_config" ("system_name");
CREATE INDEX IF NOT EXISTS "idx_report_conf_report__dac706" ON "report_config" ("report_name");
CREATE INDEX IF NOT EXISTS "idx_report_conf_maintai_e334f0" ON "report_config" ("maintainer");
COMMENT ON COLUMN "report_config"."deleted" IS '删除标记: 0-未删除, 1-已删除';
COMMENT ON COLUMN "report_config"."deleted_at" IS '删除时间';
COMMENT ON COLUMN "report_config"."system_name" IS '系统名称';
COMMENT ON COLUMN "report_config"."report_name" IS '报表名称';
COMMENT ON COLUMN "report_config"."sql_statement" IS 'SQL语句';
COMMENT ON COLUMN "report_config"."maintainer" IS '维护人';
COMMENT ON COLUMN "report_config"."db_connection_id" IS '数据库连接ID';
COMMENT ON TABLE "report_config" IS '报表配置模型';
        CREATE TABLE IF NOT EXISTS "report_generation" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "deleted" SMALLINT NOT NULL DEFAULT 0,
    "deleted_at" TIMESTAMPTZ,
    "report_name" VARCHAR(200) NOT NULL,
    "generator" VARCHAR(100) NOT NULL,
    "generated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMPTZ,
    "status" VARCHAR(20) NOT NULL DEFAULT 'exporting',
    "file_path" VARCHAR(500),
    "execution_json" JSONB,
    "report_config_id" BIGINT NOT NULL REFERENCES "report_config" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_report_gene_deleted_59c59e" ON "report_generation" ("deleted");
CREATE INDEX IF NOT EXISTS "idx_report_gene_report__60e441" ON "report_generation" ("report_name");
CREATE INDEX IF NOT EXISTS "idx_report_gene_generat_07f151" ON "report_generation" ("generator");
CREATE INDEX IF NOT EXISTS "idx_report_gene_generat_a5d041" ON "report_generation" ("generated_at");
CREATE INDEX IF NOT EXISTS "idx_report_gene_status_6cb679" ON "report_generation" ("status");
COMMENT ON COLUMN "report_generation"."deleted" IS '删除标记: 0-未删除, 1-已删除';
COMMENT ON COLUMN "report_generation"."deleted_at" IS '删除时间';
COMMENT ON COLUMN "report_generation"."report_name" IS '报表名称';
COMMENT ON COLUMN "report_generation"."generator" IS '生成人';
COMMENT ON COLUMN "report_generation"."generated_at" IS '生成时间';
COMMENT ON COLUMN "report_generation"."completed_at" IS '完成时间';
COMMENT ON COLUMN "report_generation"."status" IS '报表状态: exporting-导出中, completed-已完成, failed-失败';
COMMENT ON COLUMN "report_generation"."file_path" IS '文件路径';
COMMENT ON COLUMN "report_generation"."execution_json" IS '执行日志(SQL语句、数据库连接等)';
COMMENT ON COLUMN "report_generation"."report_config_id" IS '报表配置ID';
COMMENT ON TABLE "report_generation" IS '报表生成记录模型';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "report_generation";
        DROP TABLE IF EXISTS "report_config";"""


MODELS_STATE = (
    "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"
)
