<template>
  <CommonPage show-footer>
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="100">
      <n-form-item label="人员工号" path="codesText">
        <n-input
          v-model:value="form.codesText"
          type="textarea"
          :autosize="{ minRows: 5, maxRows: 10 }"
          clearable
          placeholder="请输入人员工号，多个工号可用逗号或换行分隔"
        />
      </n-form-item>
      <n-form-item label="修改时间" path="entryTime">
        <n-date-picker v-model:value="form.entryTime" type="datetime" clearable placeholder="请选择入职时间" />
      </n-form-item>
      <n-space>
        <n-button type="primary" :loading="executing" @click="handleExecute">执行</n-button>
        <n-button :loading="validating" @click="handleValidate">验证</n-button>
        <n-button @click="handleReset">重置</n-button>
      </n-space>
    </n-form>

    <n-divider />

    <n-data-table
      v-if="results.length > 0"
      :columns="columns"
      :data="results"
      :bordered="false"
      size="small"
      :pagination="{ pageSize: 20 }"
    />
    <n-empty v-else description="暂无验证结果" />
  </CommonPage>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import { NTag, useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'
import dayjs from 'dayjs'

defineOptions({ name: '修改入职时间' })

const message = useMessage()
const formRef = ref(null)
const form = ref({ codesText: '', entryTime: null })
const results = ref([])
const validating = ref(false)
const executing = ref(false)

const codes = computed(() =>
  form.value.codesText
    .split(/[\n,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
)

const rules = {
  codesText: [
    {
      validator: () => {
        if (!codes.value.length) return new Error('请输入人员工号')
        return true
      },
    },
  ],
  entryTime: [{ required: true, message: '请选择修改时间' }],
}

const columns = [
  { title: '工号', key: 'code', width: 140 },
  {
    title: '库',
    key: 'source',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { type: row.source === 'OA' ? 'success' : 'info', size: 'small', bordered: false },
        { default: () => row.source }
      ),
  },
  { title: '表', key: 'table', minWidth: 220 },
  { title: '人员/入职Id', key: 'user_id', minWidth: 260 },
  { title: '当前入职时间', key: 'entry_time', minWidth: 180 },
]

const buildPayload = (includeTime = false) => {
  const payload = { codes: codes.value }
  if (includeTime) {
    payload.positive_time = dayjs(form.value.entryTime).tz('Asia/Shanghai').format('YYYY-MM-DDTHH:mm:ss')
  }
  return payload
}

const applyValidationResult = (data) => {
  results.value = data?.rows || []
  const notFound = data?.not_found_codes || []
  if (notFound.length > 0) {
    message.warning(`未在OA库找到：${notFound.join(', ')}`)
  } else if (results.value.length > 0) {
    message.success('验证完成')
  } else {
    message.warning('未查询到验证结果')
  }
}

const handleValidate = async () => {
  if (!codes.value.length) {
    message.error('请输入人员工号')
    return
  }
  validating.value = true
  try {
    const res = await api.validateOaEntryTime(buildPayload())
    if (res.code === 200) {
      applyValidationResult(res.data)
    } else {
      message.error(res.msg || '验证失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    validating.value = false
  }
}

const handleExecute = async () => {
  await formRef.value?.validate()
  executing.value = true
  try {
    const res = await api.executeOaEntryTime(buildPayload(true))
    if (res.code === 200) {
      const data = res.data || {}
      results.value = data.validation?.rows || []
      const notFound = data.not_found_codes || []
      if (notFound.length > 0) {
        message.warning(`执行完成，未找到：${notFound.join(', ')}`)
      } else {
        message.success('执行完成')
      }
    } else {
      message.error(res.msg || '执行失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    executing.value = false
  }
}

const handleReset = () => {
  form.value = { codesText: '', entryTime: null }
  results.value = []
}
</script>
