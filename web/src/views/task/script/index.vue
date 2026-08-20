<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="Python脚本管理" size="small">
        <n-space justify="space-between" class="mb-3">
          <n-space>
            <n-input v-model:value="searchParams.name" clearable placeholder="搜索脚本名称" style="width: 200px" @keyup.enter="handleSearch" />
            <n-select v-model:value="searchParams.status" :options="statusOptions" clearable placeholder="状态" style="width: 120px" />
            <n-button type="primary" @click="handleSearch">搜索</n-button>
            <n-button @click="handleReset">重置</n-button>
          </n-space>
          <n-button type="primary" @click="handleCreate">新建脚本</n-button>
        </n-space>

        <n-data-table
          ref="tableRef"
          v-model:checked-row-keys="checkedRowKeys"
          :row-key="(row) => row.id"
          :columns="columns"
          :data="tableData"
          :loading="loading"
          :pagination="pagination"
          :bordered="false"
          @update:page="handlePageChange"
        />

        <n-space v-if="checkedRowKeys.length > 0" class="mt-3" justify="start">
          <n-text type="info">已选择 {{ checkedRowKeys.length }} 项</n-text>
          <n-button type="error" size="small" @click="handleBatchDelete">批量删除</n-button>
        </n-space>
      </n-card>
    </n-space>

    <!-- 脚本编辑弹窗 -->
    <n-modal v-model:show="showModal" :title="modalTitle" preset="card" style="width: 900px; max-width: 90vw">
      <n-form ref="formRef" :model="formData" :rules="formRules" label-placement="left" :label-width="90">
        <n-form-item label="脚本名称" path="name">
          <n-input v-model:value="formData.name" placeholder="请输入脚本名称" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="formData.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="请输入脚本描述" />
        </n-form-item>
        <n-form-item label="Cron表达式" path="cron">
          <template #label>
            <span style="white-space: nowrap">Cron表达式</span>
          </template>
          <n-input v-model:value="formData.cron" clearable placeholder="示例: 0 9 * * * (留空则不启用定时)" />
        </n-form-item>
        <n-form-item label="状态" path="status">
          <n-switch v-model:value="formData.status">
            <template #checked>启用</template>
            <template #unchecked>禁用</template>
          </n-switch>
        </n-form-item>
        <n-form-item label="脚本内容" path="code">
          <codemirror
            v-model="formData.code"
            placeholder="请输入Python脚本内容"
            :style="{ height: '400px', width: '100%' }"
            :autofocus="true"
            :indent-with-tab="true"
            :tab-size="4"
            :extensions="extensions"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 执行日志弹窗 -->
    <n-modal v-model:show="showLogModal" title="执行日志" preset="card" style="width: 800px; max-width: 90vw">
      <n-data-table
        :columns="logColumns"
        :data="logData"
        :loading="logLoading"
        :pagination="logPagination"
        :bordered="false"
        @update:page="handleLogPageChange"
      />
    </n-modal>

    <!-- 日志详情弹窗 -->
    <n-modal v-model:show="showLogDetailModal" title="日志详情" preset="card" style="width: 800px; max-width: 90vw">
      <n-descriptions :column="2" label-placement="left" bordered size="small">
        <n-descriptions-item label="日志ID">{{ currentLog.id }}</n-descriptions-item>
        <n-descriptions-item label="执行状态">
          <n-tag :type="currentLog.status === 'success' ? 'success' : currentLog.status === 'failed' ? 'error' : 'warning'" size="small">
            {{ currentLog.status === 'success' ? '成功' : currentLog.status === 'failed' ? '失败' : '运行中' }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="开始时间">{{ currentLog.start_time }}</n-descriptions-item>
        <n-descriptions-item label="结束时间">{{ currentLog.end_time || '-' }}</n-descriptions-item>
        <n-descriptions-item label="执行时长">{{ currentLog.duration ? currentLog.duration + '秒' : '-' }}</n-descriptions-item>
      </n-descriptions>
      <n-divider>执行输出</n-divider>
      <n-input :default-value="currentLog.output || '无输出'" type="textarea" :autosize="{ minRows: 10, maxRows: 20 }" readonly />
      <template v-if="currentLog.error">
        <n-divider>错误信息</n-divider>
        <n-input :default-value="currentLog.error" type="textarea" :autosize="{ minRows: 5, maxRows: 10 }" readonly />
      </template>
    </n-modal>
  </CommonPage>
</template>

<script setup>
import { h, ref, reactive, onMounted } from 'vue'
import { useMessage, useDialog, NButton, NSpace, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'

defineOptions({ name: 'Python脚本管理' })

const extensions = [python(), oneDark]

const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const submitting = ref(false)
const tableData = ref([])
const pagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })

const searchParams = reactive({ name: '', status: null })

const statusOptions = [
  { label: '启用', value: true },
  { label: '禁用', value: false },
]

const showModal = ref(false)
const modalTitle = ref('')
const formRef = ref(null)
const formData = reactive({ id: null, name: '', code: '', description: '', status: true, cron: '' })

const formRules = {
  name: [{ required: true, message: '请输入脚本名称' }],
  code: [{ required: true, message: '请输入脚本内容' }],
  cron: [{
    validator(_rule, value) {
      if (!value) return true
      const parts = value.trim().split(/\s+/)
      if (parts.length !== 5 && parts.length !== 6) {
        return new Error('Cron表达式格式错误，请使用5位或6位格式，如: 0 9 * * *')
      }
      return true
    },
    trigger: 'blur',
  }],
}

