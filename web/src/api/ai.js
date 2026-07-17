import { request } from '@/utils'

export default {
  // Token 管理
  listTokens: (params = {}) => request.get('/ai/token/', { params }),
  createToken: (data = {}) => request.post('/ai/token/', data),
  updateToken: (data = {}) => request.post('/ai/token/update', data),
  deleteToken: (data = {}) => request.post('/ai/token/delete', data),
  
  // MCP Tools
  listMcpTools: (params = {}) => request.get('/ai/token/mcp_tools', { params }),

  // LLM 配置
  listLlmConfigs: (params = {}) => request.get('/ai/llm-config/', { params }),
  createLlmConfig: (data = {}) => request.post('/ai/llm-config/', data),
  updateLlmConfig: (data = {}) => request.post('/ai/llm-config/update', data),

  // 调用日志
  listToolLogs: (params = {}) => request.get('/ai/call-log/', { params }),

  // 审批管理
  listApprovals: (params = {}) => request.get('/ai/approval/', { params }),
  approveApproval: (approval_no, data = {}) => request.post(`/ai/approval/${approval_no}/approve`, data),
  rejectApproval: (approval_no, data = {}) => request.post(`/ai/approval/${approval_no}/reject`, data),
}
