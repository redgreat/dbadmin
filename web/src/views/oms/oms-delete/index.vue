<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="订单逻辑删除" size="small">
        <n-form ref="logicalFormRef" :model="logicalForm" :rules="rules" label-placement="left" :label-width="100">
          <n-form-item label="订单编码" path="orderNos">
            <n-input v-model:value="logicalForm.orderNos" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单编码，逗号分隔" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="logicalExecuting" @click="handleLogicalExecute">执行逻辑删除</n-button>
            <n-button @click="handleLogicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="订单物理删除" size="small">
        <n-form ref="physicalFormRef" :model="physicalForm" :rules="rules" label-placement="left" :label-width="100">
          <n-form-item label="订单编码" path="orderNos">
            <n-input v-model:value="physicalForm.orderNos" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单编码，逗号分隔" />
          </n-form-item>
          <n-space>
            <n-button type="error" :loading="physicalExecuting" @click="handlePhysicalExecute">执行物理删除</n-button>
            <n-button @click="handlePhysicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="订单逻辑删除恢复" size="small">
        <n-form ref="restoreFormRef" :model="restoreForm" :rules="restoreRules" label-placement="left" :label-width="100">
          <n-form-item label="订单编码" path="orderNo">
            <n-input v-model:value="restoreForm.orderNo" clearable placeholder="输入单个订单编码" />
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

const logicalForm = ref({ orderNos: '' })
const physicalForm = ref({ orderNos: '' })
const restoreForm = ref({ orderNo: '', operatorId: '' })

const logicalExecuting = ref(false)
const physicalExecuting = ref(false)
const restoreExecuting = ref(false)

const rules = {
  orderNos: [
    { required: true, message: '请输入订单编码' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入订单编码')
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return new Error('请输入订单编码')
        return true
      },
    },
  ],
}

const restoreRules = {
  orderNo: [
    { required: true, message: '请输入订单编码' },
  ],
  operatorId: [
    { required: true, message: '请输入删除人Id' },
    {
      validator: (_, value) => {
        const guidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        if (!guidRegex.test(String(value || '').trim())) {
          return new Error('删除人Id需为GUID格式（如：550e8400-e29b-41d4-a716-446655440000）')
        }
        return true
      },
    },
  ],
}

const parseIds = (text) => text.split(',').map((s) => s.trim()).filter((s) => s.length)

const handleLogicalReset = () => {
  logicalForm.value = { orderNos: '' }
}

const handlePhysicalReset = () => {
  physicalForm.value = { orderNos: '' }
}

const handleRestoreReset = () => {
  restoreForm.value = { orderNo: '', operatorId: '' }
}

const handleLogicalExecute = async () => {
  await logicalFormRef.value?.validate()
  const ids = parseIds(logicalForm.value.orderNos)
  logicalExecuting.value = true
  try {
    const res = await api.deleteOrdersLogicalBatch({ order_nos: ids })
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
  physicalExecuting.value = true
  try {
    const res = await api.deleteOrdersPhysicalBatch({ order_nos: ids })
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
    const res = await api.restoreOrderLogical({ order_no, operator_id })
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
