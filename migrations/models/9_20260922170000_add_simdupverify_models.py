from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE "sys_simdupverify_record" (
            "id" BIGINT AUTO_INCREMENT PRIMARY KEY,
            "batch_no" VARCHAR(50) NOT NULL,
            "source" VARCHAR(20) NOT NULL DEFAULT 'web',
            "status" VARCHAR(20) NOT NULL DEFAULT 'processing',
            "filename" VARCHAR(255) NOT NULL DEFAULT '',
            "total_count" INT NOT NULL DEFAULT 0,
            "duplicate_count" INT NOT NULL DEFAULT 0,
            "message" TEXT NULL,
            "result_file_path" VARCHAR(500) NULL,
            "user_id" BIGINT NULL,
            "username" VARCHAR(64) NOT NULL DEFAULT '',
            "api_caller" VARCHAR(100) NOT NULL DEFAULT '',
            "started_at" TIMESTAMP NULL,
            "finished_at" TIMESTAMP NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE ("batch_no"),
            INDEX "IDX_SIMDUPREC_BATCH" ("batch_no"),
            INDEX "IDX_SIMDUPREC_SOURCE" ("source"),
            INDEX "IDX_SIMDUPREC_STATUS" ("status"),
            INDEX "IDX_SIMDUPREC_USER" ("user_id"),
            INDEX "IDX_SIMDUPREC_CREATED" ("created_at"),
            INDEX "IDX_SIMDUPREC_UPDATED" ("updated_at")
        );
        CREATE TABLE "sys_simdupverify_result" (
            "id" BIGINT AUTO_INCREMENT PRIMARY KEY,
            "record_id" BIGINT NOT NULL,
            "sim_number" VARCHAR(200) NOT NULL,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX "IDX_SIMDUPRES_RECORD" ("record_id"),
            INDEX "IDX_SIMDUPRES_SIM" ("sim_number"),
            INDEX "IDX_SIMDUPRES_RECORD_SIM" ("record_id", "sim_number"),
            INDEX "IDX_SIMDUPRES_CREATED" ("created_at"),
            INDEX "IDX_SIMDUPRES_UPDATED" ("updated_at")
        );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "sys_simdupverify_result";
        DROP TABLE IF EXISTS "sys_simdupverify_record";
    """
