<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建任务
        </n-button>
        <n-button class="float-right mr-15" type="info" @click="handleRefresh">
          <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />刷新数据
        </n-button>
      </div>
    </template>

    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="getData">
      <template #queryBar>
        <QueryBarItem label="任务名称" :label-width="80">
          <n-input v-model:value="queryItems.task_name" clearable placeholder="请输入任务名称" />
        </QueryBarItem>
        <QueryBarItem label="状态" :label-width="80">
          <n-select
            v-model:value="queryItems.status"
            clearable
            :options="statusOptions"
            placeholder="请选择状态"
            style="width: 180px"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal v-model:visible="modalVisible" :title="modalTitle" :loading="modalLoading" @save="handleSave">
      <n-form
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="130"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="任务名称" path="task_name">
          <n-input v-model:value="modalForm.task_name" clearable placeholder="请输入任务名称" />
        </n-form-item>
        <n-form-item label="数据库连接" path="db_connection_id">
          <n-select
            v-model:value="modalForm.db_connection_id"
            :options="connOptions"
            filterable
            placeholder="请选择数据库连接"
          />
        </n-form-item>
        <n-form-item label="发送人" path="sender_id">
          <n-select
            v-model:value="modalForm.sender_id"
            :options="senderOptions"
            filterable
            placeholder="请选择发送人（企业微信群）"
          />
        </n-form-item>
        <n-form-item label="Cron表达式" path="cron">
          <n-input v-model:value="modalForm.cron" clearable placeholder="示例: 0 9 * * *" />
        </n-form-item>
        <n-form-item label="SQL语句" path="sql_statement">
          <n-input
            v-model:value="modalForm.sql_statement"
            type="textarea"
            :rows="5"
            placeholder="仅支持SELECT语句"
          />
        </n-form-item>
        <n-form-item label="模板列" path="template_columns">
          <n-input
            v-model:value="modalForm.template_columns"
            clearable
            placeholder="逗号分隔，如：order_no,sku,total_amount"
          />
        </n-form-item>
        <n-form-item label="消息模板" path="message_template">
          <n-input
            v-model:value="modalForm.message_template"
            type="textarea"
            :rows="4"
            placeholder='支持 {{total}} 或 {total}；支持 {} 顺序替换（按模板列）'
          />
        </n-form-item>
        <n-form-item label="总数占位符" path="total_placeholder">
          <n-input v-model:value="modalForm.total_placeholder" clearable placeholder="默认 {{total}}" />
        </n-form-item>
        <n-form-item label="发送明细Excel" path="send_detail_excel">
          <n-switch v-model:value="modalForm.send_detail_excel" />
        </n-form-item>
        <n-form-item label="启用状态" path="status">
          <n-switch v-model:value="modalForm.status" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="modalForm.remark" type="textarea" :rows="2" placeholder="备注" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref } from 'vue'
import { NButton, NPopconfirm, NSpace, NTag } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: 'SQL预警' })

const $table = ref(null)
const queryItems = ref({
  task_name: '',
  status: null,
})

const connOptions = ref([])
const senderOptions = ref([])

const statusOptions = [
  { label: '启用', value: '1' },
  { label: '禁用', value: '0' },
]

const getData = async (params = {}) => {
  try {
    const query = { ...params }
    if (query.status === '1') query.status = true
    if (query.status === '0') query.status = false
    const response = await api.getSqlAlertTaskList(query)
    return {
      data: response.data || [],
      total: response.total || 0,
    }
  } catch (error) {
    return { data: [], total: 0 }
  }
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '任务名称', key: 'task_name', width: 180 },
  { title: '数据库连接', key: 'db_connection_name', width: 180 },
  { title: '发送人', key: 'sender_name', width: 160 },
  { title: 'Cron', key: 'cron', width: 140 },
  {
    title: '消息模板',
    key: 'message_template',
    width: 260,
    render(row) {
      const value = row.message_template || ''
      const shortValue = value.length > 40 ? `${value.slice(0, 40)}...` : value
      return h('span', { title: value }, shortValue)
    },
  },
  {
    title: '附件',
    key: 'send_detail_excel',
    width: 90,
    render(row) {
      return row.send_detail_excel ? '是' : '否'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(NTag, { type: row.status ? 'success' : 'warning' }, { default: () => (row.status ? '启用' : '禁用') })
    },
  },
  { title: '上次执行', key: 'last_run_time', width: 180 },
  { title: '下次执行', key: 'next_run_time', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    fixed: 'right',
    render(row) {
      return h(NSpace, { justify: 'center' }, {
        default: () => [
          h(NButton, { size: 'small', type: 'primary', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'info', onClick: () => handleExecute(row.id) }, { default: () => '立即执行' }),
          h(
            NPopconfirm,
            { onPositiveClick: () => handleDelete({ task_id: row.id }) },
            {
              trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
              default: () => h('div', {}, '确认删除该任务吗？'),
            }
          ),
        ],
      })
    },
  },
]

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: 'SQL预警任务',
  initForm: {
    task_name: '',
    db_connection_id: null,
    sender_id: null,
    cron: '0 9 * * *',
    sql_statement: '',
    message_template: '告警总数：{{total}}',
    template_columns: '',
    total_placeholder: '{{total}}',
    send_detail_excel: true,
    status: true,
    remark: '',
  },
  doCreate: (data) => api.createSqlAlertTask(data),
  doUpdate: (data) => api.updateSqlAlertTask(data),
  doDelete: (params) => api.deleteSqlAlertTask(params),
  refresh: () => $table.value?.handleSearch(),
})

const rules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: ['input', 'blur'] }],
  db_connection_id: [{ required: true, type: 'number', message: '请选择数据库连接', trigger: ['change'] }],
  sender_id: [{ required: true, type: 'number', message: '请选择发送人', trigger: ['change'] }],
  cron: [{ required: true, message: '请输入Cron表达式', trigger: ['input', 'blur'] }],
  sql_statement: [{ required: true, message: '请输入SQL语句', trigger: ['input', 'blur'] }],
  message_template: [{ required: true, message: '请输入消息模板', trigger: ['input', 'blur'] }],
}

const handleExecute = async (taskId) => {
  await api.executeSqlAlertTask({ task_id: taskId })
  window.$message?.success('任务已开始执行')
}

const loadConnOptions = async () => {
  const res = await api.getConnList({ page: 1, page_size: 1000 })
  connOptions.value = (res.data || []).map((item) => ({
    label: item.name,
    value: item.id,
  }))
}

const loadSenderOptions = async () => {
  const res = await api.getAlertSenderList({ page: 1, page_size: 1000, channel_type: 'wechat_group', is_enabled: true })
  senderOptions.value = (res.data || []).map((item) => ({
    label: item.sender_name,
    value: item.id,
  }))
}

const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(async () => {
  await Promise.all([loadConnOptions(), loadSenderOptions()])
  $table.value?.handleSearch()
})
</script>
