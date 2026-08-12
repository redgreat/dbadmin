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
              <th>工单类型</th>
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
              <td>{{ item.order_type_name || item.order_type || '-' }}</td>
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
              <th>工单类型</th>
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
              <td>{{ item.order_type_name || item.order_type || '-' }}</td>
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
              <th>工单类型</th>
              <th>客户名称</th>
              <th>工单状态</th>
              <th>删除状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in closeQueryResult" :key="item.id">
              <td>{{ item.id }}</td>
              <td>{{ item.app_code }}</td>
              <td>{{ item.order_type_name || item.order_type || '-' }}</td>
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
import { h, ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import { NCard, NButton, NInput, NSpace } from 'naive-ui'
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

const handleDeleteResult = (res) => {
  if (res.code === 200 || res.code === 0) {
    const { success_count = 0, failed_ids = [], remark_failed_ids = [] } = res.data || {}
    if (remark_failed_ids.length > 0) {
      message.warning(
        res.msg ||
          `删除成功 ${success_count} 条，但备注写入失败 ${
            remark_failed_ids.length
          } 条：${remark_failed_ids.join(', ')}`
      )
    } else if (failed_ids.length > 0) {
      message.warning(
        res.msg || `逻辑删除完成，成功 ${success_count} 条，失败 ${failed_ids.length} 条`
      )
    } else {
      message.success(res.msg || `逻辑删除成功：${success_count} 条`)
    }
  } else {
    message.error(res.msg || '逻辑删除失败')
  }
}

const formatMultiDocs = (multiDocs) =>
  (multiDocs || [])
    .map((group) => {
      const docLines = (group.docs || [])
        .map(
          (d) =>
            `  · ${d.workorder_id || d.id}（${d.order_type_name || d.order_type || '未知类型'}）`
        )
        .join('\n')
      return `工单编码 ${group.input} 对应 ${group.docs.length} 条工单记录：\n${docLines}`
    })
    .join('\n\n')

// 不全部处理时，让用户输入具体工单Id
const askSpecificWorkorderIds = ({
  allIds = [],
  title = '请输入工单Id',
  placeholder = '输入具体工单Id，逗号分隔',
} = {}) =>
  new Promise((resolve) => {
    let settled = false
    const settle = (v) => {
      if (!settled) {
        settled = true
        resolve(v)
      }
    }
    const inputValue = ref(allIds.join(','))
    const dialog = window.$dialog.warning({
      title,
      content: () =>
        h(NInput, {
          value: inputValue.value,
          'onUpdate:value': (v) => {
            inputValue.value = v
          },
          type: 'textarea',
          autosize: { minRows: 3, maxRows: 6 },
          placeholder,
        }),
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => {
        const ids = parseIds(inputValue.value)
        if (!ids.length) {
          message.warning('请输入至少一个工单Id')
          settle(null)
        } else {
          settle({ workorder_ids: ids })
        }
        dialog.destroy()
      },
      onNegativeClick: () => {
        settle(null)
        dialog.destroy()
      },
      onClose: () => settle(null),
      onMaskClick: () => settle(null),
    })
  })

// 同一编码对应多条工单时，确认处理范围（全部/指定/取消）
const confirmMultiAction = (data, options = {}) =>
  new Promise((resolve) => {
    const {
      title = '存在多条工单记录，请确认处理范围',
      prompt = '是否全部处理？如不全部处理，请点击「指定处理」并输入具体工单Id。',
      allLabel = '全部处理',
      allPayload = { all: true },
      specificLabel = '指定处理',
      specificTitle = '请输入工单Id',
      specificPlaceholder = '输入具体工单Id，逗号分隔',
    } = options
    let settled = false
    const settle = (v) => {
      if (!settled) {
        settled = true
        resolve(v)
      }
    }
    const dialog = window.$dialog.warning({
      title,
      content: `${formatMultiDocs(data.multi_docs)}\n\n${prompt}`,
      action: () =>
        h(
          NSpace,
          { justify: 'end' },
          {
            default: () => [
              h(
                NButton,
                {
                  onClick: () => {
                    dialog.destroy()
                    settle(null)
                  },
                },
                { default: () => '取消' }
              ),
              h(
                NButton,
                {
                  onClick: () => {
                    dialog.destroy()
                    askSpecificWorkorderIds({
                      allIds: data.all_ids || [],
                      title: specificTitle,
                      placeholder: specificPlaceholder,
                    }).then(settle)
                  },
                },
                { default: () => specificLabel }
              ),
              h(
                NButton,
                {
                  type: 'primary',
                  onClick: () => {
                    dialog.destroy()
                    settle(allPayload)
                  },
                },
                { default: () => allLabel }
              ),
            ],
          }
        ),
      onClose: () => settle(null),
      onMaskClick: () => settle(null),
    })
  })

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
      content: '确定要逻辑删除这些工单吗？',
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  deleteExecuting.value = true
  try {
    const basePayload = { workorder_nos: ids, operator_id: operatorId, remark }
    const res = await api.deleteEhcfWorkorderLogical(basePayload)
    if (res.code !== 200 && res.code !== 0) {
      message.error(res.msg || '逻辑删除失败')
      return
    }
    if (res.data?.need_confirm) {
      // 存在一对多工单，需要用户确认是否全部删除
      const choice = await confirmMultiAction(res.data, {
        title: '存在多条工单记录，请确认删除范围',
        prompt: '是否全部删除？如不全部删除，请点击「指定删除」并输入具体工单Id。',
        allLabel: '全部删除',
        allPayload: { delete_all: true },
        specificLabel: '指定删除',
        specificTitle: '请输入要删除的工单Id',
        specificPlaceholder: '输入要删除的具体工单Id，逗号分隔',
      })
      if (!choice) return
      const res2 = await api.deleteEhcfWorkorderLogical({ ...basePayload, ...choice })
      handleDeleteResult(res2)
      return
    }
    handleDeleteResult(res)
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

const handleRestoreResult = (res) => {
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
}

const handleRestoreExecute = async () => {
  await restoreFormRef.value?.validate()
  const workorderNo = String(restoreForm.value.workorderNo).trim()
  const operatorId = String(restoreForm.value.operatorId).trim()
  if (!operatorId) {
    message.warning('请选择操作人')
    return
  }
  const remark = String(restoreForm.value.remark || '').trim()

  restoreExecuting.value = true
  try {
    const basePayload = { workorder_no: workorderNo, operator_id: operatorId, remark }
    const res = await api.restoreEhcfWorkorderLogical(basePayload)
    if (res.code !== 200 && res.code !== 0) {
      message.error(res.msg || '逻辑删除恢复失败')
      return
    }
    if (res.data?.need_confirm) {
      // 同一编码对应多条已删除工单，需要用户确认是否全部恢复
      const choice = await confirmMultiAction(res.data, {
        title: '存在多条已删除工单，请确认恢复范围',
        prompt: '是否全部恢复？如不全部恢复，请点击「指定恢复」并输入具体工单Id。',
        allLabel: '全部恢复',
        allPayload: { restore_all: true },
        specificLabel: '指定恢复',
        specificTitle: '请输入要恢复的工单Id',
        specificPlaceholder: '输入要恢复的具体工单Id，逗号分隔',
      })
      if (!choice) return
      const res2 = await api.restoreEhcfWorkorderLogical({ ...basePayload, ...choice })
      handleRestoreResult(res2)
      return
    }
    handleRestoreResult(res)
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

const handleCloseResult = (res) => {
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
}

const handleCloseExecute = async () => {
  await closeFormRef.value?.validate()
  const ids = parseIds(closeForm.value.workorderNos)
  const remark = String(closeForm.value.remark || '').trim()

  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.warning({
      title: '确认关闭工单',
      content: '确定要关闭这些工单吗？将设置 WorkStatus=10',
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  closeExecuting.value = true
  try {
    const basePayload = { workorder_nos: ids, operator_id: '', remark }
    const res = await api.closeEhcfWorkorder(basePayload)
    if (res.code !== 200 && res.code !== 0) {
      message.error(res.msg || '关闭失败')
      return
    }
    if (res.data?.need_confirm) {
      // 同一编码对应多条工单，需要用户确认是否全部关闭
      const choice = await confirmMultiAction(res.data, {
        title: '存在多条工单记录，请确认关闭范围',
        prompt: '是否全部关闭？如不全部关闭，请点击「指定关闭」并输入具体工单Id。',
        allLabel: '全部关闭',
        allPayload: { close_all: true },
        specificLabel: '指定关闭',
        specificTitle: '请输入要关闭的工单Id',
        specificPlaceholder: '输入要关闭的具体工单Id，逗号分隔',
      })
      if (!choice) return
      const res2 = await api.closeEhcfWorkorder({ ...basePayload, ...choice })
      handleCloseResult(res2)
      return
    }
    handleCloseResult(res)
  } catch (e) {
    message.error('请求异常')
  } finally {
    closeExecuting.value = false
  }
}
</script>
