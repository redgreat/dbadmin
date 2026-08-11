<template>
  <CommonPage show-footer>
    <n-card title="工单查询" class="mb-4">
      <n-form label-placement="left" label-align="left" :label-width="100">
        <n-form-item label="工单编码/Id">
          <n-input v-model:value="keyword" placeholder="请输入工单AppCode或Id" clearable @keydown="handleKeywordEnter" />
        </n-form-item>
      </n-form>
      <div class="mt-4">
        <n-space>
          <n-button type="primary" :loading="querying" @click="handleQuery">
            <TheIcon icon="material-symbols:search" :size="16" class="mr-2" />
            查询工单
          </n-button>
        </n-space>
      </div>

      <div v-if="workorder" class="mt-4">
        <n-card title="工单基础信息" size="small">
          <n-descriptions label-placement="left" :column="2" bordered>
            <n-descriptions-item label="工单编码">{{ workorder.app_code }}</n-descriptions-item>
            <n-descriptions-item label="工单Id">{{ workorder.id }}</n-descriptions-item>
            <n-descriptions-item label="VIN码">{{ workorder.vin_number || '-' }}</n-descriptions-item>
            <n-descriptions-item label="订单类型">{{ workorder.order_type_name }}</n-descriptions-item>
            <n-descriptions-item label="状态类型">{{ workorder.status_type_name }}</n-descriptions-item>
            <n-descriptions-item label="工单状态">
              <n-tag :type="workorder.work_status === 9 ? 'success' : 'default'" size="small">
                {{ workorder.work_status === 9 ? '已完成(9)' : workorder.work_status }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="关闭状态">{{ workorder.close_status_name }}</n-descriptions-item>
            <n-descriptions-item label="客户名称" :span="2">{{ workorder.customer_name }}</n-descriptions-item>
          </n-descriptions>

          <n-alert v-if="workorder.work_status === 9" type="warning" class="mt-3">
            该工单已完成（WorkStatus=9），不允许执行订单ID重新生成操作
          </n-alert>
        </n-card>
      </div>
    </n-card>

    <n-card v-if="workorder" title="订单ID重新生成" class="mb-4">
      <n-form label-placement="left" label-align="left" :label-width="100">
        <n-form-item label="原因备注">
          <n-input
            v-model:value="remark"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="请填写操作原因，此操作不可逆"
          />
        </n-form-item>
      </n-form>
      <n-space>
        <n-button
          type="warning"
          :loading="fixing"
          :disabled="workorder.work_status === 9"
          @click="handleFixDetail"
        >
          <TheIcon icon="material-symbols:build" :size="16" class="mr-2" />
          修复订单明细Id
        </n-button>
        <n-button
          type="error"
          :loading="regenerating"
          :disabled="workorder.work_status === 9"
          @click="handleRegenerateOrder"
        >
          <TheIcon icon="material-symbols:refresh" :size="16" class="mr-2" />
          更新订单Id和订单明细Id
        </n-button>
      </n-space>
      <n-text depth="3" class="mt-2">注意：此操作为不可逆操作，执行后无法恢复旧值</n-text>

      <!-- 修复结果 -->
      <n-card v-if="fixResult" title="修复结果" size="small" class="mt-4">
        <n-alert :type="fixResult.success ? 'success' : 'error'" class="mb-3">
          {{ fixResult.message }}
        </n-alert>
        <n-table v-if="fixResult.results?.updated?.length" :bordered="false" :single-line="false" size="small">
          <thead>
            <tr>
              <th>表名</th>
              <th>行Id</th>
              <th>旧值</th>
              <th>新值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in fixResult.results.updated" :key="idx">
              <td>{{ item.table }}</td>
              <td>{{ item.id || '-' }}</td>
              <td>{{ item.old }}</td>
              <td>{{ item.new }}</td>
            </tr>
          </tbody>
        </n-table>
      </n-card>

      <!-- 重新生成结果 -->
      <n-card v-if="regenResult" title="重新生成结果" size="small" class="mt-4">
        <n-alert :type="regenResult.success ? 'success' : 'error'" class="mb-3">
          {{ regenResult.message }}
        </n-alert>
        <div v-if="regenResult.summary" class="mb-3">
          <n-tag type="info" class="mr-2">新OI: {{ regenResult.summary.new_oi_id }}</n-tag>
          <n-tag type="info" class="mr-2">新订单编码: {{ regenResult.summary.new_order_no }}</n-tag>
          <n-tag type="info">新OE: {{ regenResult.summary.new_oe_id }}</n-tag>
        </div>
        <n-table v-if="regenResult.results?.updated?.length" :bordered="false" :single-line="false" size="small">
          <thead>
            <tr>
              <th>表名</th>
              <th>行Id</th>
              <th>字段</th>
              <th>旧值</th>
              <th>新值</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in regenResult.results.updated" :key="idx">
              <td>{{ item.table }}</td>
              <td>{{ item.id || '-' }}</td>
              <td>{{ item.field || '-' }}</td>
              <td>{{ item.old }}</td>
              <td>{{ item.new }}</td>
            </tr>
          </tbody>
        </n-table>
        <div v-if="regenResult.results?.failed?.length" class="mt-3">
          <n-text type="error" strong>失败项：</n-text>
          <n-table :bordered="false" :single-line="false" size="small" class="mt-2">
            <thead>
              <tr>
                <th>表名</th>
                <th>行Id</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in regenResult.results.failed" :key="'f' + idx">
                <td>{{ item.table }}</td>
                <td>{{ item.id || '-' }}</td>
                <td>{{ item.error }}</td>
              </tr>
            </tbody>
          </n-table>
        </div>
      </n-card>
    </n-card>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import api from '@/api'

defineOptions({ name: '订单ID重新生成' })

const message = useMessage()

const keyword = ref('')
const remark = ref('')
const querying = ref(false)
const fixing = ref(false)
const regenerating = ref(false)

const workorder = ref(null)
const fixResult = ref(null)
const regenResult = ref(null)

const handleKeywordEnter = (e) => {
  if (e.key === 'Enter') handleQuery()
}

const handleQuery = async () => {
  if (!keyword.value.trim()) {
    message.warning('请输入工单编码或Id')
    return
  }
  querying.value = true
  fixResult.value = null
  regenResult.value = null
  remark.value = ''
  try {
    const res = await api.queryEhcfWorkorder({ keyword: keyword.value.trim() })
    if (res.code === 200 && res.data.found) {
      workorder.value = res.data.workorder
      message.success('查询成功')
    } else {
      workorder.value = null
      message.warning(res.data?.message || '未找到工单')
    }
  } catch (e) {
    workorder.value = null
    message.error('查询失败')
  } finally {
    querying.value = false
  }
}

const handleFixDetail = async () => {
  if (!workorder.value?.id) {
    message.warning('请先查询工单')
    return
  }
  if (workorder.value.work_status === 9) {
    message.error('工单已完成（WorkStatus=9），不可操作')
    return
  }

  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.error({
      title: '确认修复（不可逆操作）',
      content: `将为工单「${workorder.value.app_code}」生成新的OE编号并更新所有明细Id。

此操作不可逆转，原有订单明细Id将被永久替换为新的OE编号，无法恢复！
${remark.value ? `\n原因备注：${remark.value}` : ''}`,
      positiveText: '确认操作',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  fixing.value = true
  regenResult.value = null
  try {
    const res = await api.fixEhcfDetailId({
      workorder_id: workorder.value.id,
      remark: remark.value,
    })
    if (res.code === 200) {
      fixResult.value = res.data
      message.success(res.data.message)
    } else {
      message.error(res.msg || '修复失败')
    }
  } catch (e) {
    message.error('修复失败')
  } finally {
    fixing.value = false
  }
}

const handleRegenerateOrder = async () => {
  if (!workorder.value?.id) {
    message.warning('请先查询工单')
    return
  }
  if (workorder.value.work_status === 9) {
    message.error('工单已完成（WorkStatus=9），不可操作')
    return
  }

  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.error({
      title: '确认重新生成（不可逆操作）',
      content: `将为工单「${workorder.value.app_code}」重新生成OI订单编号和订单编码，更新所有关联表。

此操作不可逆转，原有订单Id、订单编码、明细Id将被永久替换，无法恢复！
${remark.value ? `\n原因备注：${remark.value}` : ''}`,
      positiveText: '确认操作',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  regenerating.value = true
  fixResult.value = null
  try {
    const res = await api.regenerateEhcfOrderId({
      workorder_id: workorder.value.id,
      remark: remark.value,
    })
    if (res.code === 200) {
      regenResult.value = res.data
      message.success(res.data.message)
    } else {
      message.error(res.msg || '重新生成失败')
    }
  } catch (e) {
    message.error('重新生成失败')
  } finally {
    regenerating.value = false
  }
}
</script>
