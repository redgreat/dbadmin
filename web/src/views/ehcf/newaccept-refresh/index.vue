<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <!-- 文件上传 + 预览 -->
      <n-card title="上传Excel（固定模板）" size="small">
        <n-form label-placement="left" :label-width="100">
          <n-form-item label="Excel文件">
            <n-space vertical>
              <n-upload
                v-model:file-list="fileList"
                :max="1"
                :default-upload="false"
                accept=".xlsx,.xls"
                @before-upload="handleBeforeUpload"
                @change="handleUploadChange"
              >
                <n-button type="primary">
                  <TheIcon icon="mdi:file-upload-outline" :size="16" class="mr-2" />
                  选择文件
                </n-button>
              </n-upload>
              <n-text depth="3">
                模板列（表头须固定）：订单号 / 旧代办人工号 / 新代办人工号
              </n-text>
            </n-space>
          </n-form-item>
        </n-form>
        <n-space>
          <n-button type="primary" @click="handleDownloadTemplate">
            <TheIcon icon="mdi:download" :size="16" class="mr-2" />
            下载固定Excel模板
          </n-button>
          <n-button
            type="primary"
            :loading="previewing"
            :disabled="!currentFile"
            @click="handlePreview"
          >
            <TheIcon icon="mdi:magnify" :size="16" class="mr-2" />
            预览（不修改业务表）
          </n-button>
          <n-button
            type="warning"
            :loading="executing"
            :disabled="!previewResult?.success"
            @click="handleExecute"
          >
            <TheIcon icon="mdi:check-all" :size="16" class="mr-2" />
            执行刷新（按批次）
          </n-button>
          <n-button :loading="cleaning" :disabled="!previewResult" @click="handleCleanup">
            <TheIcon icon="mdi:delete-sweep-outline" :size="16" class="mr-2" />
            清理本批次
          </n-button>
        </n-space>
      </n-card>

      <!-- 预览结果 -->
      <n-card v-if="previewResult" title="预览结果" size="small">
        <n-alert :type="previewResult.success ? 'success' : 'warning'" class="mb-4">
          {{ previewResult.message }}
        </n-alert>
        <n-descriptions label-placement="left" :column="2" bordered size="small">
          <n-descriptions-item label="临时表">{{ previewResult.table_name }}</n-descriptions-item>
          <n-descriptions-item label="批次Id">{{ previewResult.batch_id }}</n-descriptions-item>
          <n-descriptions-item label="总行数">{{ previewResult.total }}</n-descriptions-item>
          <n-descriptions-item label="写入行数">{{ previewResult.written }}</n-descriptions-item>
          <n-descriptions-item label="跳过行数">{{ previewResult.skipped }}</n-descriptions-item>
          <n-descriptions-item label="命中工作流待办">
            {{ previewResult.matched_workflow }}
          </n-descriptions-item>
          <n-descriptions-item label="工单操作记录">
            {{ previewResult.operating_info }}
          </n-descriptions-item>
        </n-descriptions>
      </n-card>

      <!-- 执行结果 -->
      <n-card
        v-if="executeResult"
        :title="executeResult.success ? '执行成功' : '执行失败'"
        size="small"
      >
        <n-alert :type="executeResult.success ? 'success' : 'error'">
          {{ executeResult.message }}
        </n-alert>
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import api from '@/api'

defineOptions({ name: '车务待办人刷新' })

const message = useMessage()

const fileList = ref([])
const currentFile = ref(null)
const previewing = ref(false)
const executing = ref(false)
const cleaning = ref(false)

const previewResult = ref(null)
const executeResult = ref(null)

const handleBeforeUpload = ({ file }) => {
  const ext = file?.name?.split('.').pop()?.toLowerCase()
  if (!['xlsx', 'xls'].includes(ext)) {
    message.error('仅支持 .xlsx 和 .xls 文件')
    return false
  }
  return true
}

const handleUploadChange = ({ fileList: fl, file }) => {
  if (fl && fl.length === 0) {
    currentFile.value = null
    previewResult.value = null
    executeResult.value = null
    return
  }
  const fileItem = file || fl?.[0]
  currentFile.value = fileItem?.file || fileItem
}

const handleDownloadTemplate = async () => {
  try {
    const blob = await api.downloadEhcfNewAcceptTemplate()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '车务待办人刷新模板.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    message.error(e?.message || '模板下载失败')
  }
}

const errMsg = (e) => e?.message || e?.msg || '操作失败'

const handlePreview = async () => {
  if (!currentFile.value) {
    message.warning('请先选择Excel文件')
    return
  }
  previewing.value = true
  previewResult.value = null
  executeResult.value = null
  try {
    const res = await api.previewEhcfNewAccept(currentFile.value)
    if (res.code === 200) {
      previewResult.value = res.data
      message.success(res.data.message)
    } else {
      message.error(res.msg || '预览失败')
    }
  } catch (e) {
    message.error(errMsg(e))
  } finally {
    previewing.value = false
  }
}

const handleExecute = async () => {
  if (!previewResult.value?.success || !previewResult.value?.batch_id) {
    message.warning('请先预览并确认数据有效')
    return
  }
  const batchId = previewResult.value.batch_id
  const confirmed = await new Promise((resolve) => {
    window.$dialog.error({
      title: '确认执行车务待办人刷新',
      content: `将基于临时表「${previewResult.value.table_name}」批次 ${batchId}（写入 ${previewResult.value.written} 条）
调用存储过程 proc_VhsAcceptRefesh 刷新业务表：
- workflowruntimeactors（工作流待办人）
- tb_operatinginfo（工单操作记录）
- workflowruntimestatus（工作流状态）

此操作为批量改派，请确认数据无误！`,
      positiveText: '确认执行',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  executing.value = true
  executeResult.value = null
  try {
    const res = await api.refreshEhcfNewAcceptByBatch(batchId)
    if (res.code === 200 && res.data.success) {
      executeResult.value = res.data
      message.success(res.data.message)
    } else {
      executeResult.value = res.data
      message.error(res.data?.message || res.msg || '执行失败')
    }
  } catch (e) {
    executeResult.value = { success: false, message: errMsg(e) }
    message.error(errMsg(e))
  } finally {
    executing.value = false
  }
}

const handleCleanup = async () => {
  if (!previewResult.value?.batch_id) {
    message.warning('没有需要清理的批次数据')
    return
  }
  const batchId = previewResult.value.batch_id
  const confirmed = await new Promise((resolve) => {
    window.$dialog.warning({
      title: '确认清理本批次',
      content: `将删除临时表「${previewResult.value.table_name}」中批次 ${batchId} 的数据，此操作不可恢复。`,
      positiveText: '确认清理',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  cleaning.value = true
  try {
    await api.cleanupEhcfNewAccept(batchId)
    message.success('本批次数据已清理')
    previewResult.value = null
    executeResult.value = null
  } catch (e) {
    message.error(errMsg(e))
  } finally {
    cleaning.value = false
  }
}
</script>
