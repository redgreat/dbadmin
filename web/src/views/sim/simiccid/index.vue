<template>
  <CommonPage show-footer>
    <n-form ref="formRef" :model="form" label-placement="left" :label-width="100">
      <n-form-item label="Excel文件" path="file">
        <n-space :size="8" vertical align="start">
          <n-upload
            v-model:file-list="fileList"
            :max="1"
            :show-file-list="false"
            :default-upload="false"
            :accept="'.xlsx,.xls,.csv'"
            @before-upload="handleBeforeUpload"
            @change="handleUploadChange"
            @remove="handleRemove"
          >
            <n-button type="primary">选择文件</n-button>
          </n-upload>
          <n-button v-if="!selectedFile" text tag="a" href="/SimICCID.xlsx" download>下载样例文件（SimICCID.xlsx）</n-button>
        </n-space>
      </n-form-item>
      <n-space>
        <n-button type="primary" :loading="submitting" :disabled="!selectedFile" @click="handleSubmit">提交处理</n-button>
        <n-button @click="handleReset">重置</n-button>
      </n-space>
    </n-form>
    <div v-if="fileKey && progress && progress.stage !== 'unknown'" class="mt-15">
      <n-card title="处理进度" size="small">
        <n-steps :current="stepIndex" status="process">
          <n-step title="解析文件" description="读取并校验列名" />
          <n-step title="写入临时表" :description="progressDescWriting" />
          <n-step title="调用过程" description="执行后台存储过程" />
          <n-step title="完成" />
        </n-steps>
        <div class="mt-10">
          <n-tag type="info" v-if="fileKey">批次号：{{ fileKey }}</n-tag>
          <n-tag class="ml-10" :type="statusTagType" v-if="progress">
            {{ statusText }}
          </n-tag>
        </div>
      </n-card>
    </div>
  </CommonPage>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'
import { lStorage } from '@/utils'

defineOptions({ name: 'SIM-ICCID导入' })

const message = useMessage()
const formRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const submitting = ref(false)
const fileKey = ref('')
const progress = ref(null)
let timer = null

/** 选择文件前校验（函数级中文注释） */
const handleBeforeUpload = async ({ file }) => {
  const ext = file?.name?.split('.').pop()?.toLowerCase()
  const allow = ['xlsx', 'xls', 'csv']
  if (!allow.includes(ext)) {
    message.error('仅支持 .xlsx/.xls/.csv 文件')
    return false
  }
  return true
}

/** 上传变更处理（函数级中文注释） */
const handleUploadChange = ({ fileList: fl }) => {
  fileList.value = fl
  selectedFile.value = fl[0]?.file || null
}

/** 移除文件处理（函数级中文注释） */
const handleRemove = () => {
  selectedFile.value = null
  fileList.value = []
}

/** 提交处理（函数级中文注释） */
const handleSubmit = async () => {
  if (!selectedFile.value) {
    message.error('请先选择文件')
    return
  }
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    const submitRes = await api.simiccidSubmit(fd)
    if (submitRes.code === 200) {
      fileKey.value = submitRes?.data?.file_key
      if (fileKey.value) {
        lStorage.set('simiccid_file_key', fileKey.value)
        message.success('任务已提交，正在后台处理')
        startPolling()
      } else {
        message.warning('未获取到任务标识')
      }
    } else {
      message.error(submitRes.msg || '处理失败')
    }
  } catch (e) {
    message.error(e?.message || '请求异常')
  } finally {
    submitting.value = false
  }
}

/** 重置表单（函数级中文注释） */
const handleReset = () => {
  selectedFile.value = null
  fileList.value = []
  fileKey.value = ''
  progress.value = null
  lStorage.remove('simiccid_file_key')
  stopPolling()
}

/** 开始轮询进度（函数级中文注释） */
const startPolling = () => {
  stopPolling()
  timer = setInterval(async () => {
    if (!fileKey.value) return
    try {
      const res = await api.simiccidProgress({ file_key: fileKey.value })
      if (res.code === 200) {
        progress.value = res.data
        if (progress.value?.stage === 'done' || progress.value?.stage === 'failed') {
          stopPolling()
        }
      }
    } catch (e) {
      // 忽略单次错误
    }
  }, 1500)
}

/** 停止轮询（函数级中文注释） */
const stopPolling = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

onMounted(() => {
  const last = lStorage.get('simiccid_file_key')
  if (last) {
    fileKey.value = last
    startPolling()
  }
})

onBeforeUnmount(() => {
  stopPolling()
})

/** 计算属性：步骤索引（函数级中文注释） */
const stepIndex = computed(() => {
  const stage = progress.value?.stage
  if (stage === 'parsing') return 1
  if (stage === 'writing') return 2
  if (stage === 'processing') return 3
  if (stage === 'done' || stage === 'failed') return 4
  return 1
})

/** 计算属性：写入描述（函数级中文注释） */
const progressDescWriting = computed(() => {
  if (!progress.value) return ''
  const { current = 0, total = 0 } = progress.value
  if (total) return `已写入 ${current}/${total}`
  return '写入临时表'
})

/** 计算属性：状态文本与标签（函数级中文注释） */
const statusText = computed(() => {
  const p = progress.value
  if (!p) return '等待中'
  if (p.stage === 'failed') return `失败：${p.message || ''}`
  if (p.stage === 'done') return '完成'
  if (p.stage === 'processing') return '处理中'
  if (p.stage === 'writing') return '写入中'
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
