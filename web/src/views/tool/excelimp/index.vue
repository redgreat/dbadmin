<template>
  <CommonPage show-footer>
    <div class="excel-import-container">
      <n-card class="form-card" :bordered="false">
        <n-form ref="formRef" :model="form" label-placement="left" :label-width="100">
          <n-form-item label="Excel文件" path="file">
            <div class="upload-wrapper">
              <n-upload
                v-model:file-list="fileList"
                :max="1"
                :show-file-list="true"
                :default-upload="false"
                accept=".xlsx,.xls"
                @before-upload="handleBeforeUpload"
                @change="handleUploadChange"
              >
                <n-button type="primary" size="medium">
                  <template #icon>
                    <TheIcon icon="material-symbols:upload" :size="18" />
                  </template>
                  选择Excel文件
                </n-button>
              </n-upload>
            </div>
          </n-form-item>

          <n-form-item label="目标连接(可选)" path="targetConnId">
            <n-select
              v-model:value="form.targetConnId"
              :options="connOptions"
              filterable
              clearable
              placeholder="可不选；不选则仅生成SQL，不可执行"
            />
          </n-form-item>

          <n-form-item label=" " :show-label="true">
            <n-space class="action-buttons">
              <n-button
                type="primary"
                size="medium"
                :loading="generating"
                :disabled="!selectedFile"
                @click="handleGenerate"
              >
                <template #icon>
                  <TheIcon icon="material-symbols:bolt" :size="18" />
                </template>
                生成SQL
              </n-button>
              <n-button size="medium" @click="handleClear">
                <template #icon>
                  <TheIcon icon="material-symbols:clear-all" :size="18" />
                </template>
                清空
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>

      <div v-if="fileKey && progress && progress.stage !== 'unknown'" class="mt-15">
        <n-card title="处理进度" size="small">
          <n-steps :current="stepIndex" status="process">
            <n-step title="解析文件" description="读取Excel文件" />
            <n-step title="生成SQL" description="生成建表和插入语句" />
            <n-step title="完成" description="SQL生成完成" />
          </n-steps>
          <div class="mt-10">
            <n-tag v-if="fileKey" type="info">批次号：{{ fileKey }}</n-tag>
            <n-tag v-if="progress" class="ml-10" :type="statusTagType">
              {{ statusText }}
            </n-tag>
          </div>
        </n-card>
      </div>

      <n-card v-if="sqlResult" title="生成的SQL语句" class="result-card" :bordered="false">
        <template #header-extra>
          <n-space>
            <n-button
              v-if="form.targetConnId"
              type="success"
              size="small"
              :disabled="!fileKey"
              @click="handleExecute"
            >
              <template #icon>
                <TheIcon icon="material-symbols:play-arrow" :size="16" />
              </template>
              执行SQL
            </n-button>
            <n-button type="primary" size="small" @click="handleDownload">
              <template #icon>
                <TheIcon icon="material-symbols:download" :size="16" />
              </template>
              下载SQL文件
            </n-button>
            <n-button size="small" @click="handleCopy">
              <template #icon>
                <TheIcon icon="material-symbols:content-copy" :size="16" />
              </template>
              复制到剪贴板
            </n-button>
          </n-space>
        </template>
        <n-input
          v-model:value="sqlResult"
          type="textarea"
          :rows="resultRows"
          readonly
          placeholder="生成的SQL语句将显示在这里..."
          class="sql-textarea"
        />
      </n-card>

      <n-alert type="info" class="usage-guide" :bordered="false">
        <template #icon>
          <TheIcon icon="material-symbols:info-outline" :size="20" />
        </template>
        <div class="guide-content">
          <div class="guide-title">使用说明</div>
          <ul class="guide-list">
            <li>上传Excel文件后，选择连接管理中的目标连接</li>
            <li>系统会在后端生成SQL，执行时只允许执行该后端生成结果</li>
            <li>执行接口不接收前端SQL文本，防止篡改自定义SQL</li>
            <li>大文件会在后台异步处理，可离开页面后再次查看进度</li>
          </ul>
        </div>
      </n-alert>
    </div>
  </CommonPage>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import api from '@/api'
import { lStorage } from '@/utils'

defineOptions({ name: 'Excel临时表生成' })

const message = useMessage()
const fileList = ref([])
const selectedFile = ref(null)
const generating = ref(false)
const sqlResult = ref('')
const windowWidth = ref(window.innerWidth)
const fileKey = ref('')
const progress = ref(null)
const connOptions = ref([])
let timer = null

const form = ref({
  targetConnId: null,
})

const resultRows = computed(() => {
  if (windowWidth.value < 768) return 15
  if (windowWidth.value < 1024) return 18
  return 20
})

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  loadConnOptions()
  const last = lStorage.get('excelimp_file_key')
  if (last) {
    fileKey.value = last
    startPolling()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  stopPolling()
})

const loadConnOptions = async () => {
  try {
    const res = await api.getConnList({ page: 1, page_size: 1000 })
    connOptions.value = (res.data || []).map((item) => ({
      label: `${item.name} (${item.db_type})`,
      value: item.id,
    }))
  } catch {
    connOptions.value = []
  }
}

const handleBeforeUpload = async ({ file }) => {
  const ext = file?.name?.split('.').pop()?.toLowerCase()
  const allow = ['xlsx', 'xls']
  if (!allow.includes(ext)) {
    message.error('仅支持 .xlsx 和 .xls 文件')
    return false
  }
  return true
}

