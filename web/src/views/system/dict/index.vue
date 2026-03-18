<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives, computed } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NTag,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '字典管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 表单初始化内容
const initForm = {
  name: '',
  code: '',
  parent_code: null,
  parent_name: null,
}

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleAdd,
  handleDelete,
  handleEdit,
  handleSave,
  modalForm,
  modalFormRef,
} = useCRUD({
  name: '字典',
  initForm,
  doCreate: api.createDict,
  doDelete: api.deleteDict,
  doUpdate: api.updateDict,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

// 计算层级信息
const levelInfo = computed(() => {
  if (!modalForm.value.parent_code) {
    return { level: 1, label: '一级字典' }
  }
  // 从父级编码解析层级
  const parentLevel = (modalForm.value.parent_code.match(/-/g) || []).length + 1
  return { level: parentLevel + 1, label: `${parentLevel + 1}级字典` }
})

const columns = [
  { title: 'ID', key: 'id', width: 60, ellipsis: { tooltip: true }, align: 'center' },
  { title: '字典名称', key: 'name', width: 150, ellipsis: { tooltip: true }, align: 'center' },
  { title: '字典编码', key: 'code', width: 150, ellipsis: { tooltip: true }, align: 'center' },
  {
    title: '父级编码',
    key: 'parent_code',
    width: 120,
    align: 'center',
    render(row) {
      return h('span', row.parent_code || '根级')
    },
  },
  {
    title: '创建日期',
    key: 'created_at',
    width: 100,
    align: 'center',
    render(row) {
      return h('span', formatDate(row.created_at))
    },
  },
  {
    title: '更新日期',
    key: 'updated_at',
    width: 100,
    align: 'center',
    render(row) {
      return h('span', formatDate(row.updated_at))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    align: 'center',
    fixed: 'right',
    render(row) {
      // 计算当前层级
      const currentLevel = (row.code.match(/-/g) || []).length + 1
      const canAddChild = currentLevel < 3 // 最多三层
      
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'primary',
              style: `display: ${canAddChild ? '' : 'none'};`,
              onClick: () => {
                initForm.parent_code = row.code
                initForm.parent_name = row.name
                handleAdd()
              },
            },
            { default: () => '子字典', icon: renderIcon('material-symbols:add', { size: 16 }) }
          ),
          [[vPermission, 'post/api/v1/dict/create']]
        ),
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'info',
              onClick: () => {
                handleEdit(row)
              },
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/dict/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ id: row.id }, false),
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'tiny',
                    quaternary: true,
                    type: 'error',
                    style: `display: ${row.children && row.children.length > 0 ? 'none' : ''};`,
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/dict/delete']]
              ),
            default: () => h('div', {}, '确定删除该字典吗?'),
          }
        ),
      ]
    },
  },
]

// 新增根字典
function handleClickAdd() {
  initForm.parent_code = null
  initForm.parent_name = null
  handleAdd()
}
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer>
    <template #action>
      <NButton v-permission="'post/api/v1/dict/create'" type="primary" @click="handleClickAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建根字典
      </NButton>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :is-pagination="false"
      :columns="columns"
      :get-data="api.getDictTree"
      :single-line="true"
    >
    </CrudTable>

    <!-- 新增/编辑/查看 弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave()"
    >
      <!-- 表单 -->
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
      >
        <NFormItem label="层级信息">
          <NTag type="info">{{ levelInfo.label }}</NTag>
        </NFormItem>
        <NFormItem
          label="字典名称"
          path="name"
          :rule="{
            required: true,
            message: '请输入字典名称',
            trigger: ['input', 'blur'],
          }"
        >
          <NInput v-model:value="modalForm.name" placeholder="请输入字典名称，编码将自动生成" />
        </NFormItem>
        <NFormItem label="字典编码" path="code">
          <NTag type="success">{{ modalForm.code || '编码将根据名称自动生成' }}</NTag>
        </NFormItem>
        <NFormItem v-if="modalForm.parent_code" label="父级字典">
          <NTag type="warning">{{ modalForm.parent_name }} ({{ modalForm.parent_code }})</NTag>
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
