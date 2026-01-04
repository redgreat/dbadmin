<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="订单逻辑删除" size="small">
        <n-form ref="logicalFormRef" :model="logicalForm" :rules="rules" label-placement="left" :label-width="100">
          <n-form-item label="订单Id" path="orderIds">
            <n-input v-model:value="logicalForm.orderIds" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单Id，逗号分隔" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="logicalExecuting" @click="handleLogicalExecute">执行逻辑删除</n-button>
            <n-button @click="handleLogicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="订单物理删除" size="small">
        <n-form ref="physicalFormRef" :model="physicalForm" :rules="rules" label-placement="left" :label-width="100">
          <n-form-item label="订单Id" path="orderIds">
            <n-input v-model:value="physicalForm.orderIds" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单Id，逗号分隔" />
          </n-form-item>
          <n-space>
            <n-button type="error" :loading="physicalExecuting" @click="handlePhysicalExecute">执行物理删除</n-button>
            <n-button @click="handlePhysicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="订单逻辑删除恢复" size="small">
        <n-form ref="restoreFormRef" :model="restoreForm" :rules="restoreRules" label-placement="left" :label-width="100">
          <n-form-item label="订单Id" path="orderId">
            <n-input v-model:value="restoreForm.orderId" clearable placeholder="输入单个订单Id" />
          </n-form-item>
          <n-form-item label="删除人Id" path="operatorId">
            <n-input v-model:value="restoreForm.operatorId" clearable placeholder="输入删除人Id" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="restoreExecuting" @click="handleRestoreExecute">执行恢复</n-button>
            <n-button @click="handleRestoreReset">重置</n-button>
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
import { NCard, NSpace } from 'naive-ui'
import api from '@/api'

defineOptions({ name: '订单删除' })

const message = useMessage()

const logicalFormRef = ref(null)
const physicalFormRef = ref(null)
const restoreFormRef = ref(null)

const logicalForm = ref({ orderIds: '' })
const physicalForm = ref({ orderIds: '' })
const restoreForm = ref({ orderId: '', operatorId: '' })

const logicalExecuting = ref(false)
const physicalExecuting = ref(false)
const restoreExecuting = ref(false)

const rules = {
  orderIds: [
    { required: true, message: '请输入订单Id', trigger: ['blur', 'input'] },
    {
      validator: (_, value) => {
        if (!value) return false
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return false
        const allNumeric = ids.every((s) => /^\d+$/.test(s))
        return allNumeric || '订单Id需为数字，逗号分隔'
      },
      trigger: ['blur', 'input'],
    },
  ],
}

const restoreRules = {
  orderId: [
    { required: true, message: '请输入订单Id', trigger: ['blur', 'input'] },
    {
      validator: (_, value) => /^\d+$/.test(String(value || '').trim()) || '订单Id需为数字',
      trigger: ['blur', 'input'],
    },
  ],
  operatorId: [
    { required: true, message: '请输入删除人Id', trigger: ['blur', 'input'] },
    {
      validator: (_, value) => /^\d+$/.test(String(value || '').trim()) || '删除人Id需为数字',
      trigger: ['blur', 'input'],
    },
  ],
}

const parseIds = (text) => text.split(',').map((s) => s.trim()).filter((s) => s.length)

const handleLogicalReset = () => {
  logicalForm.value = { orderIds: '' }
}

const handlePhysicalReset = () => {
  physicalForm.value = { orderIds: '' }
}

const handleRestoreReset = () => {
  restoreForm.value = { orderId: '', operatorId: '' }
}

const handleLogicalExecute = async () => {
  await logicalFormRef.value?.validate()
  const ids = parseIds(logicalForm.value.orderIds)
  logicalExecuting.value = true
  try {
    const res = await api.deleteOrdersLogicalBatch({ order_ids: ids })
    if (res.code === 0) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      message.success(`逻辑删除成功：${success_count} 条${failed_ids.length ? `，失败 ${failed_ids.length} 条` : ''}`)
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
  const ids = parseIds(physicalForm.value.orderIds)
  physicalExecuting.value = true
  try {
    const res = await api.deleteOrdersPhysicalBatch({ order_ids: ids })
    if (res.code === 0) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      message.success(`物理删除成功：${success_count} 条${failed_ids.length ? `，失败 ${failed_ids.length} 条` : ''}`)
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
    const order_id = parseInt(String(restoreForm.value.orderId).trim(), 10)
    const operator_id = parseInt(String(restoreForm.value.operatorId).trim(), 10)
    const res = await api.restoreOrderLogical({ order_id, operator_id })
    if (res.code === 200) {
      message.success('逻辑删除恢复成功')
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
