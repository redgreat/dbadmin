-- 壹好车服-车务待办人刷新 菜单+API 授权脚本（数据运维系统管理库 dbadmin）
-- 应用启动时 ensure_ehcf_newaccept_menu() 会自动同步，此脚本供手工执行参考
BEGIN;

-- 1. 二级菜单（父：壹好车服 path=/ehcf）
INSERT INTO menu (name, path, parent_id, component, icon, "order", menu_type, is_hidden, keepalive, remark, redirect, created_at, updated_at)
SELECT '车务待办人刷新', 'newaccept-refresh', m.id, '/ehcf/newaccept-refresh', 'mdi:refresh', 4, 'menu', false, true, null, null, NOW(), NOW()
FROM menu m
WHERE m.path = '/ehcf' AND m.parent_id = 0 AND NOT EXISTS (
  SELECT 1 FROM menu c WHERE c.path = 'newaccept-refresh' AND c.parent_id = m.id
);

-- 2. API 记录
INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'GET', '/api/v1/ehcf/newaccept-refresh/template', '下载固定Excel模板', '壹好车服', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='GET' AND path='/api/v1/ehcf/newaccept-refresh/template');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'POST', '/api/v1/ehcf/newaccept-refresh/preview', '上传预览-车务待办人刷新', '壹好车服', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='POST' AND path='/api/v1/ehcf/newaccept-refresh/preview');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'POST', '/api/v1/ehcf/newaccept-refresh/execute', '执行车务待办人刷新', '壹好车服', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='POST' AND path='/api/v1/ehcf/newaccept-refresh/execute');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'POST', '/api/v1/ehcf/newaccept-refresh/cleanup', '清理临时表', '壹好车服', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='POST' AND path='/api/v1/ehcf/newaccept-refresh/cleanup');

-- 3. 菜单-API 关联
INSERT INTO menu_api (menu_id, api_id, created_at, updated_at)
SELECT c.id, a.id, NOW(), NOW()
FROM menu c
JOIN menu m ON m.path = '/ehcf' AND m.parent_id = 0
CROSS JOIN api a
WHERE c.path = 'newaccept-refresh' AND c.parent_id = m.id
  AND a.method = 'POST'
  AND a.path IN (
    '/api/v1/ehcf/newaccept-refresh/preview',
    '/api/v1/ehcf/newaccept-refresh/execute',
    '/api/v1/ehcf/newaccept-refresh/cleanup'
  )
  AND NOT EXISTS (
    SELECT 1 FROM menu_api ma WHERE ma.menu_id = c.id AND ma.api_id = a.id
  );

-- 3.1 菜单-API 关联（模板下载，GET）
INSERT INTO menu_api (menu_id, api_id, created_at, updated_at)
SELECT c.id, a.id, NOW(), NOW()
FROM menu c
JOIN menu m ON m.path = '/ehcf' AND m.parent_id = 0
CROSS JOIN api a
WHERE c.path = 'newaccept-refresh' AND c.parent_id = m.id
  AND a.method = 'GET'
  AND a.path = '/api/v1/ehcf/newaccept-refresh/template'
  AND NOT EXISTS (
    SELECT 1 FROM menu_api ma WHERE ma.menu_id = c.id AND ma.api_id = a.id
  );

-- 4. 授予「壹好车服运维」角色（二级菜单；一级菜单已授权，跳过）
INSERT INTO role_menu (role_id, menu_id)
SELECT r.id, c.id
FROM role r
JOIN menu c ON c.path = 'newaccept-refresh' AND c.parent_id = (SELECT id FROM menu WHERE path='/ehcf' AND parent_id=0)
WHERE r.name = '壹好车服运维'
  AND NOT EXISTS (SELECT 1 FROM role_menu rm WHERE rm.role_id = r.id AND rm.menu_id = c.id);

COMMIT;