const handleUploadChange = ({ fileList: fl, file }) => {
  fileList.value = fl
  if (file) {
    selectedFile.value = file.file || file
  } else if (fl && fl.length > 0) {
    const fileItem = fl[0]
    selectedFile.value = fileItem.file || fileItem
  } else {
    selectedFile.value = null
  }
}

const handleGenerate = async () => {
  if (!selectedFile.value) {
    message.error('请先选择Excel文件')
    return
  }
  generating.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    if (form.value.targetConnId) {
      fd.append('target_conn_id', form.value.targetConnId)
    }

    const res = await api.submitExcelSql(fd)

    if (res.code === 200 && res.data?.file_key) {
      fileKey.value = res.data.file_key
      lStorage.set('excelimp_file_key', fileKey.value)
      message.success('任务已提交，正在后台处理')
      startPolling()
    } else {
      message.error(res.msg || 'SQL生成失败')
    }
  } catch (e) {
    const errorMsg = e?.error?.detail || e?.message || '请求异常'
    message.error(errorMsg)
  } finally {
    generating.value = false
  }
}

const handleClear = () => {
  selectedFile.value = null
  fileList.value = []
  sqlResult.value = ''
  fileKey.value = ''
  progress.value = null
  lStorage.remove('excelimp_file_key')
  stopPolling()
}

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(sqlResult.value)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

const handleDownload = () => {
  if (!sqlResult.value) {
    message.error('没有可下载的SQL内容')
    return
  }

  const blob = new Blob([sqlResult.value], { type: 'text/plain' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `excel_import_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.sql`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
  message.success('SQL文件下载成功')
}

const handleExecute = async () => {
  if (!fileKey.value) {
    message.error('没有可执行的任务标识')
    return
  }
  if (!form.value.targetConnId) {
    message.error('请先选择目标连接')
    return
  }
  try {
    const res = await api.executeExcelImportTask({
      source_type: 'excelimp',
      file_key: fileKey.value,
      target_conn_id: form.value.targetConnId,
    })
    if (res?.data?.success === false) {
      message.error(res.msg || '执行失败')
      return
    }
    message.success(res.msg || '执行成功')
  } catch {
    // 全局请求拦截器已弹出错误，避免重复提示
  }
}

const startPolling = () => {
  stopPolling()
  timer = setInterval(async () => {
    if (!fileKey.value) return
    try {
      const res = await api.getExcelProgress({ file_key: fileKey.value })
      if (res.code === 200) {
        progress.value = res.data
        if (progress.value?.stage === 'done') {
          stopPolling()
          if (progress.value?.sql) {
            sqlResult.value = progress.value.sql
            message.success('SQL生成完成')
          }
        } else if (progress.value?.stage === 'failed') {
          stopPolling()
          message.error(progress.value?.message || 'SQL生成失败')
        }
      }
    } catch {
      // 忽略单次错误
    }
  }, 1500)
}

const stopPolling = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const stepIndex = computed(() => {
  const stage = progress.value?.stage
  if (stage === 'parsing') return 1
  if (stage === 'generating') return 2
  if (stage === 'done' || stage === 'failed') return 3
  return 1
})

const statusText = computed(() => {
  const p = progress.value
  if (!p) return '等待中'
  if (p.stage === 'failed') return `失败：${p.message || ''}`
  if (p.stage === 'done') return '完成'
  if (p.stage === 'generating') return '生成SQL中'
  if (p.stage === 'parsing') return '解析中'
  return p.stage || '未知'
})

const statusTagType = computed(() => {
  const p = progress.value
  if (!p) return 'default'
  if (p.stage === 'failed') return 'error'
  if (p.stage === 'done') return 'success'
  return 'info'
})
</script>

<style scoped>
.excel-import-container {
  max-width: 1200px;
  margin: 0 auto;
}
.usage-guide {
  margin-top: 24px;
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
}
.guide-content {
  padding: 4px 0;
}
.guide-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1976d2;
}
.guide-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
  color: #424242;
}
.guide-list li {
  margin-bottom: 4px;
}
.form-card {
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.upload-wrapper {
  width: 100%;
}
.action-buttons {
  width: 100%;
}
.result-card {
  margin-top: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  animation: fadeIn 0.3s ease-in;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.sql-textarea {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.sql-textarea :deep(textarea) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}
@media (max-width: 768px) {
  .excel-import-container {
    padding: 0 8px;
  }
  .usage-guide {
    margin-top: 16px;
  }
  .guide-title {
    font-size: 14px;
  }
  .guide-list {
    font-size: 13px;
    padding-left: 16px;
    line-height: 1.6;
  }
  .form-card {
    margin-bottom: 16px;
  }
  .action-buttons {
    flex-direction: column;
    width: 100%;
  }
  .action-buttons :deep(.n-button) {
    width: 100%;
  }
  .sql-textarea {
    font-size: 12px;
  }
  .sql-textarea :deep(textarea) {
    font-size: 12px;
  }
}
@media (min-width: 769px) and (max-width: 1024px) {
  .excel-import-container {
    padding: 0 16px;
  }
  .guide-list {
    font-size: 14px;
  }
}
@media (min-width: 1440px) {
  .excel-import-container {
    max-width: 1400px;
  }
}
</style>
