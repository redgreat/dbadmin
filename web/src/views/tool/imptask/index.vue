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

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="getData"
    >
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

    <!-- 新增任务弹窗 -->
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
        <n-form-item label="数据库类型" path="db_type">
          <n-select v-model:value="modalForm.db_type" :options="dbTypeOptions" placeholder="请选择数据库类型" />
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
import { NButton, NTag, NSpace, NProgress, useDialog } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'
import { useMessage } from 'naive-ui'
import { useUserStore } from '@/store'
import { getToken } from '@/utils'

const message = useMessage()
const dialog = useDialog()
const userStore = useUserStore()

// 判断是否为管理员
const isAdmin = computed(() => {
  return userStore.isSuperUser || userStore.role.includes('admin')
})

// 表格引用
const $table = ref(null)

// 查询条件
const queryItems = ref({
  task_name: null,
})

// 数据库类型选项
const dbTypeOptions = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
]

// 表格列定义
const columns = [
  {
    title: '任务名称',
    key: 'task_name',
    width: 200,
  },
  {
    title: '文件名',
    key: 'filename',
    width: 250,
    ellipsis: { tooltip: true },
  },
  {
    title: '文件大小',
    key: 'file_size',
    width: 120,
    render: (row) => formatFileSize(row.file_size),
  },
  {
    title: '数据库类型',
    key: 'db_type',
    width: 120,
    render: (row) => {
      const typeMap = { mysql: 'MySQL', postgresql: 'PostgreSQL' }
      return typeMap[row.db_type] || row.db_type
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row) => {
      const statusMap = {
        pending: { text: '待处理', type: 'default' },
        processing: { text: '处理中', type: 'info' },
        completed: { text: '已完成', type: 'success' },
        failed: { text: '失败', type: 'error' },
      }
      const status = statusMap[row.status] || { text: row.status, type: 'default' }
      return h(NTag, { type: status.type }, { default: () => status.text })
    },
  },
  {
    title: '进度',
    key: 'progress',
    width: 200,
    render: (row) => {
      if (row.status === 'pending') {
        return h(NProgress, { type: 'line', percentage: 0, status: 'default' })
      } else if (row.status === 'processing') {
        return h(NProgress, { type: 'line', percentage: row.progress, status: 'info' })
      } else if (row.status === 'completed') {
        return h(NProgress, { type: 'line', percentage: 100, status: 'success' })
      } else {
        return h(NProgress, { type: 'line', percentage: row.progress, status: 'error' })
      }
    },
  },
  {
    title: '消息',
    key: 'message',
    width: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right',
    render: (row) => {
      const buttons = []

      // 下载按钮 - 只有已完成的任务才显示
      if (row.status === 'completed') {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'success',
              onClick: () => handleDownload(row),
            },
            { default: () => '下载' }
          )
        )
      }

      // 删除按钮 - 只有管理员才能看到
      if (isAdmin.value) {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              onClick: () => handleDeleteWithConfirm(row),
            },
            { default: () => '删除' }
          )
        )
      }

      return h(NSpace, null, {
        default: () => buttons,
      })
    },
  },
]

// 获取数据
const getData = async (params) => {
  const res = await api.getExcelImportTaskList({
    page: params.page,
    page_size: params.page_size,
    task_name: queryItems.value.task_name,
  })
  return {
    data: res.data.items,
    total: res.data.total,
  }
}

// CRUD操作
const {
  modalVisible,
  modalLoading,
  modalForm,
  modalFormRef,
  handleAdd,
  handleDelete,
} = useCRUD({
  name: '任务',
  initForm: {
    db_type: 'mysql',
    file: null,
  },
  doCreate: async (data) => {
    // 自动生成任务名称: 文件名_年月日时分秒
    const now = new Date()
    const timestamp = now.getFullYear().toString() +
      (now.getMonth() + 1).toString().padStart(2, '0') +
      now.getDate().toString().padStart(2, '0') +
      now.getHours().toString().padStart(2, '0') +
      now.getMinutes().toString().padStart(2, '0') +
      now.getSeconds().toString().padStart(2, '0')
    
    const fileName = selectedFile.value.name.replace(/\.(xlsx|xls)$/i, '')
    const taskName = `${fileName}_${timestamp}`
    
    const formData = new FormData()
    formData.append('task_name', taskName)
    formData.append('db_type', data.db_type)
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

// 刷新数据
const handleRefresh = () => {
  $table.value?.handleSearch()
}

// 文件上传相关
const fileList = ref([])
const selectedFile = ref(null)

const handleUploadChange = ({ fileList: fl, file }) => {
  console.log('文件选择变更:', { fileList: fl, file })
  fileList.value = fl

  // 获取文件对象
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

const handleRemoveFile = () => {
  selectedFile.value = null
  fileList.value = []
}

// 表单验证规则
const rules = {
  db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
}

// 保存任务
const handleSave = async () => {
  try {
    await modalFormRef.value?.validate()
  } catch (errors) {
    // 表单验证失败,errors 是错误数组
    console.log('表单验证失败:', errors)
    return
  }

  if (!selectedFile.value) {
    message.error('请选择Excel文件')
    return
  }

  modalLoading.value = true
  try {
    // 自动生成任务名称: 文件名_年月日时分秒
    const now = new Date()
    const timestamp = now.getFullYear().toString() +
      (now.getMonth() + 1).toString().padStart(2, '0') +
      now.getDate().toString().padStart(2, '0') +
      now.getHours().toString().padStart(2, '0') +
      now.getMinutes().toString().padStart(2, '0') +
      now.getSeconds().toString().padStart(2, '0')

    const fileName = selectedFile.value.name.replace(/\.(xlsx|xls)$/i, '')
    const taskName = `${fileName}_${timestamp}`

    const formData = new FormData()
    formData.append('task_name', taskName)
    formData.append('db_type', modalForm.value.db_type)
    formData.append('file', selectedFile.value)

    // 提交任务
    const res = await api.createExcelImportTask(formData)

    // 立即关闭弹窗并提示
    modalVisible.value = false
    modalLoading.value = false
    handleRemoveFile()
    message.success(res.msg || '任务已提交,正在后台处理')

    // 刷新任务列表
    $table.value?.handleSearch()
  } catch (error) {
    modalLoading.value = false
    message.error(error.message || '创建任务失败')
  }
}

// 查看任务详情
const handleView = async (row) => {
  const res = await api.getExcelImportTaskDetail(row.id)
  message.info(`任务状态: ${res.data.status}, 进度: ${res.data.progress}%`)
}

// 下载SQL文件
const handleDownload = (row) => {
  // 获取token
  const token = getToken()
  if (!token) {
    message.error('未登录，请先登录')
    return
  }
  
  // 构造带token的下载URL
  const url = `/api/v1/imptask/download/${row.id}?token=${encodeURIComponent(token)}`
  window.open(url, '_blank')
}

// 删除任务（带确认弹框）
const handleDeleteWithConfirm = (row) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除任务"${row.task_name}"吗？此操作不可恢复。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: () => {
      handleDelete(row)
    },
  })
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

onMounted(() => {
  // 初始化加载数据
  $table.value?.handleSearch()
})

// 清理定时器
watch(modalVisible, (val) => {
  if (!val) {
    handleRemoveFile()
  }
})
</script>
