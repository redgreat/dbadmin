-- 插入Python脚本管理菜单
-- 执行方式：在 dbadmin 数据库中运行此脚本

INSERT INTO menu (name, path, parent_id, component, icon, "order", menu_type, is_hidden, keepalive, remark, redirect)
VALUES ('Python脚本管理', 'script', 10, '/task/script', 'mdi:script-text-play', 3, 'menu', false, true, null, null);

-- 验证插入结果
SELECT id, name, path, parent_id, component, icon, "order", menu_type, is_hidden
FROM menu WHERE path = 'script';
