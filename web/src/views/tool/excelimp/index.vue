<template>
  <CommonPage show-footer>
    <div class="excel-import-container">
      <!-- 表单区域 -->
      <n-card class="form-card" :bordered="false">
        <n-form ref="formRef" :model="form" label-placement="left" :label-width="100">
          <!-- 文件上传 -->
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

          <!-- 数据库类型选择 -->
          <n-form-item label="数据库类型" path="dbType">
            <n-radio-group v-model:value="form.dbType" size="medium">
              <n-space>
                <n-radio value="mysql">MySQL</n-radio>
                <n-radio value="postgresql">PostgreSQL</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <!-- 操作按钮 -->
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

      <!-- 进度显示 -->
      <div v-if="fileKey && progress && progress.stage !== 'unknown'" class="mt-15">
        <n-card title="处理进度" size="small">
          <n-steps :current="stepIndex" status="process">
            <n-step title="解析文件" description="读取Excel文件" />
            <n-step title="生成SQL" description="生成建表和插入语句" />
            <n-step title="完成" description="SQL生成完成" />
          </n-steps>
          <div class="mt-10">
            <n-tag type="info" v-if="fileKey">批次号：{{ fileKey }}</n-tag>
            <n-tag class="ml-10" :type="statusTagType" v-if="progress">
              {{ statusText }}
            </n-tag>
          </div>
        </n-card>
      </div>

      <!-- 结果显示区域 -->
      <n-card v-if="sqlResult" title="生成的SQL语句" class="result-card" :bordered="false">
        <template #header-extra>
          <n-space>
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
      
      <!-- 使用说明 -->
      <n-alert type="info" class="usage-guide" :bordered="false">
        <template #icon>
          <TheIcon icon="material-symbols:info-outline" :size="20" />
        </template>
        <div class="guide-content">
          <div class="guide-title">使用说明</div>
          <ul class="guide-list">
            <li>上传Excel文件(支持.xlsx和.xls格式,最大10MB),系统将读取第一个工作表</li>
            <li>第一行将作为列名,自动转换为英文字段名</li>
            <li>系统会自动推断每列的数据类型(INT、VARCHAR、DATE等)</li>
            <li>生成带时间戳的临时表建表语句和批量插入SQL(每批500行)</li>
            <li>大文件会在后台异步处理,可离开页面后再次查看进度</li>
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
const formRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const generating = ref(false)
const sqlResult = ref('')
const windowWidth = ref(window.innerWidth)
const fileKey = ref('')
const progress = ref(null)
let timer = null

const form = ref({
  dbType: 'mysql'
})

// 响应式结果区域行数
const resultRows = computed(() => {
  if (windowWidth.value < 768) return 15
  if (windowWidth.value < 1024) return 18
  return 20
})

// 监听窗口大小变化
const handleResize = () => {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // 恢复上次未完成的任务
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

/** 选择文件前校验 */
const handleBeforeUpload = async ({ file }) => {
  console.log('选择文件前校验:', file)
  const ext = file?.name?.split('.').pop()?.toLowerCase()
  const allow = ['xlsx', 'xls']
  if (!allow.includes(ext)) {
    message.error('仅支持 .xlsx 和 .xls 文件')
    return false
  }
  // 返回 true 或不返回,允许文件选择
  return true
}

/** 上传变更处理 */
const handleUploadChange = ({ fileList: fl, file }) => {
  console.log('上传变更:', { fileList: fl, file })
  fileList.value = fl

  // 优先使用 file 参数,然后尝试从 fileList 获取
  if (file) {
    selectedFile.value = file.file || file
  } else if (fl && fl.length > 0) {
    const fileItem = fl[0]
    selectedFile.value = fileItem.file || fileItem
  } else {
    selectedFile.value = null
  }

  console.log('选中的文件:', selectedFile.value)
}

/** 生成SQL */
const handleGenerate = async () => {
  if (!selectedFile.value) {
    message.error('请先选择Excel文件')
    return
  }

  generating.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    fd.append('db_type', form.value.dbType)

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
    // 优先显示后端返回的详细错误信息
    const errorMsg = e?.error?.detail || e?.message || '请求异常'
    message.error(errorMsg)
  } finally {
    generating.value = false
  }
}

/** 清空表单 */
const handleClear = () => {
  selectedFile.value = null
  fileList.value = []
  sqlResult.value = ''
  fileKey.value = ''
  progress.value = null
  lStorage.remove('excelimp_file_key')
  stopPolling()
}

/** 复制到剪贴板 */
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(sqlResult.value)
    message.success('已复制到剪贴板')
  } catch (e) {
    message.error('复制失败,请手动复制')
  }
}

/** 下载SQL文件 */
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

/** 开始轮询进度 */
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
    } catch (e) {
      // 忽略单次错误
    }
  }, 1500)
}

/** 停止轮询 */
const stopPolling = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

/** 计算属性：步骤索引 */
const stepIndex = computed(() => {
  const stage = progress.value?.stage
  if (stage === 'parsing') return 1
  if (stage === 'generating') return 2
  if (stage === 'done' || stage === 'failed') return 3
  return 1
})

/** 计算属性：状态文本 */
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

/* 使用说明样式 */
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

/* 表单卡片样式 */
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

/* 结果卡片样式 */
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

/* 移动端响应式布局 */
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

/* 平板端响应式布局 */
@media (min-width: 769px) and (max-width: 1024px) {
  .excel-import-container {
    padding: 0 16px;
  }

  .guide-list {
    font-size: 14px;
  }
}

/* 大屏幕优化 */
@media (min-width: 1440px) {
  .excel-import-container {
    max-width: 1400px;
  }
}
</style>
