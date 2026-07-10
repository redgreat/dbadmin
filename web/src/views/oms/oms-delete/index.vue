<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="订单逻辑删除" size="small">
        <n-form ref="logicalFormRef" :model="logicalForm" :rules="rules" label-placement="left" :label-width="100">
          <n-form-item label="订单编码/Id" path="orderNos">
            <n-input v-model:value="logicalForm.orderNos" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单编码或Id，逗号分隔" />
          </n-form-item>
          <n-form-item label="删除人" path="operatorId">
            <n-select
              v-model:value="logicalForm.operatorId"
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
            <n-input v-model:value="logicalForm.remark" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="非必填，记录运维日志使用" />
          </n-form-item>
          <n-space>
            <n-button :loading="logicalQuerying" @click="handleLogicalQuery">查询</n-button>
            <n-button type="primary" :loading="logicalExecuting" @click="handleLogicalExecute">执行逻辑删除</n-button>
            <n-button @click="handleLogicalReset">重置</n-button>
          </n-space>
          <n-table v-if="logicalQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
            <thead>
              <tr>
                <th>订单Id</th>
                <th>订单编号</th>
                <th>审核时间</th>
                <th>删除状态</th>
                <th>删除人</th>
                <th>删除时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in logicalQueryResult" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.order_no }}</td>
                <td>{{ item.audit_time || '-' }}</td>
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
        </n-form>
      </n-card>

      <n-card title="订单物理删除" size="small">
        <n-form ref="physicalFormRef" :model="physicalForm" :rules="rules" label-placement="left" :label-width="100">
          <n-form-item label="订单编码/Id" path="orderNos">
            <n-input v-model:value="physicalForm.orderNos" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单编码或Id，逗号分隔" />
          </n-form-item>
          <n-form-item label="备注" path="remark">
            <n-input v-model:value="physicalForm.remark" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="非必填，记录运维日志使用" />
          </n-form-item>
          <n-space>
            <n-button :loading="physicalQuerying" @click="handlePhysicalQuery">查询</n-button>
            <n-button type="error" :loading="physicalExecuting" @click="handlePhysicalExecute">执行物理删除</n-button>
            <n-button @click="handlePhysicalReset">重置</n-button>
          </n-space>
          <n-table v-if="physicalQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
            <thead>
              <tr>
                <th>订单Id</th>
                <th>订单编号</th>
                <th>审核时间</th>
                <th>删除状态</th>
                <th>删除人</th>
                <th>删除时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in physicalQueryResult" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.order_no }}</td>
                <td>{{ item.audit_time || '-' }}</td>
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
        </n-form>
      </n-card>

      <n-card title="订单逻辑删除恢复" size="small">
        <n-form ref="restoreFormRef" :model="restoreForm" :rules="restoreRules" label-placement="left" :label-width="100">
          <n-form-item label="订单编码/Id" path="orderNo">
            <n-input v-model:value="restoreForm.orderNo" clearable placeholder="输入单个订单编码或Id" />
          </n-form-item>
          <n-form-item label="删除人" path="operatorId">
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
            <n-input v-model:value="restoreForm.remark" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="非必填，记录运维日志使用" />
          </n-form-item>
          <n-space>
            <n-button :loading="restoreQuerying" @click="handleRestoreQuery">查询</n-button>
            <n-button type="primary" :loading="restoreExecuting" @click="handleRestoreExecute">执行恢复</n-button>
            <n-button @click="handleRestoreReset">重置</n-button>
          </n-space>
          <n-table v-if="restoreQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
            <thead>
              <tr>
                <th>订单Id</th>
                <th>订单编号</th>
                <th>审核时间</th>
                <th>删除状态</th>
                <th>删除人</th>
                <th>删除时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in restoreQueryResult" :key="item.id">
                <td>{{ item.id }}</td>
                <td>{{ item.order_no }}</td>
                <td>{{ item.audit_time || '-' }}</td>
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
        </n-form>
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

defineOptions({ name: '订单删除' })

const message = useMessage()

const logicalFormRef = ref(null)
const physicalFormRef = ref(null)
const restoreFormRef = ref(null)

const logicalForm = ref({ orderNos: '', operatorId: '', remark: '' })
const physicalForm = ref({ orderNos: '', remark: '' })
const restoreForm = ref({ orderNo: '', operatorId: '', remark: '' })

const logicalExecuting = ref(false)
const physicalExecuting = ref(false)
const restoreExecuting = ref(false)

