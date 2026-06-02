<template>
  <CommonPage show-footer>
    <n-space vertical :size="16">
      <n-card title="SIM卡同步" size="small">
        <template #header-extra>
          <n-tag type="info">从仓储中心同步数据到SIM卡中心</n-tag>
        </template>
        <n-form ref="formRef" :model="formData" :rules="rules" label-placement="left" :label-width="120">
          <n-form-item label="入库单号" path="receiptNumbers">
            <n-input
              v-model:value="formData.receiptNumbers"
              type="textarea"
              :autosize="{ minRows: 8, maxRows: 15 }"
              placeholder="输入单个或多个入库单号，每行一个
例如：
RK2024001
RK2024002
RK2024003"
            />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="executing" @click="handleExecute">执行同步</n-button>
            <n-button @click="handleReset">重置</n-button>
          </n-space>
        </n-form>
      </n-card>

      <n-card v-if="taskStatus" title="同步进度" size="small">
        <n-space vertical :size="12">
          <n-descriptions bordered :column="2">
            <n-descriptions-item label="任务ID">
              {{ taskStatus.task_id }}
            </n-descriptions-item>
            <n-descriptions-item label="执行状态">
              <n-tag :type="statusTagType">
                {{ statusText }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="执行方式">
              {{ taskStatus.backend === 'celery' ? 'Celery后台任务' : '本地后台任务' }}
            </n-descriptions-item>
            <n-descriptions-item label="当前阶段">
              {{ taskStatus.message || '-' }}
            </n-descriptions-item>
          </n-descriptions>
          <n-progress
            type="line"
            :percentage="taskStatus.progress || 0"
            :status="taskStatus.status === 'failed' ? 'error' : taskStatus.status === 'success' ? 'success' : 'info'"
          />
        </n-space>
      </n-card>

      <n-card v-if="syncResult" title="同步结果" size="small">
        <n-descriptions bordered :column="2">
          <n-descriptions-item label="同步状态">
            <n-tag :type="syncResult.success ? 'success' : 'error'">
              {{ syncResult.success ? '成功' : '失败' }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="同步消息">
            {{ syncResult.message }}
          </n-descriptions-item>
          <n-descriptions-item label="验证总数">
            {{ syncResult.validation?.total_count || 0 }}
          </n-descriptions-item>
          <n-descriptions-item label="有效单号">
            <n-tag type="success">{{ syncResult.validation?.exists_count || 0 }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="无效单号">
            <n-tag :type="syncResult.validation?.not_exists_count > 0 ? 'warning' : 'default'">
              {{ syncResult.validation?.not_exists_count || 0 }}
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item v-if="syncResult.installed_check" label="已加装设备">
            <n-tag :type="syncResult.installed_check.has_installed ? 'error' : 'success'">
              {{ syncResult.installed_check.installed_count || 0 }} 条
            </n-tag>
          </n-descriptions-item>
          <n-descriptions-item v-if="syncResult.sync_result" label="写入SIM卡">
            <n-tag type="success" size="large">{{ syncResult.sync_result.sim_card_count || 0 }} 张</n-tag>
          </n-descriptions-item>
          <n-descriptions-item v-if="syncResult.sync_result" label="总计写入">
            <n-tag type="info">{{ syncResult.sync_result.total_inserted || 0 }} 条</n-tag>
          </n-descriptions-item>
        </n-descriptions>

        <n-alert
          v-if="syncResult.validation?.not_exists_count > 0"
          type="warning"
          title="不存在的入库单号"
          style="margin-top: 16px"
        >
          <n-ul>
            <n-li v-for="(receipt, index) in syncResult.validation.not_exists" :key="index">
              {{ receipt }}
            </n-li>
          </n-ul>
        </n-alert>

        <n-alert
          v-if="syncResult.sync_result?.inserted_by_table"
          type="info"
          title="各表写入详情"
          style="margin-top: 16px"
        >
          <n-descriptions bordered :column="2" size="small">
            <n-descriptions-item
              v-for="(count, table) in syncResult.sync_result.inserted_by_table"
              :key="table"
              :label="table"
            >
              {{ count }} 条
            </n-descriptions-item>
          </n-descriptions>
        </n-alert>
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: 'SIM卡同步' })

const message = useMessage()

const formRef = ref(null)
const executing = ref(false)
const syncResult = ref(null)
const taskStatus = ref(null)
let pollTimer = null

const formData = ref({
  receiptNumbers: '',
})

const rules = {
  receiptNumbers: [
    { required: true, message: '请输入入库单号' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入入库单号')
        const lines = value
          .split('\n')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!lines.length) return new Error('请输入至少一个入库单号')
        return true
      },
    },
  ],
}

const statusText = computed(() => {
  const status = taskStatus.value?.status
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'running') return '执行中'
  return '排队中'
})

const statusTagType = computed(() => {
  const status = taskStatus.value?.status
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'info'
  return 'default'
})

const stopPolling = () => {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

const handleReset = () => {
  stopPolling()
  formData.value = { receiptNumbers: '' }
  syncResult.value = null
  taskStatus.value = null
  executing.value = false
}

const pollTaskStatus = async (taskId) => {
  try {
    const res = await api.getSimSyncStatus({ task_id: taskId })
    taskStatus.value = res.data

    if (res.data.status === 'success') {
      syncResult.value = res.data.result
      executing.value = false
      message.success(res.data.message || '同步完成')
      return
    }

    if (res.data.status === 'failed') {
      if (res.data.result) {
        syncResult.value = res.data.result
      }
      executing.value = false
      message.warning(res.data.message || '同步失败')
      return
    }

    pollTimer = setTimeout(() => pollTaskStatus(taskId), 2000)
  } catch (e) {
    executing.value = false
    message.error(e.message || '查询同步进度失败')
  }
}

const handleExecute = async () => {
  await formRef.value?.validate()

  stopPolling()
  executing.value = true
  syncResult.value = null
  taskStatus.value = null
  try {
    const res = await api.syncSimCards({ receipt_numbers: formData.value.receiptNumbers })
    taskStatus.value = res.data
    message.success(res.msg || '同步任务已提交')
    pollTaskStatus(res.data.task_id)
  } catch (e) {
    executing.value = false
    message.error(e.message || '请求异常')
  }
}

onBeforeUnmount(stopPolling)
</script>
