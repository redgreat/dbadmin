<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button v-if="isAdmin" class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增报表
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
        <QueryBarItem label="系统名称" :label-width="80">
          <n-input
            v-model:value="queryItems.system_name"
            clearable
            type="text"
            placeholder="请输入系统名称"
          />
        </QueryBarItem>
        <QueryBarItem label="报表名称" :label-width="80">
          <n-input
            v-model:value="queryItems.report_name"
            clearable
            type="text"
            placeholder="请输入报表名称"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <!-- 新增/编辑 弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
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
        <n-form-item label="系统名称" path="system_name">
          <n-select
            v-model:value="modalForm.system_name"
            :options="systemNameOptions"
            placeholder="请选择系统名称"
          />
        </n-form-item>
        <n-form-item label="报表名称" path="report_name">
          <n-input v-model:value="modalForm.report_name" clearable placeholder="请输入报表名称" />
        </n-form-item>
        <n-form-item label="SQL语句" path="sql_statement">
          <n-input
            v-model:value="modalForm.sql_statement"
            type="textarea"
            :rows="6"
            placeholder="请输入SQL查询语句（仅支持SELECT）"
          />
        </n-form-item>
        <n-form-item label="数据库连接" path="db_connection_id">
          <n-select
            v-model:value="modalForm.db_connection_id"
            :options="dbConnectionOptions"
            placeholder="请选择数据库连接"
          />
        </n-form-item>
      </n-form>
    </CrudModal>

    <!-- SQL详情弹窗 -->
    <n-modal v-model:show="showSQLModal" preset="card" title="SQL语句详情" style="width: 800px">
      <n-code :code="currentSQL" language="sql" />
    </n-modal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, computed } from 'vue'
import { NButton, NTag, NSpace, NIcon, useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '@/store'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '报表维护' })

const $table = ref(null)
const queryItems = ref({})
const $message = useMessage()
const $dialog = useDialog()
const userStore = useUserStore()

// 判断是否为管理员
const isAdmin = computed(() => userStore.role?.includes('admin'))

// 系统名称选项
const systemNameOptions = ref([])

// 数据库连接选项
const dbConnectionOptions = ref([])

// SQL详情弹窗
const showSQLModal = ref(false)
const currentSQL = ref('')

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '系统名称', key: 'system_name', width: 120 },
  { title: '报表名称', key: 'report_name', width: 150 },
  {
    title: 'SQL语句',
    key: 'sql_statement_short',
    width: 200,
    ellipsis: { tooltip: false },
    render: (row) => {
      return h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: () => showSQLDetail(row.sql_statement)
        },
        { default: () => row.sql_statement_short }
      )
    }
  },
  { title: '数据库连接', key: 'db_connection_name', width: 150 },
  { title: '维护人', key: 'maintainer', width: 100 },
  {
    title: '维护时间',
    key: 'updated_at',
    width: 180,
    render: (row) => row.updated_at || row.created_at
  },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    fixed: 'right',
    render: (row) => {
      const buttons = [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            onClick: () => handleGenerate(row)
          },
          { default: () => '生成' }
        )
      ]

      // 权限控制：管理员或自己维护的报表可以编辑删除
      if (isAdmin.value || row.maintainer === userStore.username) {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'info',
              style: 'margin-left: 8px',
              onClick: () => handleEdit(row)
            },
            { default: () => '编辑' }
          )
        )
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              style: 'margin-left: 8px',
              onClick: () => handleDelete(row)
            },
            { default: () => '删除' }
          )
        )
      }

      return h(NSpace, null, { default: () => buttons })
    }
  }
]

// 表单规则
const rules = {
  system_name: { required: true, message: '请选择系统名称', trigger: 'blur' },
  report_name: { required: true, message: '请输入报表名称', trigger: 'blur' },
  sql_statement: { required: true, message: '请输入SQL语句', trigger: 'blur' },
  db_connection_id: { required: true, type: 'number', message: '请选择数据库连接', trigger: 'blur' }
}

// 获取数据的API
const getData = async (params) => {
  try {
    const res = await api.getReportConfigList(params)
    if (res.code === 200) {
      return { data: res.data, total: res.total }
    } else {
      $message.error(res.msg || '获取数据失败')
      return { data: [], total: 0 }
    }
  } catch (error) {
    console.error('获取报表配置列表失败', error)
    $message.error('获取数据失败')
    return { data: [], total: 0 }
  }
}

// CRUD操作
const {
  modalVisible,
  modalTitle,
  modalLoading,
  modalForm,
  modalFormRef,
  handleAdd,
  handleEdit,
  handleDelete,
  handleSave
} = useCRUD({
  name: '报表配置',
  initForm: {
    system_name: null,
    report_name: '',
    sql_statement: '',
    db_connection_id: null
  },
  doCreate: (data) => api.createReportConfig(data),
  doUpdate: (data) => api.updateReportConfig(data),
  doDelete: (data) => api.deleteReportConfig({ config_id: data.id }),
  refresh: () => $table.value?.refresh()
})

// 刷新数据
const handleRefresh = () => {
  $table.value?.refresh()
}

// 显示SQL详情
const showSQLDetail = (sql) => {
  currentSQL.value = sql
  showSQLModal.value = true
}

// 生成报表
const handleGenerate = (row) => {
  $dialog.warning({
    title: '确认生成',
    content: `确定要生成报表"${row.report_name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await api.generateReport({ config_id: row.id })
        if (res.code === 200) {
          $message.success('生成任务已提交，请到报表生成页面查看进度')
        } else {
          $message.error(res.msg || '生成失败')
        }
      } catch (error) {
        console.error('生成报表失败', error)
        $message.error('生成失败')
      }
    }
  })
}

// 加载系统名称选项
const loadSystemNameOptions = async () => {
  try {
    const res = await api.getSystemNameOptions()
    if (res.code === 200) {
      systemNameOptions.value = res.data
    }
  } catch (error) {
    console.error('获取系统名称选项失败', error)
  }
}

// 加载数据库连接选项
const loadDBConnectionOptions = async () => {
  try {
    const res = await api.getConnList({ page: 1, page_size: 1000 })
    if (res.code === 200) {
      dbConnectionOptions.value = res.data.map((item) => ({
        label: item.name,
        value: item.id
      }))
    }
  } catch (error) {
    console.error('获取数据库连接选项失败', error)
  }
}

onMounted(() => {
  loadSystemNameOptions()
  loadDBConnectionOptions()
})
</script>
