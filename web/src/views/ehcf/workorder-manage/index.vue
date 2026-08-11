<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="工单逻辑删除" size="small">
        <n-form ref="deleteFormRef" :model="deleteForm" :rules="deleteRules" label-placement="left" :label-width="100">
          <n-form-item label="工单编码/Id" path="workorderNos">
            <n-input
              v-model:value="deleteForm.workorderNos"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
              placeholder="输入单个或多个工单编码或Id，逗号分隔"
            />
          </n-form-item>
          <n-form-item label="操作人" path="operatorId">
            <n-select
              v-model:value="deleteForm.operatorId"
              filterable
              remote
              clearable
              placeholder="输入姓名搜索用户中心用户"
              :options="operatorOptions"
              :loading="operatorLoading"
              @search="handleSearchOperator"
            />
          </n-form-item>
          <n-form-item label="备注" path="remark">
            <n-input
              v-model:value="deleteForm.remark"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              placeholder="非必填，记录运维日志使用"
            />
          </n-form-item>
          <n-space>
            <n-button :loading="deleteQuerying" @click="handleDeleteQuery">查询</n-button>
            <n-button type="primary" :loading="deleteExecuting" @click="handleDeleteExecute">执行逻辑删除</n-button>
            <n-button @click="handleDeleteReset">重置</n-button>
          </n-space>
        </n-form>
        <n-table v-if="deleteQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
          <thead>
            <tr>
              <th>工单Id</th>
              <th>工单编码</th>
              <th>客户名称</th>
              <th>工单状态</th>
              <th>删除状态</th>
              <th>删除人</th>
              <th>删除时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in deleteQueryResult" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.app_code }}</td>
              <td>{{ item.customer_name || '-' }}</td>
              <td>{{ item.work_status }}</td>
              <td>
                <n-tag :type="item.deleted ? 'error' : 'success'" size="small">
                  {{ item.deleted ? '已删除' : '正常' }}
                </n-tag>
              </td>
              <td>{{ item.deleted_by_name ? item.deleted_by_name + '-' + (item.deleted_by_code || '') + '-(' + item.deleted_by_id + ')' : (item.deleted_by_id || '-') }}</td>
              <td>{{ item.deleted_at || '-' }}</td>
            </tr>
          </tbody>
        </n-table>
      </n-card>

      <n-card title="工单逻辑删除恢复" size="small">
        <n-form ref="restoreFormRef" :model="restoreForm" :rules="restoreRules" label-placement="left" :label-width="100">
          <n-form-item label="工单编码/Id" path="workorderNo">
            <n-input v-model:value="restoreForm.workorderNo" clearable placeholder="输入单个工单编码或Id" />
          </n-form-item>
          <n-form-item label="操作人" path="operatorId">
            <n-select
              v-model:value="restoreForm.operatorId"
              filterable
              remote
              clearable
              placeholder="输入姓名搜索用户中心用户"
              :options="operatorOptions"
              :loading="operatorLoading"
              @search="handleSearchOperator"
            />
          </n-form-item>
          <n-form-item label="备注" path="remark">
            <n-input
              v-model:value="restoreForm.remark"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              placeholder="非必填，记录运维日志使用"
            />
          </n-form-item>
          <n-space>
            <n-button :loading="restoreQuerying" @click="handleRestoreQuery">查询</n-button>
            <n-button type="primary" :loading="restoreExecuting" @click="handleRestoreExecute">执行恢复</n-button>
            <n-button @click="handleRestoreReset">重置</n-button>
          </n-space>
        </n-form>
        <n-table v-if="restoreQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
          <thead>
            <tr>
              <th>工单Id</th>
              <th>工单编码</th>
              <th>客户名称</th>
              <th>工单状态</th>
              <th>删除状态</th>
              <th>删除人</th>
              <th>删除时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in restoreQueryResult" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.app_code }}</td>
              <td>{{ item.customer_name || '-' }}</td>
              <td>{{ item.work_status }}</td>
              <td>
                <n-tag :type="item.deleted ? 'error' : 'success'" size="small">
                  {{ item.deleted ? '已删除' : '正常' }}
                </n-tag>
              </td>
              <td>{{ item.deleted_by_name ? item.deleted_by_name + '-' + (item.deleted_by_code || '') + '-(' + item.deleted_by_id + ')' : (item.deleted_by_id || '-') }}</td>
              <td>{{ item.deleted_at || '-' }}</td>
            </tr>
          </tbody>
        </n-table>
      </n-card>

      <n-card title="关闭工单" size="small">
        <n-form ref="closeFormRef" :model="closeForm" :rules="closeRules" label-placement="left" :label-width="100">
          <n-form-item label="工单编码/Id" path="workorderNos">
            <n-input
              v-model:value="closeForm.workorderNos"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
              placeholder="输入单个或多个工单编码或Id，逗号分隔"
            />
          </n-form-item>
          <n-form-item label="备注" path="remark">
            <n-input
              v-model:value="closeForm.remark"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              placeholder="非必填，记录运维日志使用"
            />
          </n-form-item>
          <n-space>
            <n-button :loading="closeQuerying" @click="handleCloseQuery">查询</n-button>
            <n-button type="error" :loading="closeExecuting" @click="handleCloseExecute">执行关闭</n-button>
            <n-button @click="handleCloseReset">重置</n-button>
          </n-space>
        </n-form>
        <n-table v-if="closeQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
          <thead>
            <tr>
              <th>工单Id</th>
              <th>工单编码</th>
              <th>客户名称</th>
              <th>工单状态</th>
              <th>删除状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in closeQueryResult" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.app_code }}</td>
              <td>{{ item.customer_name || '-' }}</td>
              <td>
                <n-tag :type="item.work_status === 10 ? 'success' : 'default'" size="small">
                  {{ item.work_status === 10 ? '已关闭' : item.work_status }}
                </n-tag>
              </td>
              <td>
                <n-tag :type="item.deleted ? 'error' : 'success'" size="small">
                  {{ item.deleted ? '已删除' : '正常' }}
                </n-tag>
              </td>
            </tr>
          </tbody>
        </n-table>
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import { NCard, NSpace } from 'naive-ui'
import api from '@/api'

