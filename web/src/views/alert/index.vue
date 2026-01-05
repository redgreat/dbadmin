<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建预警
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
        <QueryBarItem label="预警标题" :label-width="80">
          <n-input
            v-model:value="queryItems.title"
            clearable
            type="text"
            placeholder="请输入预警标题"
          />
        </QueryBarItem>
        <QueryBarItem label="预警级别" :label-width="80">
          <n-select
            v-model:value="queryItems.level"
            clearable
            :options="levelOptions"
            placeholder="请选择预警级别"
          />
        </QueryBarItem>
        <QueryBarItem label="预警状态" :label-width="80">
          <n-select
            v-model:value="queryItems.status"
            clearable
            :options="statusOptions"
            placeholder="请选择预警状态"
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
        :label-width="80"
        :model="modalForm"
      >
        <n-form-item label="预警标题" path="title">
          <n-input v-model:value="modalForm.title" clearable placeholder="请输入预警标题" />
        </n-form-item>
        <n-form-item label="预警内容" path="content">
          <n-input v-model:value="modalForm.content" type="textarea" placeholder="请输入预警内容" />
        </n-form-item>
        <n-form-item label="预警级别" path="level">
          <n-select
            v-model:value="modalForm.level"
            :options="levelOptions"
            placeholder="请选择预警级别"
          />
        </n-form-item>
        <n-form-item label="预警类型" path="type">
          <n-select
            v-model:value="modalForm.type"
            :options="typeOptions"
            placeholder="请选择预警类型"
          />
        </n-form-item>
        <n-form-item label="预警状态" path="status">
          <n-select
            v-model:value="modalForm.status"
            :options="statusOptions"
            placeholder="请选择预警状态"
          />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, resolveDirective } from 'vue'
import { NButton, NTag, NSpace } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '预警信息' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 预警级别选项
const levelOptions = [
  { label: '低', value: 'low', color: 'info' },
  { label: '中', value: 'medium', color: 'warning' },
  { label: '高', value: 'high', color: 'error' },
]

// 预警类型选项
const typeOptions = [
  { label: '系统异常', value: 'system' },
  { label: '数据异常', value: 'data' },
  { label: '安全警告', value: 'security' },
  { label: '性能问题', value: 'performance' },
  { label: '其他', value: 'other' },
]

// 预警状态选项
const statusOptions = [
  { label: '未处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已解决', value: 'resolved' },
  { label: '已忽略', value: 'ignored' },
]

// 模拟获取数据的API
const getData = () => {
  // 这里应该调用真实的API
  return Promise.resolve({
    items: [
      { id: 1, title: '数据库连接异常', content: '数据库连接超时，请检查网络连接', level: 'high', type: 'system', status: 'pending', createTime: '2023-05-01 10:00:00' },
      { id: 2, title: '磁盘空间不足', content: '服务器磁盘空间不足，请及时清理', level: 'medium', type: 'performance', status: 'processing', createTime: '2023-05-02 11:00:00' },
      { id: 3, title: '异常登录尝试', content: '检测到多次异常登录尝试，可能存在安全风险', level: 'high', type: 'security', status: 'resolved', createTime: '2023-05-03 12:00:00' },
    ],
    total: 3,
  })
}

// 获取级别标签类型
const getLevelType = (level) => {
  const option = levelOptions.find(item => item.value === level)
  return option ? option.color : 'default'
}

// 获取状态标签类型
const getStatusType = (status) => {
  const map = {
    'pending': 'error',
    'processing': 'warning',
    'resolved': 'success',
    'ignored': 'info',
  }
  return map[status] || 'default'
}

// 获取状态标签文本
const getStatusText = (status) => {
  const option = statusOptions.find(item => item.value === status)
  return option ? option.label : '未知状态'
}

// 获取类型文本
const getTypeText = (type) => {
  const option = typeOptions.find(item => item.value === type)
  return option ? option.label : '未知类型'
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '预警标题', key: 'title', width: 200 },
  { title: '预警内容', key: 'content', width: 300 },
  {
    title: '预警级别',
    key: 'level',
    width: 100,
    render(row) {
      const option = levelOptions.find(item => item.value === row.level)
      return h(
        NTag,
        { type: getLevelType(row.level) },
        { default: () => option ? option.label : '未知级别' }
      )
    },
  },
  {
    title: '预警类型',
    key: 'type',
    width: 120,
    render(row) {
      return h('span', null, getTypeText(row.type))
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: getStatusType(row.status) },
        { default: () => getStatusText(row.status) }
      )
    },
  },
  { title: '创建时间', key: 'createTime', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 200,
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
  name: '预警',
  initForm: {
    title: '',
    content: '',
    level: 'medium',
    type: 'system',
    status: 'pending',
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
