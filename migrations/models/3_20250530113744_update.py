from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "conn" ALTER COLUMN "status" TYPE SMALLINT USING "status"::SMALLINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "conn" ALTER COLUMN "status" TYPE BOOL USING "status"::BOOL;"""
