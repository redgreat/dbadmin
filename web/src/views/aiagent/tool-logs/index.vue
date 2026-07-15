<template>
  <CommonPage title="工具调用日志">
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :extra-params="extraParams"
      :scroll-x="1200"
      :columns="columns"
      :get-data="aiApi.listToolLogs"
    >
      <template #queryBar>
        <QueryBarItem label="工具名称" :label-width="70">
          <n-input
            v-model:value="queryItems.tool_name"
            type="text"
            placeholder="请输入工具名称"
            @keydown.enter="$table?.handleSearch"
          />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>

<script setup>
import { ref, h } from 'vue'
import { NInput, NTag, NTooltip } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import aiApi from '@/api/ai'

defineOptions({ name: 'ToolLogsManagement' })

const $table = ref(null)
const queryItems = ref({})
const extraParams = ref({})

const columns = [
  { title: 'ID', key: 'id', width: 80, align: 'center' },
  { title: '工具名称', key: 'tool_name', width: 180, align: 'center' },
  { title: '会话ID', key: 'session_id', width: 150, align: 'center', ellipsis: { tooltip: true } },
  { title: '写操作', key: 'is_write_op', width: 80, align: 'center', render(row) {
    return h(NTag, { type: row.is_write_op ? 'warning' : 'default', size: 'small' }, { default: () => (row.is_write_op ? '是' : '否') })
  } },
  { title: '输入参数', key: 'tool_input', width: 250, ellipsis: { tooltip: true }, render(row) {
    return JSON.stringify(row.tool_input || {})
  } },
  { title: '状态', key: 'status', width: 100, align: 'center', render(row) {
    return h(
      NTag,
      { type: row.status === 'success' ? 'success' : 'error' },
      { default: () => row.status }
    )
  } },
  { title: '耗时(ms)', key: 'duration_ms', width: 100, align: 'center' },
  { title: '错误信息', key: 'error_message', width: 200, ellipsis: { tooltip: true } },
  { title: '调用时间', key: 'timestamp', width: 180, align: 'center' },
]
</script>
