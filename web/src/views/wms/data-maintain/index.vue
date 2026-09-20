<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="出入库内部交易状态修改(InSideDealState)" size="small">
        <n-form ref="insideDealFormRef" :model="insideDealForm" label-placement="left" :label-width="120">
          <n-form-item label="出入库单号/Id" path="stockNos">
            <n-input
              v-model:value="insideDealForm.stockNos"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              placeholder="输入单个或多个出入库单号或Id，逗号分隔"
            />
          </n-form-item>
          <n-space>
            <n-button :loading="insideDealQuerying" @click="handleInsideDealQuery">查询</n-button>
            <n-button @click="handleInsideDealReset">重置</n-button>
          </n-space>
        </n-form>
        <n-table v-if="insideDealQueryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
          <thead>
            <tr>
              <th>单据Id</th>
              <th>单据编号</th>
              <th>单据类型</th>
              <th>数据来源</th>
              <th>当前InSideDealState</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in insideDealQueryResult" :key="item.stock_id">
              <td>{{ item.stock_id }}</td>
              <td>{{ item.stock_no }}</td>
              <td>{{ item.doc_type === 'instock' ? '入库单' : '出库单' }}</td>
              <td>{{ item.table_type === 'main' ? '主表' : '历史表' }}</td>
              <td>
                <n-tag :type="item.inside_deal_state !== '' ? 'info' : 'default'" size="small">
                  {{ item.inside_deal_state !== '' ? item.inside_deal_state : '-' }}
                </n-tag>
              </td>
              <td>
                <n-button size="small" type="primary" @click="handleOpenInsideDealEdit(item)">修改</n-button>
              </td>
            </tr>
          </tbody>
        </n-table>
      </n-card>

      <n-card title="仓储应收状态变更" size="small">
        <n-form ref="queryFormRef" :model="queryForm" :rules="queryRules" label-placement="left" :label-width="100">
          <n-form-item label="出库单号" path="out_stock_no">
            <n-input v-model:value="queryForm.out_stock_no" clearable placeholder="输入出库单号或ID" />
          </n-form-item>
          <n-space>
            <n-button :loading="querying" @click="handleQuery">查询</n-button>
            <n-button @click="handleReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card v-if="queryResult" title="出库单信息" size="small">
        <n-descriptions :column="2" label-placement="left" bordered size="small">
          <n-descriptions-item label="出库单ID">
            {{ queryResult.id }}
          </n-descriptions-item>
          <n-descriptions-item label="出库单号">
            {{ queryResult.out_stock_no }}
          </n-descriptions-item>
          <n-descriptions-item label="出库类型">
            {{ queryResult.out_stock_type || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="仓库名称">
            {{ queryResult.warehouse_name || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="目标仓库">
            {{ queryResult.to_warehouse_name || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="审核时间">
            {{ queryResult.audit_time || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="应收状态">
            <n-tag :type="queryResult.is_receive === 1 ? 'success' : 'warning'" size="small">
              {{ queryResult.is_receive === 1 ? '已收' : '未收' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="数据来源">
            <n-tag :type="queryResult.source_table === 'main' ? 'info' : 'default'" size="small">
              {{ queryResult.source_table === 'main' ? '主表' : '历史表' }}
            </n-tag>
          </n-descriptions-item>
        </n-descriptions>

        <n-divider />

        <n-form ref="updateFormRef" :model="updateForm" :rules="updateRules" label-placement="left" :label-width="100">
          <n-form-item label="修改状态" path="is_receive">
            <n-input-number
              v-model:value="updateForm.is_receive"
              :min="0"
              :max="999"
              placeholder="请输入IsReceive值"
              style="width: 200px"
            />
            <span class="ml-2 text-gray-500 text-sm">0-未收, 1-已收</span>
          </n-form-item>
          <n-form-item label="修改人" path="operatorId">
            <n-select
              v-model:value="updateForm.operatorId"
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
            <n-input v-model:value="updateForm.remark" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="非必填，记录运维日志使用" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="updating" @click="handleUpdate">提交修改</n-button>
          </n-space>
        </n-form>
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage, useDialog } from 'naive-ui'
import { NInputNumber } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import { h } from 'vue'
import api from '@/api'

defineOptions({ name: '仓储中心数据维护' })

const message = useMessage()
const dialog = useDialog()

// --- 出入库内部交易状态 ---
const insideDealFormRef = ref(null)
const insideDealForm = ref({ stockNos: '' })
const insideDealQuerying = ref(false)
const insideDealQueryResult = ref([])

const queryFormRef = ref(null)
const updateFormRef = ref(null)

const queryForm = ref({ out_stock_no: '' })
const updateForm = ref({ is_receive: 1, operatorId: '', remark: '' })

const querying = ref(false)
const updating = ref(false)

const queryResult = ref(null)

const operatorOptions = ref([])
const operatorLoading = ref(false)
let searchTimer = null

const queryRules = {
  out_stock_no: [
    { required: true, message: '请输入出库单号或ID' },
  ],
}

const updateRules = {
  is_receive: [
    { required: true, message: '请输入IsReceive值' },
  ],
  operatorId: [
    { required: true, message: '请选择修改人' },
  ],
}

const parseStockNos = (text) => text.split(',').map((s) => s.trim()).filter((s) => s.length)

// --- 出入库内部交易状态 ---
const handleInsideDealReset = () => {
  insideDealForm.value = { stockNos: '' }
  insideDealQueryResult.value = []
}

const handleInsideDealQuery = async () => {
  const nos = parseStockNos(insideDealForm.value.stockNos)
  if (!nos.length) {
    message.warning('请输入出入库单号或Id')
    return
  }
  insideDealQuerying.value = true
  try {
    const res = await api.queryWmsInsideDealState({ stock_nos: nos })
    if (res.code === 200 || res.code === 0) {
      insideDealQueryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${insideDealQueryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    insideDealQuerying.value = false
  }
}

const handleOpenInsideDealEdit = (item) => {
  const newInsideDealState = ref(item.inside_deal_state !== '' ? Number(item.inside_deal_state) : 1)
  const remark = ref('')
  const dialogInstance = dialog.create({
    title: '修改内部交易状态(InSideDealState)',
    content: () =>
      h('div', { style: 'display: flex; flex-direction: column; gap: 12px;' }, [
        h('div', {}, `${item.doc_type === 'instock' ? '入库单' : '出库单'} ${item.stock_no} 当前 InSideDealState: ${item.inside_deal_state}`),
        h('div', { style: 'display: flex; align-items: center; gap: 8px;' }, [
          h('span', {}, '新值:'),
          h(NInputNumber, {
            value: newInsideDealState.value,
            'onUpdate:value': (v) => {
              newInsideDealState.value = v
            },
            min: 0,
            max: 999,
            style: 'width: 120px;',
            placeholder: '默认1',
          }),
        ]),
      ]),
    positiveText: '确认修改',
    negativeText: '取消',
    onPositiveClick: async () => {
      if (newInsideDealState.value === null || newInsideDealState.value === undefined) {
        message.warning('请输入InSideDealState值')
        return false
      }
      try {
        const res = await api.updateWmsInsideDealState({
          stock_no: item.stock_no,
          inside_deal_state: Number(newInsideDealState.value),
          remark: remark.value,
        })
        if (res.code === 200 || res.code === 0) {
          message.success(res.msg || '修改成功')
          // 刷新查询结果
          handleInsideDealQuery()
        } else {
          message.error(res.msg || '修改失败')
          return false
        }
      } catch (e) {
        message.error('请求异常')
        return false
      }
    },
  })
}

// --- 应收状态变更 ---
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

const handleQuery = async () => {
  try {
    await queryFormRef.value?.validate()
  } catch (e) {
    return
  }

  const input = String(queryForm.value.out_stock_no || '').trim()
  if (!input) {
    message.warning('请输入出库单号或ID')
    return
  }

  querying.value = true
  try {
    const isNumeric = /^\d+$/.test(input)
    const res = await api.queryOwingStatus({
      out_stock_no: isNumeric ? '' : input,
      stock_id: isNumeric ? input : '',
    })
    if (res.code === 200 || res.code === 0) {
      queryResult.value = res.data
      updateForm.value.is_receive = 1
      message.success('查询成功')
    } else {
      message.error(res.msg || '查询失败')
      queryResult.value = null
    }
  } catch (e) {
    message.error('请求异常')
    queryResult.value = null
  } finally {
    querying.value = false
  }
}

const handleReset = () => {
  queryForm.value = { out_stock_no: '' }
  updateForm.value = { is_receive: 1, operatorId: '', remark: '' }
  queryResult.value = null
  operatorOptions.value = []
}

const handleUpdate = async () => {
  if (!queryResult.value) {
    message.warning('请先查询出库单')
    return
  }

  try {
    await updateFormRef.value?.validate()
  } catch (e) {
    return
  }

  updating.value = true
  try {
    const res = await api.updateOwingStatus({
      stock_id: queryResult.value.id,
      is_receive: updateForm.value.is_receive,
      operator_id: String(updateForm.value.operatorId).trim(),
      source_table: queryResult.value.source_table || 'main',
      remark: String(updateForm.value.remark || '').trim(),
    })
    if (res.code === 200 || res.code === 0) {
      message.success(res.msg || '修改成功')
      queryResult.value.is_receive = updateForm.value.is_receive
    } else {
      message.error(res.msg || '修改失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    updating.value = false
  }
}
</script>
