import { request } from '@/utils'

export default {
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),
  // oplog
  getOpLogList: (params = {}) => request.get('/oplog/list', { params }),
  createOpLog: (data = {}) => request.post('/oplog/create', data),
  // conn
  getConnList: (params = {}) => request.get('/conn/list', { params }),
  getConnById: (params = {}) => request.get('/conn/get', { params }),
  createConn: (data = {}) => request.post('/conn/create', data),
  updateConn: (data = {}) => request.post('/conn/update', data),
  deleteConn: (params = {}) => request.delete('/conn/delete', { params }),
  testConn: (data = {}) => request.post('/conn/test', data),
  // oms
  updateOrdersAuditTimeBatch: (data = {}) => request.post('/oms/orders/update_audit_time_batch', data),
  deleteOrdersLogicalBatch: (data = {}) => request.post('/oms/orders/delete_logical_batch', data),
  deleteOrdersPhysicalBatch: (data = {}) => request.post('/oms/orders/delete_physical_batch', data),
  restoreOrderLogical: (data = {}) => request.post('/oms/orders/restore_logical', data),
  validateOrders: (data = {}) => request.post('/oms/validate-orders', data),
  batchUpdateAuditTime: (data = {}) => request.post('/oms/batch-update-audit-time', data),
  
  // oms 订单删除相关API
  validateOrdersForDelete: (data) => request.post('/oms/validate-orders-for-delete', data),
  batchDeleteOrders: (data) => request.post('/oms/batch-delete-orders', data),
  // simiccid
  simiccidUpload: (formData) =>
    request.post('/sim/simiccid/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  simiccidProcess: (data = {}) => request.post('/sim/simiccid/process', data),
  simiccidSubmit: (formData) =>
    request.post('/sim/simiccid/submit', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
}
