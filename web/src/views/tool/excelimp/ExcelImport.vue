<template>
  <CommonPage show-footer title="Excel临时表生成工具">
    <div class="excel-import-container">
      <!-- 使用说明 -->
      <n-alert type="info" class="usage-guide" :bordered="false">
        <template #icon>
          <n-icon><InfoCircleOutlined /></n-icon>
        </template>
        <div class="guide-content">
          <div class="guide-title">使用说明</div>
          <ul class="guide-list">
            <li>上传Excel文件（支持.xlsx和.xls格式），系统将读取第一个工作表</li>
            <li>第一行将作为列名，自动转换为英文字段名</li>
            <li>系统会自动推断每列的数据类型（INT、VARCHAR、DATE等）</li>
            <li>生成带时间戳的临时表建表语句和批量插入SQL（每批500行）</li>
          </ul>
        </div>
      </n-alert>

      <!-- 表单区域 -->
      <n-card class="form-card" :bordered="false">
        <n-form ref="formRef" :model="form" label-placement="left" :label-width="labelWidth">
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
                    <n-icon><UploadOutlined /></n-icon>
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
          <n-form-item :show-label="false">
            <n-space class="action-buttons">
              <n-button 
                type="primary" 
                size="medium"
                :loading="generating" 
                :disabled="!selectedFile"
                @click="handleGenerate"
              >
                <template #icon>
                  <n-icon><ThunderboltOutlined /></n-icon>
                </template>
                生成SQL
              </n-button>
              <n-button size="medium" @click="handleClear">
                <template #icon>
                  <n-icon><ClearOutlined /></n-icon>
                </template>
                清空
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>

      <!-- 结果显示区域 -->
      <n-card v-if="sqlResult" title="生成的SQL语句" class="result-card" :bordered="false">
        <template #header-extra>
          <n-button type="primary" size="small" @click="handleCopy">
            <template #icon>
              <n-icon><CopyOutlined /></n-icon>
            </template>
            复制到剪贴板
          </n-button>
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
    </div>
  </CommonPage>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import { 
  InfoCircleOutlined, 
  UploadOutlined, 
  ThunderboltOutlined, 
  ClearOutlined, 
  CopyOutlined 
} from '@vicons/antd'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: 'Excel临时表生成' })

const message = useMessage()
const formRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const generating = ref(false)
const sqlResult = ref('')
const windowWidth = ref(window.innerWidth)

const form = ref({
  dbType: 'mysql'
})

// 响应式标签宽度
const labelWidth = computed(() => {
  return windowWidth.value < 768 ? 80 : 120
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
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

/** 选择文件前校验 */
const handleBeforeUpload = async ({ file }) => {
  const ext = file?.name?.split('.').pop()?.toLowerCase()
  const allow = ['xlsx', 'xls']
  if (!allow.includes(ext)) {
    message.error('仅支持 .xlsx 和 .xls 文件')
    return false
  }
  return true
}

/** 上传变更处理 */
const handleUploadChange = ({ fileList: fl }) => {
  fileList.value = fl
  selectedFile.value = fl[0]?.file || null
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
    
    const res = await api.generateExcelSql(fd)
    
    if (res.code === 200 && res.data?.sql) {
      sqlResult.value = res.data.sql
      message.success('SQL生成成功')
    } else {
      message.error(res.msg || 'SQL生成失败')
    }
  } catch (e) {
    message.error(e?.message || '请求异常')
  } finally {
    generating.value = false
  }
}

/** 清空表单 */
const handleClear = () => {
  selectedFile.value = null
  fileList.value = []
  sqlResult.value = ''
  form.value.dbType = 'mysql'
}

/** 复制到剪贴板 */
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(sqlResult.value)
    message.success('已复制到剪贴板')
  } catch (e) {
    message.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.excel-import-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* 使用说明样式 */
.usage-guide {
  margin-bottom: 24px;
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
    margin-bottom: 16px;
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
