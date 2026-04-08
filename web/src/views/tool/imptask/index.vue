<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增任务
        </n-button>
        <n-button class="float-right mr-15" type="info" @click="handleRefresh">
          <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />刷新数据
        </n-button>
      </div>
    </template>

    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="getData">
      <template #queryBar>
        <QueryBarItem label="任务名称" :label-width="80">
          <n-input
            v-model:value="queryItems.task_name"
            clearable
            type="text"
            placeholder="请输入任务名称"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal
      v-model:visible="modalVisible"
      title="新增Excel导入任务"
      :loading="modalLoading"
      @save="handleSave"
    >
      <n-form
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="100"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="目标连接(可选)" path="target_conn_id">
          <n-select
            v-model:value="modalForm.target_conn_id"
            :options="connOptions"
            clearable
            filterable
            placeholder="可不选；不选则仅生成SQL，不可执行导入"
          />
        </n-form-item>
        <n-form-item label="Excel文件" path="file">
          <n-upload
            :max="1"
            :file-list="fileList"
            :default-upload="false"
            accept=".xlsx,.xls"
            @change="handleUploadChange"
            @remove="handleRemoveFile"
          >
            <n-button>
              <TheIcon icon="material-symbols:upload" :size="18" class="mr-5" />选择文件
            </n-button>
          </n-upload>
          <div v-if="selectedFile" class="mt-10 text-gray-500">
            已选择: {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
          </div>
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, watch, computed } from 'vue'
import { NButton, NTag, NSpace, NProgress, useMessage, NPopconfirm } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'
import { useUserStore } from '@/store'
import { getToken } from '@/utils'

defineOptions({ name: 'Excel导入任务' })

const message = useMessage()
const userStore = useUserStore()

const isAdmin = computed(() => userStore.isSuperUser || userStore.role.includes('admin'))
const $table = ref(null)

const queryItems = ref({ task_name: null })
const connOptions = ref([])

const columns = [
  {
    title: '临时表名',
    key: 'temp_table_name',
    width: 200,
    render: (row) => row.temp_table_name || '-',
  },
  { title: '文件名', key: 'filename', width: 220, ellipsis: { tooltip: true } },
  { title: '目标连接', key: 'target_conn_name', width: 180 },
  {
    title: '数据库类型',
    key: 'db_type',
    width: 120,
    render: (row) => ({ mysql: 'MySQL', postgresql: 'PostgreSQL' }[row.db_type] || row.db_type),
  },
  {
    title: '文件大小',
    key: 'file_size',
    width: 120,
    render: (row) => formatFileSize(row.file_size),
  },
  {
    title: '任务状态',
    key: 'status',
    width: 110,
    render: (row) => {
      const map = {
        pending: { text: '待处理', type: 'default' },
        processing: { text: '处理中', type: 'info' },
        completed: { text: '已完成', type: 'success' },
        failed: { text: '失败', type: 'error' },
      }
      const item = map[row.status] || { text: row.status, type: 'default' }
      return h(NTag, { type: item.type }, { default: () => item.text })
    },
  },
  {
    title: '执行状态',
    key: 'execute_status',
    width: 110,
    render: (row) => {
      const map = {
        pending: { text: '未执行', type: 'default' },
        success: { text: '成功', type: 'success' },
        failed: { text: '失败', type: 'error' },
      }
      const item = map[row.execute_status || 'pending'] || {
        text: row.execute_status || '-',
        type: 'default',
      }
      return h(NTag, { type: item.type }, { default: () => item.text })
    },
  },
  {
    title: '进度',
    key: 'progress',
    width: 170,
    render: (row) => {
      if (row.status === 'completed')
        return h(NProgress, { type: 'line', percentage: 100, status: 'success' })
      if (row.status === 'failed')
        return h(NProgress, { type: 'line', percentage: row.progress || 0, status: 'error' })
      if (row.status === 'processing')
        return h(NProgress, { type: 'line', percentage: row.progress || 0, status: 'info' })
      return h(NProgress, { type: 'line', percentage: 0, status: 'default' })
    },
  },
  { title: '消息', key: 'message', width: 180, ellipsis: { tooltip: true } },
  { title: '创建时间', key: 'created_at', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    fixed: 'right',
    render: (row) => {
      const buttons = []

      if (row.status === 'completed') {
        buttons.push(
          h(
            NButton,
            { size: 'small', type: 'success', onClick: () => handleDownload(row) },
            { default: () => '下载SQL' }
          )
        )
        if (row.target_conn_id) {
          buttons.push(
            h(
              NButton,
              { size: 'small', type: 'primary', onClick: () => handleExecuteImport(row) },
              { default: () => '执行导入' }
            )
          )
        }
      }

      if (isAdmin.value) {
        buttons.push(
          h(
            NPopconfirm,
            { onPositiveClick: () => handleDelete(row) },
            {
              trigger: () =>
                h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
              default: () => '确定删除该任务吗？',
            }
          )
        )
      }

      return h(NSpace, null, { default: () => buttons })
    },
  },
]

