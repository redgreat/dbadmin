<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建记录
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
        <QueryBarItem label="车牌号" :label-width="80">
          <n-input
            v-model:value="queryItems.plateNumber"
            clearable
            type="text"
            placeholder="请输入车牌号"
          />
        </QueryBarItem>
        <QueryBarItem label="车主姓名" :label-width="80">
          <n-input
            v-model:value="queryItems.ownerName"
            clearable
            type="text"
            placeholder="请输入车主姓名"
          />
        </QueryBarItem>
        <QueryBarItem label="服务类型" :label-width="80">
          <n-select
            v-model:value="queryItems.serviceType"
            clearable
            :options="serviceTypeOptions"
            placeholder="请选择服务类型"
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
        <n-form-item label="车牌号" path="plateNumber">
          <n-input v-model:value="modalForm.plateNumber" clearable placeholder="请输入车牌号" />
        </n-form-item>
        <n-form-item label="车主姓名" path="ownerName">
          <n-input v-model:value="modalForm.ownerName" clearable placeholder="请输入车主姓名" />
        </n-form-item>
        <n-form-item label="联系电话" path="phone">
          <n-input v-model:value="modalForm.phone" clearable placeholder="请输入联系电话" />
        </n-form-item>
        <n-form-item label="车型" path="carModel">
          <n-input v-model:value="modalForm.carModel" clearable placeholder="请输入车型" />
        </n-form-item>
        <n-form-item label="服务类型" path="serviceType">
          <n-select
            v-model:value="modalForm.serviceType"
            :options="serviceTypeOptions"
            placeholder="请选择服务类型"
          />
        </n-form-item>
        <n-form-item label="服务时间" path="serviceTime">
          <n-date-picker
            v-model:value="modalForm.serviceTime"
            type="datetime"
            clearable
            placeholder="请选择服务时间"
          />
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
import { NButton, NTag, NSpace } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '壹好车服' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 服务类型选项
const serviceTypeOptions = [
  { label: '常规保养', value: 1 },
  { label: '轮胎更换', value: 2 },
  { label: '故障维修', value: 3 },
  { label: '美容清洗', value: 4 },
  { label: '年检服务', value: 5 },
]

// 模拟获取数据的API
const getData = () => {
  // 这里应该调用真实的API
  return Promise.resolve({
    items: [
      { id: 1, plateNumber: '沪A12345', ownerName: '张三', phone: '13800138000', carModel: '奥迪A6', serviceType: 1, serviceTime: '2023-05-01 10:00:00', status: 1 },
      { id: 2, plateNumber: '沪B67890', ownerName: '李四', phone: '13900139000', carModel: '宝马3系', serviceType: 2, serviceTime: '2023-05-02 11:00:00', status: 2 },
      { id: 3, plateNumber: '沪C54321', ownerName: '王五', phone: '13700137000', carModel: '奔驰C级', serviceType: 3, serviceTime: '2023-05-03 12:00:00', status: 3 },
    ],
    total: 3,
  })
}

// 获取服务类型文本
const getServiceTypeText = (type) => {
  const option = serviceTypeOptions.find(item => item.value === type)
  return option ? option.label : '未知类型'
}

// 获取状态标签类型
const getStatusType = (status) => {
  const map = {
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
    1: '待服务',
    2: '服务中',
    3: '已完成',
    4: '已取消',
  }
  return map[status] || '未知状态'
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '车牌号', key: 'plateNumber', width: 120 },
  { title: '车主姓名', key: 'ownerName', width: 120 },
  { title: '联系电话', key: 'phone', width: 120 },
  { title: '车型', key: 'carModel', width: 120 },
  {
    title: '服务类型',
    key: 'serviceType',
    width: 120,
    render(row) {
      return h('span', null, getServiceTypeText(row.serviceType))
    },
  },
  { title: '服务时间', key: 'serviceTime', width: 180 },
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
  name: '车服记录',
  initForm: {
    plateNumber: '',
    ownerName: '',
    phone: '',
    carModel: '',
    serviceType: null,
    serviceTime: null,
    remark: '',
    status: 1,
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
