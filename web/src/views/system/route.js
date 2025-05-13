const Layout = () => import('@/layout/index.vue')

export default {
  name: 'System',
  path: '/system',
  component: Layout,
  redirect: '/system/user',
  meta: {
    title: '系统管理',
    icon: 'ph:user-list-bold',
    order: 5,
  },
  children: [
    {
      name: 'User',
      path: 'user',
      component: () => import('./user/index.vue'),
      meta: {
        title: '用户列表',
        icon: 'mdi:account',
        keepAlive: true,
      },
    },
    {
      name: 'Menu',
      path: 'menu',
      component: () => import('./menu/index.vue'),
      meta: {
        title: '菜单列表',
        icon: 'ic:twotone-menu-book',
        keepAlive: true,
      },
    },
    {
      name: 'Role',
      path: 'role',
      component: () => import('./role/index.vue'),
      meta: {
        title: '角色列表',
        icon: 'carbon:user-role',
        keepAlive: true,
      },
    },
    {
      name: 'Api',
      path: 'api',
      component: () => import('./api/index.vue'),
      meta: {
        title: 'API列表',
        icon: 'ant-design:api-outlined',
        keepAlive: true,
      },
    },
    {
      name: 'AuditLog',
      path: 'auditlog',
      component: () => import('./auditlog/index.vue'),
      meta: {
        title: '审计日志',
        icon: 'ant-design:audit-outlined',
        keepAlive: true,
        permissions: ['GET:/v1/auditlog/list'],
      },
    },
  ],
}
