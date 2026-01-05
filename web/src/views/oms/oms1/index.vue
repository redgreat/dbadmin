<template>
  <CommonPage show-footer title="订单完成时间修改">
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="100">
      <n-form-item label="订单Id" path="orderIds">
        <n-input v-model:value="form.orderIds" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单Id，逗号分隔" />
      </n-form-item>
      <n-form-item label="修改时间" path="auditTime">
        <n-date-picker v-model:value="form.auditTime" type="datetime" placeholder="请选择日期时间" />
      </n-form-item>
      <n-space>
        <n-button type="primary" :loading="executing" @click="handleExecute">执行</n-button>
        <n-button @click="handleReset">重置</n-button>
      </n-space>
    </n-form>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '订单审核时间修改' })

const message = useMessage()
const formRef = ref(null)
const form = ref({ orderIds: '', auditTime: null })
const executing = ref(false)

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
  auditTime: [{ required: true, message: '请选择修改时间', trigger: ['change', 'blur'] }],
}

const handleReset = () => {
  form.value = { orderIds: '', auditTime: null }
}

const handleExecute = async () => {
  await formRef.value?.validate()
  const ids = form.value.orderIds
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length)
  executing.value = true
  try {
    const payload = { order_ids: ids, audit_time: form.value.auditTime }
    const res = await api.updateOrdersAuditTimeBatch(payload)
    if (res.code === 200) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      message.success(`执行成功：${success_count} 条${failed_ids.length ? `，失败 ${failed_ids.length} 条` : ''}`)
    } else {
      message.error(res.msg || '执行失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    executing.value = false
  }
}
</script>
