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
        <n-button class="float-right mr-15" type="success" @click="showCronModal">
          <TheIcon icon="mdi:clock-time-four-outline" :size="18" class="mr-5" />Cron表达式
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
            v-model:value="queryItems.name"
            clearable
            type="text"
            placeholder="请输入任务名称"
          />
        </QueryBarItem>
        <QueryBarItem label="任务状态" :label-width="80">
          <n-select
            v-model:value="queryItems.status"
            clearable
            :options="statusOptions"
            placeholder="请选择任务状态"
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
      >
        <n-form-item label="任务名称" path="name">
          <n-input v-model:value="modalForm.name" clearable placeholder="请输入任务名称" />
        </n-form-item>
        <n-form-item label="任务类型" path="type">
          <n-select
            v-model:value="modalForm.type"
            :options="taskTypeOptions"
            placeholder="请选择任务类型"
          />
        </n-form-item>
        <n-form-item label="Cron表达式" path="cron">
          <n-input v-model:value="modalForm.cron" clearable placeholder="请输入Cron表达式" />
        </n-form-item>
        <n-form-item label="执行命令/函数" path="command">
          <n-input v-model:value="modalForm.command" type="textarea" placeholder="请输入执行命令或函数" />
        </n-form-item>
        <n-form-item label="执行目录" path="work_dir">
          <n-input v-model:value="modalForm.work_dir" clearable placeholder="请输入执行目录，如：/home/app" />
        </n-form-item>
        <n-form-item label="执行用户" path="run_user">
          <n-input v-model:value="modalForm.run_user" clearable placeholder="请输入执行用户，如：root" />
        </n-form-item>
        <n-form-item label="环境变量" path="env_vars">
          <n-input v-model:value="modalForm.env_vars" type="textarea" placeholder="请输入环境变量，格式：KEY=VALUE，每行一个" />
        </n-form-item>
        <n-form-item label="参数" path="args">
          <n-input v-model:value="modalForm.args" type="textarea" placeholder="请输入参数，JSON格式" />
        </n-form-item>
        <n-form-item label="超时时间(秒)" path="timeout">
          <n-input-number v-model:value="modalForm.timeout" :min="0" :max="86400" clearable placeholder="任务执行超时时间，0表示不限制" />
        </n-form-item>
        <n-form-item label="最大重试次数" path="max_retries">
          <n-input-number v-model:value="modalForm.max_retries" :min="0" :max="10" clearable placeholder="任务失败后最大重试次数" />
        </n-form-item>
        <n-form-item label="任务状态" path="status">
          <n-switch v-model:value="modalForm.status" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="modalForm.remark" type="textarea" placeholder="请输入备注信息" />
        </n-form-item>
      </n-form>
    </CrudModal>

    <!-- Cron表达式生成器弹窗 -->
    <n-modal
      v-model:show="cronModalVisible"
      title="Cron表达式生成器"
      preset="card"
      style="width: 600px"
    >
      <n-tabs type="line">
        <n-tab-pane name="seconds" tab="秒">
          <n-space vertical>
            <n-radio-group v-model:value="cronParts.seconds.type">
              <n-space>
                <n-radio :value="'*'">每秒</n-radio>
                <n-radio :value="'/'">周期</n-radio>
                <n-radio :value="'-'">区间</n-radio>
                <n-radio :value="','">指定</n-radio>
              </n-space>
            </n-radio-group>

            <template v-if="cronParts.seconds.type === '/'">
              <n-space>
                从第 <n-input-number v-model:value="cronParts.seconds.start" :min="0" :max="59" style="width: 80px" /> 秒开始，每隔
                <n-input-number v-model:value="cronParts.seconds.interval" :min="1" :max="59" style="width: 80px" /> 秒执行一次
              </n-space>
            </template>

            <template v-if="cronParts.seconds.type === '-'">
              <n-space>
                从第 <n-input-number v-model:value="cronParts.seconds.start" :min="0" :max="59" style="width: 80px" /> 秒到第
                <n-input-number v-model:value="cronParts.seconds.end" :min="0" :max="59" style="width: 80px" /> 秒
              </n-space>
            </template>

            <template v-if="cronParts.seconds.type === ','">
              <n-space align="center">
                <span>指定秒数：</span>
                <n-select
                  v-model:value="cronParts.seconds.selected"
                  multiple
                  :options="secondOptions"
                  placeholder="请选择秒数"
                  style="min-width: 300px"
                />
              </n-space>
            </template>
          </n-space>
        </n-tab-pane>

        <!-- 其他选项卡（分钟、小时、日、月、周）类似，此处省略 -->
      </n-tabs>

      <div class="mt-4">
        <n-input v-model:value="generatedCron" readonly placeholder="生成的Cron表达式" />
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="cronModalVisible = false">取消</n-button>
          <n-button type="primary" @click="applyCron">应用</n-button>
        </n-space>
      </template>
    </n-modal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, computed, resolveDirective } from 'vue'
import { NButton, NTag, NSpace, NSwitch } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '定时任务' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 任务状态选项
const statusOptions = [
  { label: '启用', value: true },
  { label: '禁用', value: false },
]

// 任务类型选项
const taskTypeOptions = [
  { label: 'Shell命令', value: 'shell' },
  { label: 'HTTP请求', value: 'http' },
  { label: 'Python函数', value: 'python' },
]

