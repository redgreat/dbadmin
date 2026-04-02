<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="单据逻辑删除" size="small">
        <n-form ref="logicalFormRef" :model="logicalForm" :rules="logicalRules" label-placement="left" :label-width="100">
          <n-form-item label="单据编码" path="stock_nos">
            <n-input v-model:value="logicalForm.stock_nos" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个单据编码，逗号分隔" />
          </n-form-item>
          <n-form-item label="操作人Id" path="operatorId">
            <n-input v-model:value="logicalForm.operatorId" clearable placeholder="输入操作人Id" />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="logicalExecuting" @click="handleLogicalExecute">执行逻辑删除</n-button>
            <n-button @click="handleLogicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="单据物理删除" size="small">
        <n-form ref="physicalFormRef" :model="physicalForm" :rules="physicalRules" label-placement="left" :label-width="100">
          <n-form-item label="单据编码" path="stock_nos">
            <n-input v-model:value="physicalForm.stock_nos" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个单据编码，逗号分隔" />
          </n-form-item>
          <n-space>
            <n-button type="error" :loading="physicalExecuting" @click="handlePhysicalExecute">执行物理删除</n-button>
            <n-button @click="handlePhysicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="单据逻辑删除恢复" size="small">
        <n-form ref="restoreFormRef" :model="restoreForm" :rules="restoreRules" label-placement="left" :label-width="100">
          <n-form-item label="单据编码" path="stock_no">
            <n-input v-model:value="restoreForm.stock_no" clearable placeholder="输入单个单据编码" />
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

defineOptions({ name: '单据删除' })

const message = useMessage()

const logicalFormRef = ref(null)
const physicalFormRef = ref(null)
const restoreFormRef = ref(null)

const logicalForm = ref({ stock_nos: '', operatorId: '' })
const physicalForm = ref({ stock_nos: '' })
const restoreForm = ref({ stock_no: '', operatorId: '' })

const logicalExecuting = ref(false)
const physicalExecuting = ref(false)
const restoreExecuting = ref(false)

const guidValidator = (value) => {
  const guidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
  return guidRegex.test(String(value || '').trim())
}

const logicalRules = {
  stock_nos: [
    { required: true, message: '请输入单据编码' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入单据编码')
        const nos = value.split(',').map((s) => s.trim()).filter((s) => s.length)
        if (!nos.length) return new Error('请输入单据编码')
        return true
      },
    },
  ],
  operatorId: [
    { required: true, message: '请输入操作人Id' },
    {
      validator: (_, value) => {
        if (!guidValidator(value)) {
          return new Error('操作人Id需为GUID格式（如：550e8400-e29b-41d4-a716-446655440000）')
        }
        return true
      },
    },
  ],
}

const physicalRules = {
  stock_nos: [
    { required: true, message: '请输入单据编码' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入单据编码')
        const nos = value.split(',').map((s) => s.trim()).filter((s) => s.length)
        if (!nos.length) return new Error('请输入单据编码')
        return true
      },
    },
  ],
}

const restoreRules = {
  stock_no: [
    { required: true, message: '请输入单据编码' },
  ],
  operatorId: [
    { required: true, message: '请输入删除人Id' },
    {
      validator: (_, value) => {
        if (!guidValidator(value)) {
          return new Error('删除人Id需为GUID格式（如：550e8400-e29b-41d4-a716-446655440000）')
        }
        return true
      },
    },
  ],
}

const parseNos = (text) => text.split(',').map((s) => s.trim()).filter((s) => s.length)

const handleLogicalReset = () => {
  logicalForm.value = { stock_nos: '', operatorId: '' }
}

const handlePhysicalReset = () => {
  physicalForm.value = { stock_nos: '' }
}

const handleRestoreReset = () => {
  restoreForm.value = { stock_no: '', operatorId: '' }
}

const handleLogicalExecute = async () => {
  try {
    await logicalFormRef.value?.validate()
  } catch (e) {
    return
  }
  const nos = parseNos(logicalForm.value.stock_nos)
  const operator_id = String(logicalForm.value.operatorId).trim()

  logicalExecuting.value = true
  try {
    const res = await api.deleteWmsDocumentsLogicalBatch({ stock_nos: nos, operator_id })
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
  try {
    await physicalFormRef.value?.validate()
  } catch (e) {
    return
  }
  const nos = parseNos(physicalForm.value.stock_nos)

  physicalExecuting.value = true
  try {
    const res = await api.deleteWmsDocumentsPhysicalBatch({ stock_nos: nos })
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
  try {
    await restoreFormRef.value?.validate()
  } catch (e) {
    return
  }
  const stock_no = String(restoreForm.value.stock_no).trim()
  const operator_id = String(restoreForm.value.operatorId).trim()

  restoreExecuting.value = true
  try {
    const res = await api.restoreWmsDocumentLogical({ stock_no, operator_id })
    if (res.code === 200 || res.code === 0) {
      const { restored = false } = res.data || {}
      if (restored) {
        message.success(res.msg || '逻辑删除恢复成功')
      } else {
        message.warning(res.msg || '单据无需恢复')
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
