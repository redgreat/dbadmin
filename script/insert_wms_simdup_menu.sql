-- 仓储中心-SIM卡重复入库验证 菜单+API 授权脚本（数据运维系统管理库 dbadmin）
-- 应用启动时 ensure_wms_simdup_menu() 会自动同步，此脚本供手工执行参考
-- 一级菜单：仓储中心 path=/wms（已存在）；二级菜单：SIM卡重复入库验证 path=simdup
BEGIN;

-- 1. 二级菜单（父：仓储中心 path=/wms）
INSERT INTO menu (name, path, parent_id, component, icon, "order", menu_type, is_hidden, keepalive, remark, redirect, created_at, updated_at)
SELECT 'SIM卡重复入库验证', 'simdup', m.id, '/wms/simdup', 'mdi:sim-card', 99, 'menu', false, true, null, null, NOW(), NOW()
FROM menu m
WHERE m.path = '/wms' AND m.parent_id = 0 AND NOT EXISTS (
  SELECT 1 FROM menu c WHERE c.path = 'simdup' AND c.parent_id = m.id
);

-- 2. API 记录
INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'GET', '/api/v1/wms/simdup/template', '下载SIM卡重复入库验证Excel模板', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='GET' AND path='/api/v1/wms/simdup/template');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'POST', '/api/v1/wms/simdup/verify', '上传Excel验证SIM卡重复入库', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='POST' AND path='/api/v1/wms/simdup/verify');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'GET', '/api/v1/wms/simdup/record/{record_id}/export', '下载某次验证记录的重复编码Excel', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='GET' AND path='/api/v1/wms/simdup/record/{record_id}/export');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'POST', '/api/v1/wms/simdup/record/list', 'SIM卡重复入库验证记录列表', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='POST' AND path='/api/v1/wms/simdup/record/list');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'GET', '/api/v1/wms/simdup/record/{record_id}', '查看某次验证记录的详情', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='GET' AND path='/api/v1/wms/simdup/record/{record_id}');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'GET', '/api/v1/wms/simdup/record/{record_id}/results', '查看某次验证记录命中的重复卡号', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='GET' AND path='/api/v1/wms/simdup/record/{record_id}/results');

INSERT INTO api (method, path, summary, tags, created_at, updated_at)
SELECT 'POST', '/api/v1/wms/simdup/api/verify', '对外API-验证SimNumber是否重复入库', '仓储中心', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM api WHERE method='POST' AND path='/api/v1/wms/simdup/api/verify');

-- 3. 菜单-API 关联
INSERT INTO menu_api (menu_id, api_id, created_at, updated_at)
SELECT c.id, a.id, NOW(), NOW()
FROM menu c
JOIN menu m ON m.path = '/wms' AND m.parent_id = 0
CROSS JOIN api a
WHERE c.path = 'simdup' AND c.parent_id = m.id
  AND a.method IN ('GET', 'POST')
  AND a.path IN (
    '/api/v1/wms/simdup/template',
    '/api/v1/wms/simdup/verify',
    '/api/v1/wms/simdup/record/{record_id}/export',
    '/api/v1/wms/simdup/record/list',
    '/api/v1/wms/simdup/record/{record_id}',
    '/api/v1/wms/simdup/record/{record_id}/results',
    '/api/v1/wms/simdup/api/verify'
  )
  AND NOT EXISTS (
    SELECT 1 FROM menu_api ma WHERE ma.menu_id = c.id AND ma.api_id = a.id
  );

-- 4. 授予「管理员」角色（一级菜单已授权，此处仅补二级菜单）
INSERT INTO role_menu (role_id, menu_id)
SELECT r.id, c.id
FROM role r
JOIN menu c ON c.path = 'simdup' AND c.parent_id = (SELECT id FROM menu WHERE path='/wms' AND parent_id=0)
WHERE r.name = '管理员'
  AND NOT EXISTS (SELECT 1 FROM role_menu rm WHERE rm.role_id = r.id AND rm.menu_id = c.id);

COMMIT;
