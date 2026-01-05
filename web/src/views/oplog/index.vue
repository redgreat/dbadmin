<template>
  <CommonPage show-footer>
    <template #action>
      <div>
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
        <QueryBarItem label="修改类型" :label-width="80">
          <n-input
            v-model:value="queryItems.logger"
            clearable
            type="text"
            placeholder="请输入修改类型"
          />
        </QueryBarItem>
        <QueryBarItem label="操作人" :label-width="80">
          <n-input
            v-model:value="queryItems.operater"
            clearable
            type="text"
            placeholder="请输入操作人"
          />
        </QueryBarItem>
        <QueryBarItem label="开始时间" :label-width="80">
          <n-date-picker
            v-model:value="queryItems.start_date"
            type="datetime"
            clearable
            placeholder="请选择开始时间"
            format="yyyy-MM-dd HH:mm:ss"
          />
        </QueryBarItem>
        <QueryBarItem label="结束时间" :label-width="80">
          <n-date-picker
            v-model:value="queryItems.end_date"
            type="datetime"
            clearable
            placeholder="请选择结束时间"
            format="yyyy-MM-dd HH:mm:ss"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <!-- 运维内容详情弹窗 -->
    <n-modal
      v-model:show="detailModalVisible"
      title="运维内容详情"
      preset="card"
      style="width: 800px; max-height: 600px"
    >
      <n-scrollbar style="max-height: 500px">
        <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; background: #2d3748; color: #e2e8f0; padding: 16px; border-radius: 4px;">{{ JSON.stringify(selectedOplogContent, null, 2) }}</pre>
      </n-scrollbar>
      <template #footer>
        <n-space justify="end">
          <n-button @click="detailModalVisible = false">关闭</n-button>
        </n-space>
      </template>
    </n-modal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, computed, resolveDirective } from 'vue'
import { NButton, NTag, NSpace, NDatePicker } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import api from '@/api'

defineOptions({ name: '运维日志' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 运维内容详情弹窗
const detailModalVisible = ref(false)
const selectedOplogContent = ref({})

// 格式化时间
const formatDateTime = (timestamp) => {
  if (!timestamp) return ''
  if (typeof timestamp === 'number') {
    return new Date(timestamp).toISOString().replace('T', ' ').slice(0, 19)
  }
  return timestamp
}

// 获取运维日志数据
const getData = async (params = {}) => {
  try {
    const queryParams = { ...params }
    if (queryParams.start_date && typeof queryParams.start_date === 'number') {
      queryParams.start_date = formatDateTime(queryParams.start_date)
    }
    if (queryParams.end_date && typeof queryParams.end_date === 'number') {
      queryParams.end_date = formatDateTime(queryParams.end_date)
    }
    
    const response = await api.getOpLogList(queryParams)
    return {
      data: response.data.records || [],
      total: response.data.pagination?.total || 0,
    }
  } catch (error) {
    console.error('获取运维日志失败:', error)
    return {
      data: [],
      total: 0,
    }
  }
}

// 查看运维内容详情
const handleViewContent = (row) => {
  selectedOplogContent.value = row.chgmsg || {}
  detailModalVisible.value = true
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '修改类型', key: 'logger', width: 150 },
  { title: '操作人', key: 'operater', width: 120 },
  { 
    title: '运维内容', 
    key: 'chgmsg', 
    width: 200,
    render(row) {
      const content = typeof row.chgmsg === 'object' ? JSON.stringify(row.chgmsg) : row.chgmsg
      const shortContent = content && content.length > 50 ? content.substring(0, 50) + '...' : content
      return h('span', { title: content }, shortContent || '-')
    }
  },
  { 
    title: '最终修改时间', 
    key: 'final_modify_time', 
    width: 180,
    render(row) {
      return formatDateTime(row.final_modify_time)
    }
  },
  { 
    title: '创建时间', 
    key: 'created_at', 
    width: 180,
    render(row) {
      return formatDateTime(row.created_at)
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right',
    render(row) {
      return h(NSpace, { justify: 'center' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: () => handleViewContent(row),
            },
            { default: () => '查看详情' }
          ),
        ],
      })
    },
  },
]



// 刷新数据
const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(() => {
  $table.value?.handleSearch()
})
</script>
