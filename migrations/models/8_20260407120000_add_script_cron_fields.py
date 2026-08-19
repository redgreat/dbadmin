from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "python_script" ADD COLUMN "cron" VARCHAR(100);
        ALTER TABLE "python_script" ADD COLUMN "last_run_time" TIMESTAMPTZ;
        ALTER TABLE "python_script" ADD COLUMN "next_run_time" TIMESTAMPTZ;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "python_script" DROP COLUMN "cron";
        ALTER TABLE "python_script" DROP COLUMN "last_run_time";
        ALTER TABLE "python_script" DROP COLUMN "next_run_time";
    """
