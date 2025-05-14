import { defHttp } from '@/utils/http'

export default {  // 创建按钮
  createButton: (data) => 
    defHttp.post('/button', data),

  // 更新按钮
  updateButton: (id, data) => 
    defHttp.put(`/button/${id}`, data),

  // 删除按钮
  deleteButton: (id) => 
    defHttp.delete(`/button/${id}`),
  
    // 获取菜单按钮
  getMenuButtons: (menuId) => 
    defHttp.get(`/button/list/menu/${menuId}`),
    // 获取所有按钮(按菜单分组)
  getButtonsMenuGroup: () => 
    defHttp.get('/button/menu-group'),

  // 获取角色按钮
  getRoleButtons: (roleId) => 
    defHttp.get(`/button/role/${roleId}`),

  // 设置角色按钮
  setRoleButtons: (roleId, buttonIds) => 
    defHttp.post(`/button/role/${roleId}`, buttonIds),
  
  // 检查按钮权限
  checkButtonPermission: (menuId, buttonCode) => 
    defHttp.get('/button/check', { params: { menu_id: menuId, button_code: buttonCode } }),
}