defineOptions({ name: '工单管理' })

const message = useMessage()

const deleteFormRef = ref(null)
const restoreFormRef = ref(null)
const closeFormRef = ref(null)

const deleteForm = ref({ workorderNos: '', operatorId: '', remark: '' })
const restoreForm = ref({ workorderNo: '', operatorId: '', remark: '' })
const closeForm = ref({ workorderNos: '', remark: '' })

const deleteExecuting = ref(false)
const restoreExecuting = ref(false)
const closeExecuting = ref(false)

const deleteQuerying = ref(false)
const restoreQuerying = ref(false)
const closeQuerying = ref(false)

const deleteQueryResult = ref([])
const restoreQueryResult = ref([])
const closeQueryResult = ref([])

const deleteRules = {
  workorderNos: [
    { required: true, message: '请输入工单编码或Id' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入工单编码或Id')
        const ids = value.split(',').map((s) => s.trim()).filter((s) => s.length)
        if (!ids.length) return new Error('请输入工单编码或Id')
        return true
      },
    },
  ],
  operatorId: [{ required: true, message: '请选择操作人' }],
}

const restoreRules = {
  workorderNo: [{ required: true, message: '请输入工单编码或Id' }],
  operatorId: [{ required: true, message: '请选择操作人' }],
}

const closeRules = {
  workorderNos: [
    { required: true, message: '请输入工单编码或Id' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入工单编码或Id')
        const ids = value.split(',').map((s) => s.trim()).filter((s) => s.length)
        if (!ids.length) return new Error('请输入工单编码或Id')
        return true
      },
    },
  ],
}

// 操作人远程搜索：从OA查 membership_userbaseinfo
const operatorOptions = ref([])
const operatorLoading = ref(false)
let searchTimer = null

const handleSearchOperator = (query) => {
  if (!query) {
    operatorOptions.value = []
    return
  }
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    operatorLoading.value = true
    try {
      const res = await api.searchUserCenterUsers({ keyword: query, limit: 20 })
      if (res.code === 200) {
        operatorOptions.value = (res.data || []).map((u) => ({
          label: `${u.user_name}-${u.code}-(${u.user_center_user_id})`,
          value: u.user_center_user_id,
        }))
      } else {
        operatorOptions.value = []
      }
    } catch (e) {
      operatorOptions.value = []
    } finally {
      operatorLoading.value = false
    }
  }, 300)
}

const parseIds = (text) => text.split(',').map((s) => s.trim()).filter((s) => s.length)

// --- 逻辑删除 ---
const handleDeleteReset = () => {
  deleteForm.value = { workorderNos: '', operatorId: '', remark: '' }
  deleteQueryResult.value = []
}

