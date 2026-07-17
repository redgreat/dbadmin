<template>
  <CommonPage show-footer title="MCP 工具管理">
    <n-data-table
      :loading="loading"
      :columns="columns"
      :data="tableData"
      :scroll-x="1000"
      :row-key="(row) => row.name"
    />
  </CommonPage>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import aiApi from '@/api/ai'

defineOptions({ name: 'McpToolsManagement' })

const loading = ref(false)
const tableData = ref([])

const columns = [
  { title: '工具名称', key: 'name', width: 200, align: 'center', fixed: 'left' },
  { title: '描述', key: 'description', width: 350, align: 'left' },
  {
    title: '是否写操作',
    key: 'is_write',
    width: 120,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_write ? 'warning' : 'info' },
        { default: () => (row.is_write ? '是' : '否') }
      )
    },
  },
  { 
    title: '参数 Schema', 
    key: 'inputSchema', 
    width: 400, 
    align: 'left',
    ellipsis: { tooltip: true },
    render(row) {
      return JSON.stringify(row.inputSchema || {})
    }
  },
]

async function loadData() {
  loading.value = true
  try {
    const res = await aiApi.listMcpTools()
    tableData.value = res.data || []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
