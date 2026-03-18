from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "sys_dict" (
    "id" BIGSERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(100) NOT NULL,
    "code" VARCHAR(100) NOT NULL UNIQUE,
    "parent_code" VARCHAR(100),
    "deleted" BOOL NOT NULL DEFAULT False,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_sys_dict_created_141b50" ON "sys_dict" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_sys_dict_updated_6f42ee" ON "sys_dict" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_sys_dict_name_f1e63c" ON "sys_dict" ("name");
CREATE INDEX IF NOT EXISTS "idx_sys_dict_code_4e8e98" ON "sys_dict" ("code");
CREATE INDEX IF NOT EXISTS "idx_sys_dict_parent__73fed1" ON "sys_dict" ("parent_code");
CREATE INDEX IF NOT EXISTS "idx_sys_dict_deleted_39a6c4" ON "sys_dict" ("deleted");
COMMENT ON COLUMN "sys_dict"."name" IS '字典名称';
COMMENT ON COLUMN "sys_dict"."code" IS '字典编码';
COMMENT ON COLUMN "sys_dict"."parent_code" IS '父级编码';
COMMENT ON COLUMN "sys_dict"."deleted" IS '逻辑删除标记';
COMMENT ON COLUMN "sys_dict"."deleted_at" IS '删除时间';
COMMENT ON TABLE "sys_dict" IS '字典管理模型';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "sys_dict";"""


MODELS_STATE = (
    "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"
    "ShboXRn9X03NJRKjU3NpQFULKhWh0neaNB32vLL2FDUByEhgdJg1aanRQlGLdvsH85KTJx"
    "rPgujILUFxX9bFsqb2MyM1XFylNKg1pVjKzD2VYPxYyIjiFkudVibfLiUxfrX08VRDF7+f"
    "mlroKNf5yBLoKKn6YWHbtPw5NaWmVPVM0/JL2KAoXb+aCoqSpuaq57nqefQ9cq6OfZyBmF"
    "mvDaueYTVmrTxJy4xd/Zxk106v+hltbMTEbscCPXm5jVGVNCDZAM82SApNkBSqkRSKOctb"
    "ZG9YkIwFxp6fGocgE03XW50M30uO/Y4AwvR7jwXGnpaKJEiUC2g1Lbv/ge+Q7391vRKTsg"
    "bMlMzoZJakG8TZV1Su1exc8mqTOidera5zgntZTG1/RZwC+0vJDK1NWc3I9Za1WpiqVUmr"
    "sszTE4R4CAtakHYtm0LDg4aHyUMlgPn7HfbKy23uwzojOhzclQkDabxFDKntYTa8gpEC6y"
    "9NHhY5KDUTpUnlA9Os0427tktCOQ3yVWPJQeJ0zXtkh+nwIge7n0xLV8PjD55YyG6Mri1d"
    "tZCIOtg99BYS0XvkW0jk+m1k+0ikmkXk+0ikWkwc1UcimSGVNNs59mzj+rSEaDvcWdRRbS"
    "gZMxmy7RExbb3lRX3Bnl8a2q82K1MiI2dGNUexf1fnUAXd2P8Ohz9MAHvqOuAEpWcgVjeA"
    "Tol00Pl5BFhrUOysU/NwZkHJ9nL3f74BqwE="
)
