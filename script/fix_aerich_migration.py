"""
修复aerich迁移问题
"""
import asyncio
import asyncpg


async def fix_migration():
    """修复迁移"""
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='postgres',
        database='dbadmin'
    )

    try:
        # 检查python_script表的env_config列是否存在
        check_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'python_script' AND column_name = 'env_config'
        """
        result = await conn.fetch(check_sql)

        if not result:
            # 添加env_config列
            alter_sql = "ALTER TABLE python_script ADD COLUMN env_config JSONB DEFAULT NULL"
            await conn.execute(alter_sql)
            print("✓ 已添加 env_config 列到 python_script 表")
        else:
            print("✓ env_config 列已存在")

        # 检查aerich迁移记录
        check_aerich_sql = """
            SELECT version, app 
            FROM aerich 
            WHERE app = 'models' 
            ORDER BY id DESC 
            LIMIT 5
        """
        aerich_records = await conn.fetch(check_aerich_sql)

        if aerich_records:
            print("\n当前aerich迁移记录:")
            for record in aerich_records:
                print(f"  - {record['version']}")

        print("\n✓ 修复完成")

    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(fix_migration())
