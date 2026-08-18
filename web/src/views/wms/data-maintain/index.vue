<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
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
        </n-descriptions>

        <n-divider />

        <n-form ref="updateFormRef" :model="updateForm" :rules="updateRules" label-placement="left" :label-width="100">
          <n-form-item label="修改状态" path="is_receive">
            <n-radio-group v-model:value="updateForm.is_receive">
              <n-radio :value="0">未收</n-radio>
              <n-radio :value="1">已收</n-radio>
            </n-radio-group>
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
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '仓储中心数据维护' })

const message = useMessage()

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
    { required: true, message: '请选择修改状态' },
  ],
  operatorId: [
    { required: true, message: '请选择修改人' },
  ],
}

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
      updateForm.value.is_receive = res.data.is_receive === 1 ? 0 : 1
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
