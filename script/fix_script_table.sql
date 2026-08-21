-- 修复python_script表：添加env_config字段（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'python_script' AND column_name = 'env_config'
    ) THEN
        ALTER TABLE python_script ADD COLUMN env_config JSONB DEFAULT NULL;
        RAISE NOTICE 'Added env_config column to python_script';
    ELSE
        RAISE NOTICE 'env_config column already exists in python_script';
    END IF;
END $$;

-- 验证表结构
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'python_script'
ORDER BY ordinal_position;
