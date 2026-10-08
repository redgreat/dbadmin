-- 壹好车服-接口调用统计 菜单+API 授权脚本（数据运维系统管理库 dbadmin，PostgreSQL）
-- 应用启动时 ensure_ehcf_apistat_menu() 会自动同步，此脚本供手工执行（幂等，可重复跑）
BEGIN;

-- 1. 二级菜单（父：壹好车服 path=/ehcf），order=6 紧跟“修改单据来源”(order=5)之后
INSERT INTO "public"."menu" ("name", "path", "parent_id", "component", "icon", "order", "menu_type", "is_hidden", "keepalive", "remark", "redirect", "created_at", "updated_at")
SELECT '接口调用统计', 'api-stat', m.id, '/ehcf/api-stat', 'mdi:chart-bar', 6, 'menu', false, true, null, null, NOW(), NOW()
FROM "public"."menu" m
WHERE m.path = '/ehcf' AND m.parent_id = 0 AND NOT EXISTS (
  SELECT 1 FROM "public"."menu" c WHERE c.path = 'api-stat' AND c.parent_id = m.id
);

-- 2. API 记录
INSERT INTO "public"."api" ("method", "path", "summary", "tags", "created_at", "updated_at")
SELECT 'GET', '/api/v1/ehcf/api-stat/list', '接口调用统计-成功修改', '壹好车服', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM "public"."api" WHERE method = 'GET' AND path = '/api/v1/ehcf/api-stat/list');

INSERT INTO "public"."api" ("method", "path", "summary", "tags", "created_at", "updated_at")
SELECT 'GET', '/api/v1/ehcf/api-stat/interfaces', '接口调用统计-写操作接口下拉', '壹好车服', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM "public"."api" WHERE method = 'GET' AND path = '/api/v1/ehcf/api-stat/interfaces');

-- 3. 菜单-API 关联
INSERT INTO "public"."menu_api" ("menu_id", "api_id", "created_at", "updated_at")
SELECT c.id, a.id, NOW(), NOW()
FROM "public"."menu" c
JOIN "public"."menu" m ON m.path = '/ehcf' AND m.parent_id = 0
CROSS JOIN "public"."api" a
WHERE c.path = 'api-stat' AND c.parent_id = m.id
  AND a.method = 'GET'
  AND a.path IN (
    '/api/v1/ehcf/api-stat/list',
    '/api/v1/ehcf/api-stat/interfaces'
  )
  AND NOT EXISTS (
    SELECT 1 FROM "public"."menu_api" ma WHERE ma.menu_id = c.id AND ma.api_id = a.id
  );

-- 4. 授予「管理员」角色
INSERT INTO "public"."role_menu" ("role_id", "menu_id")
SELECT r.id, c.id
FROM "public"."role" r
JOIN "public"."menu" c ON c.path = 'api-stat' AND c.parent_id = (SELECT id FROM "public"."menu" WHERE path = '/ehcf' AND parent_id = 0)
WHERE r.name = '管理员'
  AND NOT EXISTS (SELECT 1 FROM "public"."role_menu" rm WHERE rm.role_id = r.id AND rm.menu_id = c.id);

-- 5. 授予「壹好车服运维」角色
INSERT INTO "public"."role_menu" ("role_id", "menu_id")
SELECT r.id, c.id
FROM "public"."role" r
JOIN "public"."menu" c ON c.path = 'api-stat' AND c.parent_id = (SELECT id FROM "public"."menu" WHERE path = '/ehcf' AND parent_id = 0)
WHERE r.name = '壹好车服运维'
  AND NOT EXISTS (SELECT 1 FROM "public"."role_menu" rm WHERE rm.role_id = r.id AND rm.menu_id = c.id);

COMMIT;