const showLogModal = ref(false)
const logLoading = ref(false)
const logData = ref([])
const logPagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })
const currentScriptId = ref(null)

const showLogDetailModal = ref(false)
const currentLog = ref({})

const checkedRowKeys = ref([])
const tableRef = ref(null)

const columns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '脚本名称', key: 'name', width: 150 },
  { title: '描述', key: 'description', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render(row) {
      return h(NTag, { type: row.status ? 'success' : 'default', size: 'small' }, { default: () => (row.status ? '启用' : '禁用') })
    },
  },
  { title: 'Cron', key: 'cron', width: 140, render(row) { return row.cron || '-' } },
  { title: '上次执行', key: 'last_run_time', width: 160, render(row) { return row.last_run_time || '-' } },
  { title: '下次执行', key: 'next_run_time', width: 160, render(row) { return row.next_run_time || '-' } },
  { title: '创建时间', key: 'created_at', width: 160 },
  { title: '更新时间', key: 'updated_at', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 280,
    render(row) {
      return h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', type: 'primary', onClick: () => handleViewLog(row) }, { default: () => '日志' }),
          h(NButton, { size: 'small', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'success', onClick: () => handleExecute(row) }, { default: () => '执行' }),
          h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' }),
        ],
      })
    },
  },
]

const logColumns = [
  { title: '日志ID', key: 'id', width: 80 },
  {
    title: '执行状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(NTag, { type: row.status === 'success' ? 'success' : row.status === 'failed' ? 'error' : 'warning', size: 'small' }, { default: () => (row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : '运行中') })
    },
  },
  { title: '开始时间', key: 'start_time', width: 160 },
  { title: '执行时长', key: 'duration', width: 100, render(row) { return row.duration ? row.duration + '秒' : '-' } },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render(row) {
      return h(NButton, { size: 'small', onClick: () => handleViewLogDetail(row) }, { default: () => '详情' })
    },
  },
]

const fetchData = async () => {
  loading.value = true
  try {
    const res = await api.getScriptList({
      page: pagination.page,
      limit: pagination.pageSize,
      name: searchParams.name || undefined,
      status: searchParams.status,
    })
    if (res.code === 200) {
      tableData.value = res.data || []
      pagination.itemCount = res.total || 0
    }
  } catch (e) {
    message.error('获取脚本列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchData()
}

const handleReset = () => {
  searchParams.name = ''
  searchParams.status = null
  pagination.page = 1
  fetchData()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchData()
}

const handleCreate = () => {
  modalTitle.value = '新建脚本'
  formData.id = null
  formData.name = ''
  formData.code = ''
  formData.description = ''
  formData.status = true
  formData.cron = ''
  showModal.value = true
}

const handleEdit = (row) => {
  modalTitle.value = '编辑脚本'
  formData.id = row.id
  formData.name = row.name
  formData.code = row.code
  formData.description = row.description
  formData.status = row.status
  formData.cron = row.cron || ''
  showModal.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value?.validate()
  } catch (e) {
    return
  }

  submitting.value = true
  try {
    if (formData.id) {
      await api.updateScript(formData.id, formData)
      message.success('更新成功')
    } else {
      await api.createScript(formData)
      message.success('创建成功')
    }
    showModal.value = false
    fetchData()
  } catch (e) {
    message.error('保存失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = (row) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除脚本"${row.name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteScript(row.id)
        message.success('删除成功')
        fetchData()
      } catch (e) {
        message.error('删除失败')
      }
    },
  })
}

const handleExecute = (row) => {
  dialog.success({
    title: '确认执行',
    content: `确定要执行脚本"${row.name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await api.executeScript(row.id)
        message.success(res.msg || '开始执行')
      } catch (e) {
        message.error('执行失败')
      }
    },
  })
}

const handleViewLog = (row) => {
  currentScriptId.value = row.id
  logPagination.page = 1
  fetchLogData()
  showLogModal.value = true
}

const fetchLogData = async () => {
  logLoading.value = true
  try {
    const res = await api.getScriptLogs({
      script_id: currentScriptId.value,
      page: logPagination.page,
      limit: logPagination.pageSize,
    })
    if (res.code === 200) {
      logData.value = res.data || []
      logPagination.itemCount = res.total || 0
    }
  } catch (e) {
    message.error('获取日志失败')
  } finally {
    logLoading.value = false
  }
}

const handleLogPageChange = (page) => {
  logPagination.page = page
  fetchLogData()
}

const handleViewLogDetail = (row) => {
  currentLog.value = row
  showLogDetailModal.value = true
}

const handleBatchDelete = () => {
  if (checkedRowKeys.value.length === 0) {
    message.warning('请先选择要删除的脚本')
    return
  }
  dialog.warning({
    title: '确认批量删除',
    content: `确定要删除选中的 ${checkedRowKeys.value.length} 个脚本吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        for (const id of checkedRowKeys.value) {
          await api.deleteScript(id)
        }
        message.success('删除成功')
        checkedRowKeys.value = []
        fetchData()
      } catch (e) {
        message.error('删除失败')
      }
    },
  })
}

onMounted(() => {
  fetchData()
})
</script>
