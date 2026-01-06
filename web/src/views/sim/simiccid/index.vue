<template>
  <CommonPage show-footer title="SIM-ICCID导入">
    <n-form ref="formRef" :model="form" label-placement="left" :label-width="100">
      <n-form-item label="Excel文件" path="file">
        <n-upload
          v-model:file-list="fileList"
          :max="1"
          :default-upload="false"
          :accept="'.xlsx,.xls,.csv'"
          @before-upload="handleBeforeUpload"
          @change="handleUploadChange"
          @remove="handleRemove"
        >
          <n-button type="primary">选择文件</n-button>
        </n-upload>
        <div v-if="selectedFile" class="mt-10">
          <n-tag type="info">文件：{{ selectedFile.name }}（{{ (selectedFile.size / 1024).toFixed(1) }} KB）</n-tag>
        </div>
        <div class="mt-10">
          <a href="/SimICCID.xlsx" download>下载样例文件（SimICCID.xlsx）</a>
        </div>
      </n-form-item>
      <n-space>
        <n-button type="primary" :loading="submitting" :disabled="!selectedFile" @click="handleSubmit">提交处理</n-button>
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

defineOptions({ name: 'SIM-ICCID导入' })

const message = useMessage()
const formRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)
const submitting = ref(false)

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
      message.success(submitRes.msg || '处理成功')
      handleReset()
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
}
</script>
