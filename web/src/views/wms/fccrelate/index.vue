<template>
  <CommonPage show-footer>
    <!-- 格式规范说明区 -->
    <n-card title="格式规范说明" size="small">
      <n-collapse>
        <n-collapse-item title="点击查看输入格式规范" name="format">
          <n-alert type="info">
            <p><strong>格式规则：</strong>FCC报销单号:仓储对账单1,仓储对账单2...;</p>
            <p><strong>分隔符说明：</strong></p>
            <ul>
              <li>冒号(:) - 分隔FCC报销单号和仓储对账单列表</li>
              <li>逗号(,) - 分隔多个仓储对账单号（支持中文逗号、顿号）</li>
              <li>分号(;) - 每行结尾标识</li>
            </ul>
            <p><strong>样例数据：</strong></p>
            <pre>J202512250009:ZD20260325153906B413D18,ZD202603251538028DCFA89,ZD20260325152917553AF9F;
J202601130001:ZD20260325153221C268F6B,ZD202603251531139A103CE;</pre>
          </n-alert>
          <n-button type="primary" size="small" @click="useExample" style="margin-top: 10px">
            使用样例
          </n-button>
        </n-collapse-item>
      </n-collapse>
    </n-card>

    <n-divider />

    <!-- 批量输入区 -->
    <n-card title="批量输入" size="small">
      <n-input
        v-model:value="inputText"
        type="textarea"
        placeholder="请输入FCC报销单与仓储对账单的关联关系"
        :rows="8"
        clearable
      />
      <n-space style="margin-top: 10px">
        <n-button type="primary" :loading="parsing" @click="handleParse">解析</n-button>
        <n-button @click="handleReset">重置</n-button>
      </n-space>
    </n-card>

    <n-divider />

    <!-- 解析预览区 -->
    <n-card v-if="parseResult" title="解析预览" size="small">
      <n-alert type="success" style="margin-bottom: 10px">
        共解析 {{ parseResult.total_fcc }} 个FCC报销单，{{ parseResult.total_wms }} 个仓储对账单
      </n-alert>
      <n-data-table
        :columns="previewColumns"
        :data="previewData"
        :bordered="false"
        size="small"
      />
      <n-space style="margin-top: 10px">
        <n-button type="primary" :loading="submitting" @click="handleSubmit">提交</n-button>
      </n-space>
    </n-card>

    <n-divider />

    <!-- 结果展示区 -->
    <n-card v-if="taskStatus" title="执行结果" size="small">
      <n-alert :type="statusType" style="margin-bottom: 10px">
        任务状态：{{ statusText }}
      </n-alert>
      <n-progress
        type="line"
        :percentage="progressPercentage"
        :status="progressStatus"
        style="margin-bottom: 10px"
      />
      <div v-if="taskStatus.result">
        <p>成功：{{ taskStatus.result.success_count }} 条</p>
        <p v-if="taskStatus.result.failed_items && taskStatus.result.failed_items.length > 0">
          失败：{{ taskStatus.result.failed_items.length }} 条
        </p>
        <n-data-table
          v-if="taskStatus.result.failed_items && taskStatus.result.failed_items.length > 0"
          :columns="failedColumns"
          :data="taskStatus.result.failed_items"
          :bordered="false"
          size="small"
          style="margin-top: 10px"
        />
      </div>
    </n-card>
  </CommonPage>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import { NCard, NSpace, NDataTable, NDivider, NInput, NButton, NCollapse, NCollapseItem, NAlert, NProgress } from 'naive-ui'
import api from '@/api'

defineOptions({ name: 'FCC报销单关联' })

const message = useMessage()

// 状态定义
const inputText = ref('')
const parseResult = ref(null)
const parsing = ref(false)
const submitting = ref(false)
const taskStatus = ref(null)
const taskId = ref('')
let pollTimer = null

// 预览表格列定义
const previewColumns = [
  { title: 'FCC报销单号', key: 'fcc_no' },
  { title: '仓储对账单号', key: 'wms_nos_str' },
  { title: '对账单数量', key: 'wms_count' },
]

// 失败项表格列定义
const failedColumns = [
  { title: 'FCC报销单号', key: 'fcc_no' },
  { title: '仓储对账单号', key: 'wms_no' },
  { title: '失败原因', key: 'reason' },
]

// 预览数据
const previewData = computed(() => {
  if (!parseResult.value || !parseResult.value.relations) return []
  return parseResult.value.relations.map(r => ({
    fcc_no: r.fcc_no,
    wms_nos_str: r.wms_nos.join(', '),
    wms_count: r.wms_nos.length
  }))
})

// 状态类型
const statusType = computed(() => {
  if (!taskStatus.value) return 'info'
  const status = taskStatus.value.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'processing') return 'warning'
  return 'info'
})

// 状态文本
const statusText = computed(() => {
  if (!taskStatus.value) return ''
  const status = taskStatus.value.status
  const statusMap = {
    'pending': '等待中',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || status
})

// 进度百分比
const progressPercentage = computed(() => {
  if (!taskStatus.value || !taskStatus.value.progress) return 0
  const { total, processed } = taskStatus.value.progress
  if (total === 0) return 0
  return Math.round((processed / total) * 100)
})

// 进度状态
const progressStatus = computed(() => {
  if (!taskStatus.value) return 'default'
  const status = taskStatus.value.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'processing') return 'warning'
  return 'default'
})

// 使用样例
const useExample = () => {
  inputText.value = `J202512250009:ZD20260325153906B413D18,ZD202603251538028DCFA89,ZD20260325152917553AF9F;
J202601130001:ZD20260325153221C268F6B,ZD202603251531139A103CE;`
}

// 解析
const handleParse = async () => {
  if (!inputText.value.trim()) {
    message.warning('请输入内容')
    return
  }
  
  parsing.value = true
  try {
    const res = await api.fccParse({ input_text: inputText.value })
    if (res.code === 200) {
      parseResult.value = res.data
      message.success('解析成功')
    } else {
      message.error(res.msg || '解析失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    parsing.value = false
  }
}

// 重置
const handleReset = () => {
  inputText.value = ''
  parseResult.value = null
  taskStatus.value = null
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 提交
const handleSubmit = async () => {
  submitting.value = true
  try {
    // 先验证
    const validateRes = await api.fccValidate({ relations: parseResult.value.relations })
    if (validateRes.code !== 200 || !validateRes.data.valid) {
      message.error(validateRes.data.message || '验证失败')
      return
    }
    
    // 提交任务
    const submitRes = await api.fccSubmit({ relations: parseResult.value.relations })
    if (submitRes.code === 200) {
      taskId.value = submitRes.data.task_id
      message.success('任务已提交')
      startPolling()
    } else {
      message.error(submitRes.msg || '提交失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    submitting.value = false
  }
}

// 开始轮询
const startPolling = () => {
  pollTimer = setInterval(async () => {
    try {
      const res = await api.fccGetTaskStatus(taskId.value)
      if (res.code === 200) {
        taskStatus.value = res.data
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          clearInterval(pollTimer)
          pollTimer = null
          if (res.data.status === 'completed') {
            message.success('任务执行完成')
          } else {
            message.error('任务执行失败')
          }
        }
      }
    } catch (e) {
      console.error('轮询失败', e)
    }
  }, 1000)
}

// 组件卸载时清理
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>
