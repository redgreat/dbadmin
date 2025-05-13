<template>
  <div class="p-4">
    <n-card title="审计日志">
      <!-- 查询表单 -->
      <n-space vertical>
        <n-form inline :model="searchForm" label-placement="left" label-width="auto">
          <n-form-item label="用户名称">
            <n-input v-model:value="searchForm.username" placeholder="请输入用户名称" clearable />
          </n-form-item>
          <n-form-item label="功能模块">
            <n-input v-model:value="searchForm.module" placeholder="请输入功能模块" clearable />
          </n-form-item>
          <n-form-item label="请求方法">
            <n-select
              v-model:value="searchForm.method"
              :options="methodOptions"
              placeholder="请选择请求方法"
              clearable
              style="min-width: 120px"
            />
          </n-form-item>
          <n-form-item label="状态码">
            <n-input-number v-model:value="searchForm.status" placeholder="请输入状态码" clearable />
          </n-form-item>
          <n-form-item label="时间范围">
            <n-date-picker
              v-model:value="dateRange"
              type="datetimerange"
              clearable
              :shortcuts="dateShortcuts"
            />
          </n-form-item>
          <n-form-item>
            <n-space>
              <n-button type="primary" @click="handleSearch">查询</n-button>
              <n-button @click="handleReset">重置</n-button>
            </n-space>
          </n-form-item>
        </n-form>

        <!-- 数据表格 -->
        <n-data-table
          remote
          :columns="columns"
          :data="tableData"
          :loading="loading"
          :pagination="pagination"
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </n-space>
    </n-card>
  </div>
</template>

<script setup>
import { h, ref, computed } from 'vue'
import auditlogApi from '@/api/auditlog'
import { useMessage } from 'naive-ui'

const message = useMessage()

// 搜索表单数据
const searchForm = ref({
  username: '',
  module: '',
  method: null,
  status: null,
  summary: '',
})

// 日期范围
const dateRange = ref(null)

// 请求方法选项
const methodOptions = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
]

// 日期快捷选项
const dateShortcuts = {
  今天: () => {
    const now = new Date()
    const start = new Date(now.setHours(0, 0, 0, 0))
    const end = new Date(now.setHours(23, 59, 59, 999))
    return [start, end]
  },
  最近三天: () => {
    const now = new Date()
    const start = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000)
    start.setHours(0, 0, 0, 0)
    const end = new Date(now.setHours(23, 59, 59, 999))
    return [start, end]
  },
  最近一周: () => {
    const now = new Date()
    const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    start.setHours(0, 0, 0, 0)
    const end = new Date(now.setHours(23, 59, 59, 999))
    return [start, end]
  },
}

// 表格列定义
const columns = [
  { title: '用户名称', key: 'username' },
  { title: '功能模块', key: 'module' },
  { title: '接口描述', key: 'summary' },
  { title: '请求方法', key: 'method' },
  { title: '请求路径', key: 'path' },
  { title: '状态码', key: 'status' },
  { 
    title: '响应时间(ms)',
    key: 'response_time',
    render(row) {
      return h('span', {
        style: {
          color: row.response_time > 1000 ? 'red' : 'inherit'
        }
      }, row.response_time)
    }
  },
  { 
    title: '操作时间',
    key: 'created_at',
    render(row) {
      return new Date(row.created_at).toLocaleString()
    }
  },
]

// 表格数据
const tableData = ref([])
const loading = ref(false)
const pagination = ref({
  page: 1,
  pageSize: 10,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 30, 40]
})

// 加载表格数据
const loadTableData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      ...searchForm.value
    }
    if (dateRange.value?.[0] && dateRange.value?.[1]) {
      params.start_time = dateRange.value[0].toISOString()
      params.end_time = dateRange.value[1].toISOString()
    }
    const { data, total } = await auditlogApi.getAuditLogs(params)
    tableData.value = data
    pagination.value.itemCount = total
  } catch (error) {
    message.error('加载数据失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 处理查询
const handleSearch = () => {
  pagination.value.page = 1
  loadTableData()
}

// 处理重置
const handleReset = () => {
  searchForm.value = {
    username: '',
    module: '',
    method: null,
    status: null,
    summary: '',
  }
  dateRange.value = null
  handleSearch()
}

// 处理页码变化
const handlePageChange = (page) => {
  pagination.value.page = page
  loadTableData()
}

// 处理每页数量变化
const handlePageSizeChange = (pageSize) => {
  pagination.value.pageSize = pageSize
  pagination.value.page = 1
  loadTableData()
}

// 初始加载
loadTableData()
</script>

<style scoped>
.n-date-picker {
  width: 320px;
}
</style>
