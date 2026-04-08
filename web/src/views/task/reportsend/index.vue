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
        :label-width="120"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="任务名称" path="task_name">
          <n-input v-model:value="modalForm.task_name" clearable placeholder="请输入任务名称" />
        </n-form-item>
        <n-form-item label="报表配置" path="report_config_id">
          <n-select
            v-model:value="modalForm.report_config_id"
            :options="reportConfigOptions"
            filterable
            placeholder="请选择报表配置"
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
        <n-form-item path="message_template">
          <template #label>
            <span class="inline-flex items-center gap-6px">
              消息模板
              <n-popover trigger="click" placement="right-start" style="max-width: 620px">
                <template #trigger>
                  <n-button text type="info" size="tiny" style="padding: 0 2px">
                    <TheIcon icon="material-symbols:help-outline-rounded" :size="16" />
                  </n-button>
                </template>
                <div style="line-height: 1.7; white-space: pre-line">
                  <div>可用占位符：</div>
                  <div>1. &#123;&#123;date&#125;&#125;：当日日期（yyyyMMdd）</div>
                  <div>2. &#123;&#123;time&#125;&#125;：当前时间（HHmm）</div>
                  <div>3. &#123;&#123;month&#125;&#125;：当月（yyyyMM）</div>
                  <div>4. &#123;&#123;report_name&#125;&#125;：报表名称</div>
                  <div>示例：</div>
                  <div>仓储出库明细_&#123;&#123;date&#125;&#125;_&#123;&#123;time&#125;&#125;</div>
                  <div>渲染后：[仓储出库明细_20260407_1635]</div>
                  <div>仓储出库明细_&#123;&#123;month&#125;&#125;</div>
                  <div>渲染后：[仓储出库明细_202603]</div>
                </div>
              </n-popover>
            </span>
          </template>
          <n-input
            v-model:value="modalForm.message_template"
            type="textarea"
            :rows="3"
            placeholder="可留空；支持 {{date}} {{time}} {{month}} {{report_name}}"
          />
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
import { NButton, NPopconfirm, NPopover, NSpace, NTag } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '定时报表发送' })

const $table = ref(null)
const queryItems = ref({
  task_name: '',
  status: null,
})

const reportConfigOptions = ref([])
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
    const response = await api.getReportSendTaskList(query)
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
  { title: '报表', key: 'report_config_name', width: 220 },
  { title: '发送人', key: 'sender_name', width: 160 },
  { title: 'Cron', key: 'cron', width: 140 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: row.status ? 'success' : 'warning' },
        { default: () => (row.status ? '启用' : '禁用') }
      )
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
      return h(
        NSpace,
        { justify: 'center' },
        {
          default: () => [
            h(
              NButton,
              { size: 'small', type: 'primary', onClick: () => handleEdit(row) },
              { default: () => '编辑' }
            ),
            h(
              NButton,
              { size: 'small', type: 'info', onClick: () => handleExecute(row.id) },
              { default: () => '立即执行' }
            ),
            h(
              NPopconfirm,
              { onPositiveClick: () => handleDelete({ task_id: row.id }) },
              {
                trigger: () =>
                  h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
                default: () => h('div', {}, '确认删除该任务吗？'),
              }
            ),
          ],
        }
      )
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
  name: '定时报表发送任务',
  initForm: {
    task_name: '',
    report_config_id: null,
    sender_id: null,
    cron: '0 9 * * *',
    message_template: '',
    status: true,
    remark: '',
  },
  doCreate: (data) => api.createReportSendTask(data),
  doUpdate: (data) => api.updateReportSendTask(data),
  doDelete: (params) => api.deleteReportSendTask(params),
  refresh: () => $table.value?.handleSearch(),
})

const rules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: ['input', 'blur'] }],
  report_config_id: [
    { required: true, type: 'number', message: '请选择报表配置', trigger: ['change'] },
  ],
  sender_id: [{ required: true, type: 'number', message: '请选择发送人', trigger: ['change'] }],
  cron: [{ required: true, message: '请输入Cron表达式', trigger: ['input', 'blur'] }],
}

const handleExecute = async (taskId) => {
  await api.executeReportSendTask({ task_id: taskId })
  window.$message?.success('任务已开始执行')
}

const loadReportConfigOptions = async () => {
  const res = await api.getReportConfigList({ page: 1, page_size: 1000 })
  reportConfigOptions.value = (res.data || []).map((item) => ({
    label: `${item.system_name} / ${item.report_name}`,
    value: item.id,
  }))
}

const loadSenderOptions = async () => {
  const res = await api.getAlertSenderList({
    page: 1,
    page_size: 1000,
    channel_type: 'wechat_group',
    is_enabled: true,
  })
  senderOptions.value = (res.data || []).map((item) => ({
    label: item.sender_name,
    value: item.id,
  }))
}

const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(async () => {
  await Promise.all([loadReportConfigOptions(), loadSenderOptions()])
  $table.value?.handleSearch()
})
</script>
