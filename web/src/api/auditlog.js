import { defHttp } from '@/utils/http'

export default {
  getAuditLogs: (params) => 
    defHttp.get('/v1/auditlog/list', { params }),
}
