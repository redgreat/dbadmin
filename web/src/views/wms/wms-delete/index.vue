<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="单据逻辑删除" size="small">
        <n-form ref="logicalFormRef" :model="logicalForm" :rules="logicalRules" label-placement="left" :label-width="100">
          <n-form-item label="单据Id" path="stock_ids">
            <n-input v-model:value="logicalForm.stock_ids" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个单据Id，逗号分隔" />
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
          <n-form-item label="单据Id" path="stock_ids">
            <n-input v-model:value="physicalForm.stock_ids" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个单据Id，逗号分隔" />
          </n-form-item>
          <n-space>
            <n-button type="error" :loading="physicalExecuting" @click="handlePhysicalExecute">执行物理删除</n-button>
            <n-button @click="handlePhysicalReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card title="单据逻辑删除恢复" size="small">
        <n-form ref="restoreFormRef" :model="restoreForm" :rules="restoreRules" label-placement="left" :label-width="100">
          <n-form-item label="单据Id" path="stock_id">
            <n-input v-model:value="restoreForm.stock_id" clearable placeholder="输入单个单据Id" />
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

const logicalForm = ref({ stock_ids: '', operatorId: '' })
const physicalForm = ref({ stock_ids: '' })
const restoreForm = ref({ stock_id: '', operatorId: '' })

const logicalExecuting = ref(false)
const physicalExecuting = ref(false)
const restoreExecuting = ref(false)

const rules = {
  stock_ids: [
    { required: true, message: '请输入单据Id' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入单据Id')
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return new Error('请输入单据Id')
        return true
      },
    },
  ],
  operatorId: [
    { required: true, message: '请输入操作人Id' },
    {
      validator: (_, value) => {
        const guidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
        if (!guidRegex.test(String(value || '').trim())) {
          return new Error('操作人Id需为GUID格式（如：550e8400-e29b-41d4-a716-446655440000）')
        }
        return true
      },
    },
  ],
}

const logicalRules = rules

const physicalRules = {
  stock_ids: [
    { required: true, message: '请输入单据Id' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入单据Id')
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return new Error('请输入单据Id')
        return true
      },
    },
  ],
}

const restoreRules = {
  stock_id: [
    { required: true, message: '请输入单据Id' },
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
  logicalForm.value = { stock_ids: '', operatorId: '' }
}

const handlePhysicalReset = () => {
  physicalForm.value = { stock_ids: '' }
}

const handleRestoreReset = () => {
  restoreForm.value = { stock_id: '', operatorId: '' }
}

const handleLogicalExecute = async () => {
  try {
    await logicalFormRef.value?.validate()
  } catch (e) {
    return
  }
  const ids = parseIds(logicalForm.value.stock_ids)
  const operator_id = String(logicalForm.value.operatorId).trim()
  if (!operator_id) {
    message.error('操作人Id不能为空')
    return
  }

  // 先验证单据状态
  logicalExecuting.value = true
  try {
    const validateRes = await api.validateWmsDocuments({ stock_ids: ids, validate_type: 'logical_delete' })
    if (validateRes.code !== 0 && validateRes.code !== 200) {
      message.error(validateRes.msg || '验证失败')
      return
    }

    if (!validateRes.data.success) {
      const { not_found_docs = [], invalid_docs = [] } = validateRes.data
      let errorMsg = validateRes.data.message
      if (not_found_docs.length > 0) {
        errorMsg += `\n不存在的单据: ${not_found_docs.join(', ')}`
      }
      if (invalid_docs.length > 0) {
        errorMsg += `\n状态不符的单据: ${invalid_docs.map(d => `${d.stock_id}(${d.reason})`).join(', ')}`
      }
      message.error(errorMsg)
      return
    }

    // 验证通过,执行删除
    const res = await api.deleteWmsDocumentsLogicalBatch({ stock_ids: ids, operator_id })
    if (res.code === 0 || res.code === 200) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      if (failed_ids.length > 0) {
        message.warning(`逻辑删除完成：成功 ${success_count} 条，失败 ${failed_ids.length} 条，失败ID：${failed_ids.join(', ')}`)
      } else {
        message.success(`逻辑删除成功：${success_count} 条`)
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
  const ids = parseIds(physicalForm.value.stock_ids)

  // 先验证单据是否存在
  physicalExecuting.value = true
  try {
    const validateRes = await api.validateWmsDocuments({ stock_ids: ids, validate_type: 'physical_delete' })
    if (validateRes.code !== 0 && validateRes.code !== 200) {
      message.error(validateRes.msg || '验证失败')
      return
    }

    if (!validateRes.data.success) {
      const { not_found_docs = [] } = validateRes.data
      let errorMsg = validateRes.data.message
      if (not_found_docs.length > 0) {
        errorMsg += `\n不存在的单据: ${not_found_docs.join(', ')}`
      }
      message.error(errorMsg)
      return
    }

    // 验证通过,执行删除
    const res = await api.deleteWmsDocumentsPhysicalBatch({ stock_ids: ids })
    if (res.code === 0 || res.code === 200) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      if (failed_ids.length > 0) {
        message.warning(`物理删除完成：成功 ${success_count} 条，失败 ${failed_ids.length} 条，失败ID：${failed_ids.join(', ')}`)
      } else {
        message.success(`物理删除成功：${success_count} 条`)
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
  const stock_id = String(restoreForm.value.stock_id).trim()
  const operator_id = String(restoreForm.value.operatorId).trim()
  if (!operator_id) {
    message.error('删除人Id不能为空')
    return
  }

  // 先验证单据状态
  restoreExecuting.value = true
  try {
    const validateRes = await api.validateWmsDocuments({ stock_ids: [stock_id], validate_type: 'restore' })
    if (validateRes.code !== 0 && validateRes.code !== 200) {
      message.error(validateRes.msg || '验证失败')
      return
    }

    if (!validateRes.data.success) {
      const { not_found_docs = [], invalid_docs = [] } = validateRes.data
      let errorMsg = validateRes.data.message
      if (not_found_docs.length > 0) {
        errorMsg += `\n不存在的单据: ${not_found_docs.join(', ')}`
      }
      if (invalid_docs.length > 0) {
        errorMsg += `\n状态不符的单据: ${invalid_docs.map(d => `${d.stock_id}(${d.reason})`).join(', ')}`
      }
      message.error(errorMsg)
      return
    }

    // 验证通过,执行恢复
    const res = await api.restoreWmsDocumentLogical({ stock_id, operator_id })
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
