from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "db_connection" RENAME TO "conn";
        ALTER TABLE "conn" ALTER COLUMN "host" TYPE VARCHAR(200) USING "host"::VARCHAR(200);
        ALTER TABLE "conn" ALTER COLUMN "password" TYPE VARCHAR(200) USING "password"::VARCHAR(200);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "conn" RENAME TO "db_connection";
        ALTER TABLE "conn" ALTER COLUMN "host" TYPE VARCHAR(255) USING "host"::VARCHAR(255);
        ALTER TABLE "conn" ALTER COLUMN "password" TYPE VARCHAR(255) USING "password"::VARCHAR(255);"""
