-- 插入环境配置管理菜单（挂在运维中心下）
INSERT INTO menu (name, path, parent_id, component, icon, "order", menu_type, is_hidden, keepalive, remark, redirect)
VALUES ('环境配置管理', 'env-config', 10, '/task/env-config', 'mdi:cog', 4, 'menu', false, true, null, null);