// 模拟获取数据的API
const getData = () => {
  // 这里应该调用真实的API
  return Promise.resolve({
    items: [
      {
        id: 1,
        name: '数据备份',
        type: 'shell',
        cron: '0 0 2 * * ?',
        command: 'backup.sh',
        work_dir: '/home/app/backup',
        run_user: 'appuser',
        env_vars: 'DB_HOST=localhost\nDB_PORT=5432',
        args: '',
        timeout: 3600,
        max_retries: 3,
        status: true,
        lastRunTime: '2023-05-01 02:00:00',
        nextRunTime: '2023-05-02 02:00:00'
      },
      {
        id: 2,
        name: '日志清理',
        type: 'shell',
        cron: '0 0 1 * * ?',
        command: 'clean_logs.sh',
        work_dir: '/var/log',
        run_user: 'root',
        env_vars: 'KEEP_DAYS=30',
        args: '',
        timeout: 1800,
        max_retries: 1,
        status: true,
        lastRunTime: '2023-05-01 01:00:00',
        nextRunTime: '2023-05-02 01:00:00'
      },
      {
        id: 3,
        name: '数据同步',
        type: 'python',
        cron: '0 */30 * * * ?',
        command: 'sync_data.py',
        work_dir: '/home/app/scripts',
        run_user: 'appuser',
        env_vars: 'PYTHONPATH=/home/app\nAPI_KEY=abcdef123456',
        args: '{"type":"full"}',
        timeout: 600,
        max_retries: 2,
        status: false,
        lastRunTime: '2023-04-30 23:30:00',
        nextRunTime: null
      },
    ],
    total: 3,
  })
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '任务名称', key: 'name', width: 150 },
  { title: '任务类型', key: 'type', width: 100 },
  { title: 'Cron表达式', key: 'cron', width: 150 },
  { title: '执行命令/函数', key: 'command', width: 200 },
  { title: '执行目录', key: 'work_dir', width: 150 },
  { title: '执行用户', key: 'run_user', width: 100 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(NSwitch, {
        value: row.status,
        disabled: false,
        onUpdateValue: (value) => {
          // 这里应该调用API更新状态
          console.log(`更新任务 ${row.id} 状态为 ${value}`)
          row.status = value
        }
      })
    },
  },
  { title: '上次执行时间', key: 'lastRunTime', width: 180 },
  { title: '下次执行时间', key: 'nextRunTime', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    fixed: 'right',
    render(row) {
      return h(NSpace, { justify: 'center' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: () => handleEdit(row),
            },
            { default: () => '编辑' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'info',
              onClick: () => handleRunNow(row.id),
            },
            { default: () => '立即执行' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'success',
              onClick: () => handleViewLogs(row.id),
            },
            { default: () => '执行日志' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              onClick: () => handleDelete(row.id),
            },
            { default: () => '删除' }
          ),
        ],
      })
    },
  },
]

// Cron表达式生成器相关
const cronModalVisible = ref(false)
const cronParts = ref({
  seconds: { type: '*', start: 0, interval: 1, end: 59, selected: [] },
  minutes: { type: '*', start: 0, interval: 1, end: 59, selected: [] },
  hours: { type: '*', start: 0, interval: 1, end: 23, selected: [] },
  dayOfMonth: { type: '*', start: 1, interval: 1, end: 31, selected: [] },
  month: { type: '*', start: 1, interval: 1, end: 12, selected: [] },
  dayOfWeek: { type: '*', start: 1, interval: 1, end: 7, selected: [] },
})

// 生成秒选项
const secondOptions = Array.from({ length: 60 }, (_, i) => ({ label: i.toString(), value: i }))

// 生成的Cron表达式
const generatedCron = computed(() => {
  // 简化版，实际应该根据各个部分的选择生成完整的表达式
  return '* * * * * *'
})

// 显示Cron表达式生成器
const showCronModal = () => {
  cronModalVisible.value = true
}

// 应用生成的Cron表达式
const applyCron = () => {
  modalForm.value.cron = generatedCron.value
  cronModalVisible.value = false
}

// 立即执行任务
const handleRunNow = (id) => {
  console.log(`立即执行任务 ${id}`)
  // 这里应该调用API立即执行任务
}

// 查看执行日志
const handleViewLogs = (id) => {
  console.log(`查看任务 ${id} 的执行日志`)
  // 这里应该跳转到日志页面或显示日志弹窗
}

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
  name: '定时任务',
  initForm: {
    name: '',
    type: 'shell',
    cron: '0 0 * * * ?',
    command: '',
    work_dir: '/home/app',
    run_user: 'appuser',
    env_vars: '',
    args: '',
    timeout: 3600,
    max_retries: 3,
    status: true,
    remark: '',
  },
  doCreate: (data) => {
    console.log('创建数据', data)
    return Promise.resolve()
  },
  doUpdate: (data) => {
    console.log('更新数据', data)
    return Promise.resolve()
  },
  doDelete: (id) => {
    console.log('删除数据', id)
    return Promise.resolve()
  },
  refresh: () => $table.value?.handleSearch(),
})

// 刷新数据
const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(() => {
  $table.value?.handleSearch()
})
</script>
