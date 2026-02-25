<template>
  <CommonPage show-footer title="SQL格式化工具">
    <div class="sql-formatter-container">
      <!-- 使用说明 -->
      <n-alert type="info" class="usage-guide" :bordered="false">
        <template #icon>
          <n-icon><InfoCircleOutlined /></n-icon>
        </template>
        <div class="guide-content">
          <div class="guide-title">使用说明</div>
          <ul class="guide-list">
            <li>在输入框中粘贴或输入需要格式化的SQL语句</li>
            <li>支持单条或多条SQL语句的格式化</li>
            <li>可自定义关键字大小写和缩进宽度</li>
            <li>格式化后的SQL将自动进行关键字处理、缩进对齐等优化</li>
            <li>点击"复制结果"按钮可快速复制格式化后的SQL到剪贴板</li>
          </ul>
        </div>
      </n-alert>

      <!-- 格式化选项 -->
      <n-card title="格式化选项" class="options-card" :bordered="false">
        <n-form :model="formatOptions" label-placement="left" :label-width="100">
          <n-form-item label="关键字大小写">
            <n-radio-group v-model:value="formatOptions.keywordCase" size="small">
              <n-space>
                <n-radio value="upper">大写 (UPPER)</n-radio>
                <n-radio value="lower">小写 (lower)</n-radio>
                <n-radio value="capitalize">首字母大写 (Capitalize)</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>
          <n-form-item label="缩进宽度">
            <n-input-number 
              v-model:value="formatOptions.indentWidth" 
              :min="0" 
              :max="8" 
              size="small"
              style="width: 120px"
            >
              <template #suffix>空格</template>
            </n-input-number>
          </n-form-item>
        </n-form>
      </n-card>

      <!-- 输入区域 -->
      <n-card title="原始SQL" class="input-card" :bordered="false">
        <n-input
          v-model:value="inputSql"
          type="textarea"
          :rows="inputRows"
          placeholder="请输入需要格式化的SQL语句..."
          class="sql-textarea"
        />
      </n-card>

      <!-- 操作按钮 -->
      <n-space class="action-buttons">
        <n-button 
          type="primary" 
          size="medium"
          :loading="formatting" 
          :disabled="!inputSql.trim()"
          @click="handleFormat"
        >
          <template #icon>
            <n-icon><ThunderboltOutlined /></n-icon>
          </template>
          格式化
        </n-button>
        <n-button size="medium" @click="handleClear">
          <template #icon>
            <n-icon><ClearOutlined /></n-icon>
          </template>
          清空
        </n-button>
      </n-space>

      <!-- 输出区域 -->
      <n-card v-if="outputSql" title="格式化后的SQL" class="output-card" :bordered="false">
        <template #header-extra>
          <n-button type="primary" size="small" @click="handleCopy">
            <template #icon>
              <n-icon><CopyOutlined /></n-icon>
            </template>
            复制结果
          </n-button>
        </template>
        <n-input
          v-model:value="outputSql"
          type="textarea"
          :rows="outputRows"
          readonly
          placeholder="格式化后的SQL将显示在这里..."
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
  ThunderboltOutlined, 
  ClearOutlined, 
  CopyOutlined 
} from '@vicons/antd'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: 'SQL格式化' })

const message = useMessage()
const inputSql = ref('')
const outputSql = ref('')
const formatting = ref(false)
const windowWidth = ref(window.innerWidth)

// 格式化选项
const formatOptions = ref({
  keywordCase: 'upper',
  indentWidth: 2
})

// 响应式输入区域行数
const inputRows = computed(() => {
  if (windowWidth.value < 768) return 10
  if (windowWidth.value < 1024) return 12
  return 14
})

// 响应式输出区域行数
const outputRows = computed(() => {
  if (windowWidth.value < 768) return 12
  if (windowWidth.value < 1024) return 14
  return 16
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

/** 格式化SQL */
const handleFormat = async () => {
  if (!inputSql.value.trim()) {
    message.error('请输入SQL语句')
    return
  }

  formatting.value = true
  try {
    const fd = new FormData()
    fd.append('sql', inputSql.value)
    fd.append('keyword_case', formatOptions.value.keywordCase)
    fd.append('indent_width', formatOptions.value.indentWidth.toString())
    
    const res = await api.formatSql(fd)
    
    if (res.code === 200 && res.data?.sql) {
      outputSql.value = res.data.sql
      message.success('格式化成功')
    } else {
      message.error(res.msg || '格式化失败')
    }
  } catch (e) {
    message.error(e?.message || '请求异常')
  } finally {
    formatting.value = false
  }
}

/** 清空 */
const handleClear = () => {
  inputSql.value = ''
  outputSql.value = ''
  formatOptions.value = {
    keywordCase: 'upper',
    indentWidth: 2
  }
}

/** 复制到剪贴板 */
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(outputSql.value)
    message.success('已复制到剪贴板')
  } catch (e) {
    message.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.sql-formatter-container {
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

/* 选项卡片样式 */
.options-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 输入卡片样式 */
.input-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 操作按钮样式 */
.action-buttons {
  margin-bottom: 24px;
  width: 100%;
}

/* 输出卡片样式 */
.output-card {
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

/* SQL文本区域样式 */
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
  .sql-formatter-container {
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

  .options-card {
    margin-bottom: 16px;
  }

  .input-card {
    margin-bottom: 16px;
  }

  .action-buttons {
    flex-direction: column;
    margin-bottom: 16px;
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
  .sql-formatter-container {
    padding: 0 16px;
  }

  .guide-list {
    font-size: 14px;
  }
}

/* 大屏幕优化 */
@media (min-width: 1440px) {
  .sql-formatter-container {
    max-width: 1400px;
  }
}
</style>
