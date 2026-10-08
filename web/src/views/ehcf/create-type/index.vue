<template>
  <CommonPage show-footer>
    <n-card title="修改单据来源(CreateType)" size="small">
      <n-alert type="info" :show-icon="true" class="mb-3">
        仅充电桩单据（服务商编码 1067）允许修改单据来源，其他服务商单据会被拒绝。
      </n-alert>
      <n-form
        ref="createTypeFormRef"
        :model="createTypeForm"
        :rules="createTypeRules"
        label-placement="left"
        :label-width="100"
      >
        <n-form-item label="工单编码/Id" path="workorderNos">
          <n-input
            v-model:value="createTypeForm.workorderNos"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="输入单个或多个工单编码或Id，逗号分隔"
          />
        </n-form-item>
        <n-form-item label="目标CreateType" path="newCreateType">
          <n-input-number
            v-model:value="createTypeForm.newCreateType"
            :min="0"
            :max="999"
            placeholder="默认 3"
            style="width: 200px"
          />
        </n-form-item>
        <n-form-item label="操作人" path="operatorId">
          <n-select
            v-model:value="createTypeForm.operatorId"
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
            v-model:value="createTypeForm.remark"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="非必填，记录运维日志使用"
          />
        </n-form-item>
        <n-space>
          <n-button :loading="createTypeQuerying" @click="handleCreateTypeQuery">查询</n-button>
          <n-button
            type="primary"
            :loading="createTypeExecuting"
            :disabled="!createTypeQueryResult.length"
            @click="handleCreateTypeBatchUpdate"
          >
            执行修改
          </n-button>
          <n-button @click="handleCreateTypeReset">重置</n-button>
        </n-space>
      </n-form>
      <n-table
        v-if="createTypeQueryResult.length"
        :bordered="false"
        :single-line="false"
        size="small"
        class="mt-3"
      >
        <thead>
          <tr>
            <th>工单Id</th>
            <th>申请编码</th>
            <th>客户名称</th>
            <th>工单类型</th>
            <th>服务商</th>
            <th>当前CreateType</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in createTypeQueryResult" :key="item.workorder_id">
            <td>{{ item.workorder_id }}</td>
            <td>{{ item.app_code }}</td>
            <td>{{ item.customer_name || '-' }}</td>
            <td>{{ item.order_type_name || item.order_type || '-' }}</td>
            <td>
              <n-tag :type="item.allow_modify ? 'success' : 'error'" size="small">
                {{
                  item.allow_modify ? '充电桩' : `非充电桩(${item.service_provider_code || '空'})`
                }}
              </n-tag>
            </td>
            <td>
              <n-tag :type="item.create_type !== '' ? 'info' : 'default'" size="small">
                {{ item.create_type !== '' ? item.create_type : '-' }}
              </n-tag>
            </td>
          </tr>
        </tbody>
      </n-table>
    </n-card>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '修改单据来源' })

const message = useMessage()

const createTypeFormRef = ref(null)
const createTypeForm = ref({ workorderNos: '', newCreateType: 3, operatorId: '', remark: '' })
const createTypeExecuting = ref(false)
const createTypeQuerying = ref(false)
const createTypeQueryResult = ref([])

const createTypeRules = {
  workorderNos: [
    { required: true, message: '请输入工单编码或Id' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入工单编码或Id')
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return new Error('请输入工单编码或Id')
        return true
      },
    },
  ],
  newCreateType: [{ required: true, message: '请输入目标CreateType值' }],
  operatorId: [{ required: true, message: '请选择操作人' }],
}

// 操作人远程搜索：从用户中心查 membership_userbaseinfo
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

const parseIds = (text) =>
  text
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length)

const handleCreateTypeReset = () => {
  createTypeForm.value = { workorderNos: '', newCreateType: 3, operatorId: '', remark: '' }
  createTypeQueryResult.value = []
}

const handleCreateTypeQuery = async () => {
  const ids = parseIds(createTypeForm.value.workorderNos)
  if (!ids.length) {
    message.warning('请输入工单编码或Id')
    return
  }
  createTypeQuerying.value = true
  try {
    const res = await api.queryEhcfChargingPileCreateType({ workorder_nos: ids })
    if (res.code === 200 || res.code === 0) {
      createTypeQueryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${createTypeQueryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    createTypeQuerying.value = false
  }
}

const handleCreateTypeBatchUpdate = async () => {
  if (!createTypeQueryResult.value?.length) {
    message.warning('请先查询出可修改的工单')
    return
  }
  try {
    await createTypeFormRef.value?.validate()
  } catch {
    message.warning('请填写完整：工单编码、目标来源、操作人')
    return
  }
  // 仅充电桩单据（ServiceProviderCode=1067）可修改
  const forbidden = createTypeQueryResult.value.filter((item) => !item.allow_modify)
  if (forbidden.length) {
    message.error(
      `以下 ${forbidden.length} 条非充电桩单据不可修改，请移除后重试：${forbidden
        .map((item) => item.workorder_id)
        .join(', ')}`
    )
    return
  }
  createTypeExecuting.value = true
  let ok = 0
  let already = 0
  let fail = 0
  for (const item of createTypeQueryResult.value) {
    try {
      const res = await api.updateEhcfChargingPileCreateType({
        workorder_no: item.workorder_id,
        create_type: Number(createTypeForm.value.newCreateType),
        operator_id: createTypeForm.value.operatorId || '',
        remark: createTypeForm.value.remark || '',
      })
      if (res?.data?.already_updated) {
        already += 1
      } else {
        ok += 1
      }
    } catch {
      fail += 1
    }
  }
  createTypeExecuting.value = false
  if (already) {
    message.success(`修改完成：成功 ${ok} 条（其中 ${already} 条已是目标值，无需修改），失败 ${fail} 条`)
  } else {
    message.success(`修改完成：成功 ${ok} 条，失败 ${fail} 条`)
  }
  handleCreateTypeQuery()
}
</script>