const logicalQuerying = ref(false)
const physicalQuerying = ref(false)
const restoreQuerying = ref(false)

const logicalQueryResult = ref([])
const physicalQueryResult = ref([])
const restoreQueryResult = ref([])

const rules = {
  orderNos: [
    { required: true, message: '请输入订单编码或Id' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入订单编码或Id')
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return new Error('请输入订单编码或Id')
        return true
      },
    },
  ],
}

const restoreRules = {
  orderNo: [
    { required: true, message: '请输入订单编码或Id' },
  ],
  operatorId: [
    { required: true, message: '请选择删除人' },
  ],
}

// 删除人远程搜索：从OA查 membership_userbaseinfo
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

const handleLogicalReset = () => {
  logicalForm.value = { orderNos: '', operatorId: '', remark: '' }
  logicalQueryResult.value = []
}

const handlePhysicalReset = () => {
  physicalForm.value = { orderNos: '', remark: '' }
  physicalQueryResult.value = []
}

const handleRestoreReset = () => {
  restoreForm.value = { orderNo: '', operatorId: '', remark: '' }
  restoreQueryResult.value = []
}

const handleLogicalQuery = async () => {
  const ids = parseIds(logicalForm.value.orderNos)
  if (!ids.length) {
    message.warning('请输入订单编码或Id')
    return
  }
  logicalQuerying.value = true
  try {
    const res = await api.queryOrderStatus({ order_nos: ids })
    if (res.code === 200 || res.code === 0) {
      logicalQueryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${logicalQueryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    logicalQuerying.value = false
  }
}

const handlePhysicalQuery = async () => {
  const ids = parseIds(physicalForm.value.orderNos)
  if (!ids.length) {
    message.warning('请输入订单编码或Id')
    return
  }
  physicalQuerying.value = true
  try {
    const res = await api.queryOrderStatus({ order_nos: ids })
    if (res.code === 200 || res.code === 0) {
      physicalQueryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${physicalQueryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    physicalQuerying.value = false
  }
}

const handleRestoreQuery = async () => {
  const orderNo = String(restoreForm.value.orderNo || '').trim()
  if (!orderNo) {
    message.warning('请输入订单编码或Id')
    return
  }
  restoreQuerying.value = true
  try {
    const res = await api.queryOrderStatus({ order_nos: [orderNo] })
    if (res.code === 200 || res.code === 0) {
      restoreQueryResult.value = res.data?.found_docs || []
      if (!restoreQueryResult.value.length) {
        message.warning('未找到该订单')
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

const handleLogicalExecute = async () => {
  await logicalFormRef.value?.validate()
  const ids = parseIds(logicalForm.value.orderNos)
  const operatorId = String(logicalForm.value.operatorId || '').trim()
  const remark = String(logicalForm.value.remark || '').trim()
  if (!operatorId) {
    message.warning('请选择删除人')
    return
  }
  logicalExecuting.value = true
  try {
    const res = await api.deleteOrdersLogicalBatch({ order_nos: ids, operator_id: operatorId, remark })
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
    logicalExecuting.value = false
  }
}

const handlePhysicalExecute = async () => {
  await physicalFormRef.value?.validate()
  const ids = parseIds(physicalForm.value.orderNos)
  const remark = String(physicalForm.value.remark || '').trim()
  physicalExecuting.value = true
  try {
    const res = await api.deleteOrdersPhysicalBatch({ order_nos: ids, remark })
    if (res.code === 200 || res.code === 0) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      if (failed_ids.length > 0) {
        message.warning(res.msg || `物理删除完成，成功 ${success_count} 条，失败 ${failed_ids.length} 条`)
      } else {
        message.success(res.msg || `物理删除成功：${success_count} 条`)
      }
    } else {
      message.error(res.msg || '物理删除失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    physicalExecuting.value = false
  }
}

const handleRestoreExecute = async () => {
  await restoreFormRef.value?.validate()
  restoreExecuting.value = true
  try {
    const order_no = String(restoreForm.value.orderNo).trim()
    const operator_id = String(restoreForm.value.operatorId).trim()
    const remark = String(restoreForm.value.remark || '').trim()
    const res = await api.restoreOrderLogical({ order_no, operator_id, remark })
    if (res.code === 200 || res.code === 0) {
      const { restored = false } = res.data || {}
      if (restored) {
        message.success(res.msg || '逻辑删除恢复成功')
      } else {
        message.warning(res.msg || '订单无需恢复')
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
</script>
