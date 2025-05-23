<template>
  <CommonPage show-footer title="订单完成时间修改">
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增修改
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
        <QueryBarItem label="订单编号" :label-width="80">
          <n-input
            v-model:value="queryItems.orderNo"
            clearable
            type="text"
            placeholder="请输入订单编号"
          />
        </QueryBarItem>
        <QueryBarItem label="客户名称" :label-width="80">
          <n-input
            v-model:value="queryItems.customerName"
            clearable
            type="text"
            placeholder="请输入客户名称"
          />
        </QueryBarItem>
        <QueryBarItem label="订单状态" :label-width="80">
          <n-select
            v-model:value="queryItems.status"
            clearable
            :options="statusOptions"
            placeholder="请选择订单状态"
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
        <n-form-item label="订单编号" path="orderNo">
          <n-input v-model:value="modalForm.orderNo" clearable placeholder="请输入订单编号" />
        </n-form-item>
        <n-form-item label="客户名称" path="customerName">
          <n-input v-model:value="modalForm.customerName" clearable placeholder="请输入客户名称" />
        </n-form-item>
        <n-form-item label="联系电话" path="phone">
          <n-input v-model:value="modalForm.phone" clearable placeholder="请输入联系电话" />
        </n-form-item>
        <n-form-item label="订单金额" path="amount">
          <n-input-number v-model:value="modalForm.amount" clearable placeholder="请输入订单金额" />
        </n-form-item>
        <n-form-item label="订单状态" path="status">
          <n-select
            v-model:value="modalForm.status"
            :options="statusOptions"
            placeholder="请选择订单状态"
          />
        </n-form-item>
        <n-form-item label="原完成时间" path="originalCompleteTime">
          <n-date-picker
            v-model:value="modalForm.originalCompleteTime"
            type="datetime"
            clearable
            placeholder="请选择原完成时间"
          />
        </n-form-item>
        <n-form-item label="新完成时间" path="newCompleteTime">
          <n-date-picker
            v-model:value="modalForm.newCompleteTime"
            type="datetime"
            clearable
            placeholder="请选择新完成时间"
          />
        </n-form-item>
        <n-form-item label="修改原因" path="reason">
          <n-input v-model:value="modalForm.reason" type="textarea" placeholder="请输入修改原因" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="modalForm.remark" type="textarea" placeholder="请输入备注信息" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, resolveDirective } from 'vue'
import { NButton, NTag, NSpace, NDatePicker } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '订单完成时间修改' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 订单状态选项
const statusOptions = [
  { label: '待付款', value: 0 },
  { label: '已付款', value: 1 },
  { label: '已发货', value: 2 },
  { label: '已完成', value: 3 },
  { label: '已取消', value: 4 },
]

// 模拟获取数据的API
const getData = () => {
  // 这里应该调用真实的API
  return Promise.resolve({
    items: [
      {
        id: 1,
        orderNo: 'ORD20230001',
        customerName: '张三',
        phone: '13800138000',
        amount: 1000,
        status: 3,
        originalCompleteTime: '2023-05-05 10:00:00',
        newCompleteTime: '2023-05-10 15:30:00',
        reason: '客户要求延迟完成时间',
        modifyTime: '2023-05-04 14:20:00'
      },
      {
        id: 2,
        orderNo: 'ORD20230002',
        customerName: '李四',
        phone: '13900139000',
        amount: 2000,
        status: 3,
        originalCompleteTime: '2023-05-15 09:30:00',
        newCompleteTime: '2023-05-18 11:00:00',
        reason: '物流延迟',
        modifyTime: '2023-05-14 16:45:00'
      },
      {
        id: 3,
        orderNo: 'ORD20230003',
        customerName: '王五',
        phone: '13700137000',
        amount: 3000,
        status: 3,
        originalCompleteTime: '2023-05-20 14:00:00',
        newCompleteTime: '2023-05-19 10:00:00',
        reason: '提前完成',
        modifyTime: '2023-05-18 09:15:00'
      },
    ],
    total: 3,
  })
}

// 获取状态标签类型
const getStatusType = (status) => {
  const map = {
    0: 'warning',
    1: 'info',
    2: 'processing',
    3: 'success',
    4: 'error',
  }
  return map[status] || 'default'
}

// 获取状态标签文本
const getStatusText = (status) => {
  const map = {
    0: '待付款',
    1: '已付款',
    2: '已发货',
    3: '已完成',
    4: '已取消',
  }
  return map[status] || '未知状态'
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '订单编号', key: 'orderNo', width: 150 },
  { title: '客户名称', key: 'customerName', width: 120 },
  { title: '联系电话', key: 'phone', width: 120 },
  { title: '订单金额', key: 'amount', width: 100 },
  {
    title: '订单状态',
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
  { title: '原完成时间', key: 'originalCompleteTime', width: 180 },
  { title: '新完成时间', key: 'newCompleteTime', width: 180 },
  { title: '修改原因', key: 'reason', width: 150 },
  { title: '修改时间', key: 'modifyTime', width: 180 },
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
  name: '订单完成时间修改',
  initForm: {
    orderNo: '',
    customerName: '',
    phone: '',
    amount: 0,
    status: 3, // 默认已完成状态
    originalCompleteTime: null,
    newCompleteTime: null,
    reason: '',
    remark: '',
  },
  doCreate: (data) => {
    // 这里应该调用真实的API
    console.log('创建数据', data)
    // 模拟添加修改时间
    data.modifyTime = new Date().toLocaleString()
    return Promise.resolve()
  },
  doUpdate: (data) => {
    // 这里应该调用真实的API
    console.log('更新数据', data)
    // 模拟更新修改时间
    data.modifyTime = new Date().toLocaleString()
    return Promise.resolve()
  },
  doDelete: (id) => {
    // 这里应该调用真实的API
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
