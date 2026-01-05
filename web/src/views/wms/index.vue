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
        <QueryBarItem label="仓库编码" :label-width="80">
          <n-input
            v-model:value="queryItems.code"
            clearable
            type="text"
            placeholder="请输入仓库编码"
          />
        </QueryBarItem>
        <QueryBarItem label="仓库名称" :label-width="80">
          <n-input
            v-model:value="queryItems.name"
            clearable
            type="text"
            placeholder="请输入仓库名称"
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
        <n-form-item label="仓库编码" path="code">
          <n-input v-model:value="modalForm.code" clearable placeholder="请输入仓库编码" />
        </n-form-item>
        <n-form-item label="仓库名称" path="name">
          <n-input v-model:value="modalForm.name" clearable placeholder="请输入仓库名称" />
        </n-form-item>
        <n-form-item label="仓库地址" path="address">
          <n-input v-model:value="modalForm.address" clearable placeholder="请输入仓库地址" />
        </n-form-item>
        <n-form-item label="联系人" path="contact">
          <n-input v-model:value="modalForm.contact" clearable placeholder="请输入联系人" />
        </n-form-item>
        <n-form-item label="联系电话" path="phone">
          <n-input v-model:value="modalForm.phone" clearable placeholder="请输入联系电话" />
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

defineOptions({ name: '仓储中心' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 模拟获取数据的API
const getData = () => {
  // 这里应该调用真实的API
  return Promise.resolve({
    items: [
      { id: 1, code: 'WH001', name: '主仓库', address: '上海市浦东新区', contact: '张三', phone: '13800138000', status: 1 },
      { id: 2, code: 'WH002', name: '分仓库1', address: '北京市朝阳区', contact: '李四', phone: '13900139000', status: 1 },
      { id: 3, code: 'WH003', name: '分仓库2', address: '广州市天河区', contact: '王五', phone: '13700137000', status: 0 },
    ],
    total: 3,
  })
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '仓库编码', key: 'code', width: 120 },
  { title: '仓库名称', key: 'name', width: 150 },
  { title: '仓库地址', key: 'address', width: 200 },
  { title: '联系人', key: 'contact', width: 100 },
  { title: '联系电话', key: 'phone', width: 120 },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: row.status ? 'success' : 'error' },
        { default: () => (row.status ? '启用' : '禁用') }
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
  name: '仓库',
  initForm: {
    code: '',
    name: '',
    address: '',
    contact: '',
    phone: '',
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