const getData = async (params) => {
  const res = await api.getExcelImportTaskList({
    page: params.page,
    page_size: params.page_size,
    task_name: queryItems.value.task_name,
  })
  return { data: res.data.items, total: res.data.total }
}

const { modalVisible, modalLoading, modalForm, modalFormRef, handleAdd, handleDelete } = useCRUD({
  name: '任务',
  initForm: {
    target_conn_id: null,
    file: null,
  },
  doCreate: async (data) => {
    const now = new Date()
    const timestamp =
      now.getFullYear().toString() +
      (now.getMonth() + 1).toString().padStart(2, '0') +
      now.getDate().toString().padStart(2, '0') +
      now.getHours().toString().padStart(2, '0') +
      now.getMinutes().toString().padStart(2, '0') +
      now.getSeconds().toString().padStart(2, '0')

    const fileName = selectedFile.value.name.replace(/\.(xlsx|xls)$/i, '')
    const taskName = `${fileName}_${timestamp}`

    const formData = new FormData()
    formData.append('task_name', taskName)
    if (data.target_conn_id) {
      formData.append('target_conn_id', data.target_conn_id)
    }
    formData.append('file', selectedFile.value)

    const res = await api.createExcelImportTask(formData)
    message.success(res.msg || '任务创建成功')
    return res
  },
  doDelete: async (row) => {
    const res = await api.deleteExcelImportTask(row.id)
    message.success(res.msg || '任务删除成功')
    return res
  },
  refresh: () => $table.value?.handleSearch(),
})

const handleRefresh = () => {
  $table.value?.handleSearch()
}

const fileList = ref([])
const selectedFile = ref(null)

const handleUploadChange = ({ fileList: fl, file }) => {
  fileList.value = fl
  if (file) {
    selectedFile.value = file.file || file
  } else if (fl && fl.length > 0) {
    selectedFile.value = fl[0].file || fl[0]
  } else {
    selectedFile.value = null
  }
}

const handleRemoveFile = () => {
  selectedFile.value = null
  fileList.value = []
}

const rules = {}

const handleSave = async () => {
  try {
    await modalFormRef.value?.validate()
  } catch {
    return
  }

  if (!selectedFile.value) {
    message.error('请选择Excel文件')
    return
  }

  modalLoading.value = true
  try {
    const now = new Date()
    const timestamp =
      now.getFullYear().toString() +
      (now.getMonth() + 1).toString().padStart(2, '0') +
      now.getDate().toString().padStart(2, '0') +
      now.getHours().toString().padStart(2, '0') +
      now.getMinutes().toString().padStart(2, '0') +
      now.getSeconds().toString().padStart(2, '0')

    const fileName = selectedFile.value.name.replace(/\.(xlsx|xls)$/i, '')
    const taskName = `${fileName}_${timestamp}`

    const formData = new FormData()
    formData.append('task_name', taskName)
    if (modalForm.value.target_conn_id) {
      formData.append('target_conn_id', modalForm.value.target_conn_id)
    }
    formData.append('file', selectedFile.value)

    const res = await api.createExcelImportTask(formData)

    modalVisible.value = false
    modalLoading.value = false
    handleRemoveFile()
    message.success(res.msg || '任务已提交，正在后台处理')
    $table.value?.handleSearch()
  } catch (error) {
    modalLoading.value = false
    message.error(error.message || '创建任务失败')
  }
}

const handleDownload = (row) => {
  const token = getToken()
  if (!token) {
    message.error('未登录，请先登录')
    return
  }
  const url = `/api/v1/imptask/download/${row.id}?token=${encodeURIComponent(token)}`
  window.open(url, '_blank')
}

const handleExecuteImport = async (row) => {
  try {
    const res = await api.executeExcelImportTask({ source_type: 'imptask', task_id: row.id })
    if (res?.data?.success === false) {
      message.error(res.msg || '执行失败')
      return
    }
    message.success(res.msg || '执行成功')
    handleRefresh()
  } catch {
    // 全局请求拦截器已弹出错误，避免重复提示
  }
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

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

onMounted(async () => {
  await loadConnOptions()
  $table.value?.handleSearch()
})

watch(modalVisible, (val) => {
  if (!val) {
    handleRemoveFile()
  }
})
</script>
