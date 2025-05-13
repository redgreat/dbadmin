import { defHttp } from '@/utils/http'

export default {
  // 创建按钮
  createButton: (data) => 
    defHttp.post('/v1/api/button', data),

  // 更新按钮
  updateButton: (id, data) => 
    defHttp.put(`/v1/api/button/${id}`, data),

  // 删除按钮
  deleteButton: (id) => 
    defHttp.delete(`/v1/api/button/${id}`),
  // 获取菜单按钮
  getMenuButtons: (menuId) => 
    defHttp.get(`/api/button/menu/${menuId}`),

  // 获取角色按钮
  getRoleButtons: (roleId) => 
    defHttp.get(`/api/button/role/${roleId}`),

  // 设置角色按钮
  setRoleButtons: (roleId, buttonIds) => 
    defHttp.post(`/api/button/role/${roleId}`, buttonIds),

  // 检查按钮权限
  checkButtonPermission: (menuId, buttonCode) => 
    defHttp.get('/api/button/check', { params: { menu_id: menuId, button_code: buttonCode } }),
}
