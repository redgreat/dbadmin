-- 为python_script表添加env_config字段（脚本专属环境变量）
ALTER TABLE python_script ADD COLUMN IF NOT EXISTS env_config JSONB DEFAULT NULL;

-- 添加注释
COMMENT ON COLUMN python_script.env_config IS '脚本专属环境变量（JSON格式），执行时覆盖全局环境变量';