const handleDeleteQuery = async () => {
  const ids = parseIds(deleteForm.value.workorderNos)
  if (!ids.length) {
    message.warning('请输入工单编码或Id')
    return
  }
  deleteQuerying.value = true
  try {
    const res = await api.queryEhcfWorkorderStatus({ workorder_nos: ids })
    if (res.code === 200 || res.code === 0) {
      deleteQueryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${deleteQueryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    deleteQuerying.value = false
  }
}

const handleDeleteExecute = async () => {
  await deleteFormRef.value?.validate()
  const ids = parseIds(deleteForm.value.workorderNos)
  const operatorId = String(deleteForm.value.operatorId || '').trim()
  if (!operatorId) {
    message.warning('请选择操作人')
    return
  }
  const remark = String(deleteForm.value.remark || '').trim()

  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.warning({
      title: '确认逻辑删除',
      content: `确定要逻辑删除 ${ids.length} 个工单吗？`,
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  deleteExecuting.value = true
  try {
    const res = await api.deleteEhcfWorkorderLogical({ workorder_nos: ids, operator_id: operatorId, remark })
    if (res.code === 200 || res.code === 0) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      if (failed_ids.length > 0) {
        message.warning(res.msg || `逻辑删除完成，成功 ${success_count} 条，失败 ${failed_ids.length} 条`)
      } else {
        message.success(res.msg || `逻辑删除成功：${success_count} 条`)
      }
    } else {
      message.error(res.msg || '逻辑删除失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    deleteExecuting.value = false
  }
}

// --- 逻辑删除恢复 ---
const handleRestoreReset = () => {
  restoreForm.value = { workorderNo: '', operatorId: '', remark: '' }
  restoreQueryResult.value = []
}

const handleRestoreQuery = async () => {
  const workorderNo = String(restoreForm.value.workorderNo || '').trim()
  if (!workorderNo) {
    message.warning('请输入工单编码或Id')
    return
  }
  restoreQuerying.value = true
  try {
    const res = await api.queryEhcfWorkorderStatus({ workorder_nos: [workorderNo] })
    if (res.code === 200 || res.code === 0) {
      restoreQueryResult.value = res.data?.found_docs || []
      if (!restoreQueryResult.value.length) {
        message.warning('未找到该工单')
      } else {
        message.success('查询成功')
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    restoreQuerying.value = false
  }
}

const handleRestoreExecute = async () => {
  await restoreFormRef.value?.validate()
  restoreExecuting.value = true
  try {
    const workorderNo = String(restoreForm.value.workorderNo).trim()
    const operatorId = String(restoreForm.value.operatorId).trim()
    const remark = String(restoreForm.value.remark || '').trim()
    const res = await api.restoreEhcfWorkorderLogical({ workorder_no: workorderNo, operator_id: operatorId, remark })
    if (res.code === 200 || res.code === 0) {
      const { restored = false } = res.data || {}
      if (restored) {
        message.success(res.msg || '逻辑删除恢复成功')
      } else {
        message.warning(res.msg || '工单无需恢复')
      }
    } else {
      message.error(res.msg || '逻辑删除恢复失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    restoreExecuting.value = false
  }
}

// --- 关闭工单 ---
const handleCloseReset = () => {
  closeForm.value = { workorderNos: '', remark: '' }
  closeQueryResult.value = []
}

const handleCloseQuery = async () => {
  const ids = parseIds(closeForm.value.workorderNos)
  if (!ids.length) {
    message.warning('请输入工单编码或Id')
    return
  }
  closeQuerying.value = true
  try {
    const res = await api.queryEhcfWorkorderStatus({ workorder_nos: ids })
    if (res.code === 200 || res.code === 0) {
      closeQueryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${closeQueryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    closeQuerying.value = false
  }
}

const handleCloseExecute = async () => {
  await closeFormRef.value?.validate()
  const ids = parseIds(closeForm.value.workorderNos)
  const remark = String(closeForm.value.remark || '').trim()

  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.warning({
      title: '确认关闭工单',
      content: `确定要关闭 ${ids.length} 个工单吗？将设置 WorkStatus=10`,
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  closeExecuting.value = true
  try {
    const res = await api.closeEhcfWorkorder({ workorder_nos: ids, operator_id: '', remark })
    if (res.code === 200 || res.code === 0) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      if (failed_ids.length > 0) {
        message.warning(res.msg || `关闭完成，成功 ${success_count} 条，失败 ${failed_ids.length} 条`)
      } else {
        message.success(res.msg || `关闭成功：${success_count} 条`)
      }
    } else {
      message.error(res.msg || '关闭失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    closeExecuting.value = false
  }
}
</script>
