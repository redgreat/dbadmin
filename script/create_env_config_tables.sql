-- 创建环境变量配置表
CREATE TABLE IF NOT EXISTS env_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description VARCHAR(255),
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_env_config_key ON env_config(key);

-- 创建Python包管理表
CREATE TABLE IF NOT EXISTS python_package (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    version VARCHAR(50),
    description VARCHAR(255),
    is_installed BOOLEAN DEFAULT FALSE,
    installed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_python_package_name ON python_package(name);
CREATE INDEX IF NOT EXISTS idx_python_package_installed ON python_package(is_installed);

-- 插入默认环境变量示例
INSERT INTO env_config (key, value, description, is_sensitive) VALUES
('DB_HOST', 'localhost', '数据库主机地址', FALSE),
('DB_PORT', '3306', '数据库端口', FALSE),
('DB_USER', 'root', '数据库用户名', FALSE),
('DB_PASSWORD', '', '数据库密码', TRUE),
('WECOM_WEBHOOK_KEY', '', '企微Webhook Key', TRUE),
('ENV', 'production', '运行环境', FALSE)
ON CONFLICT (key) DO NOTHING;
