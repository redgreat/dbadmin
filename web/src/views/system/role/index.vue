<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NTag,
  NTree,
  NDrawer,
  NDrawerContent,
  NGrid,
  NGi,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: '角色管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const {
  modalVisible,
  modalAction,
  modalTitle,
  modalLoading,
  handleAdd,
  handleDelete,
  handleEdit,
  handleSave,
  modalForm,
  modalFormRef,
} = useCRUD({
  name: '角色',
  initForm: {},
  doCreate: api.createRole,
  doDelete: api.deleteRole,
  doUpdate: api.updateRole,
  refresh: () => $table.value?.handleSearch(),
})

const pattern = ref('')
const menuOption = ref([]) // 菜单选项
const active = ref(false)
const menu_ids = ref([])
const role_id = ref(0)

onMounted(() => {
  $table.value?.handleSearch()
})

const columns = [
  {
    title: '角色名',
    key: 'name',
    width: 80,
    align: 'center',
    ellipsis: { tooltip: true },
    render(row) {
      return h(NTag, { type: 'info' }, { default: () => row.name })
    },
  },
  {
    title: '角色描述',
    key: 'desc',
    width: 80,
    align: 'center',
  },
  {
    title: '创建日期',
    key: 'created_at',
    width: 60,
    align: 'center',
    render(row) {
      return h('span', formatDate(row.created_at))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              style: 'margin-right: 8px;',
              onClick: () => {
                handleEdit(row)
              },
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/role/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ role_id: row.id }, false),
            onNegativeClick: () => {},
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    style: 'margin-right: 8px;',
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/role/delete']]
              ),
            default: () => h('div', {}, '确定删除该角色吗?'),
          }
        ),
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: async () => {
                try {
                  // 获取菜单列表和角色已有权限
                  const [menusResponse, roleAuthorizedResponse] = await Promise.all([
                    api.getMenus({ page: 1, page_size: 9999 }),
                    api.getRoleAuthorized({ id: row.id }),
                  ])

                  menuOption.value = menusResponse.data
                  menu_ids.value = roleAuthorizedResponse.data.menus.map((v) => v.id)

                  active.value = true
                  role_id.value = row.id
                } catch (error) {
                  console.error('Error loading data:', error)
                }
              },
            },
            {
              default: () => '设置权限',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'get/api/v1/role/authorized']]
        ),
      ]
    },
  },
]

async function updateRoleAuthorized() {
  // 只需要传递菜单ID，API权限会自动关联
  const { code, msg } = await api.updateRoleAuthorized({
    id: role_id.value,
    menu_ids: menu_ids.value,
  })
  if (code === 200) {
    $message?.success('设置成功')
    active.value = false
  } else {
    $message?.error(msg)
  }
}
</script>

<template>
  <CommonPage show-footer>
    <template #action>
      <NButton v-permission="'post/api/v1/role/create'" type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建角色
      </NButton>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="api.getRoleList"
    >
      <template #queryBar>
        <QueryBarItem label="角色名" :label-width="50">
          <NInput
            v-model:value="queryItems.role_name"
            clearable
            type="text"
            placeholder="请输入角色名"
            @keypress.enter="$table?.handleSearch()"
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
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :disabled="modalAction === 'view'"
      >
        <NFormItem
          label="角色名"
          path="name"
          :rule="{
            required: true,
            message: '请输入角色名称',
            trigger: ['input', 'blur'],
          }"
        >
          <NInput v-model:value="modalForm.name" placeholder="请输入角色名称" />
        </NFormItem>
        <NFormItem label="角色描述" path="desc">
          <NInput v-model:value="modalForm.desc" placeholder="请输入角色描述" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <NDrawer v-model:show="active" placement="right" :width="500">
      <NDrawerContent>
        <NGrid x-gap="24" cols="12">
          <NGi span="8">
            <NInput
              v-model:value="pattern"
              type="text"
              placeholder="筛选菜单"
              style="flex-grow: 1"
            ></NInput>
          </NGi>
          <NGi offset="2">
            <NButton
              v-permission="'post/api/v1/role/authorized'"
              type="info"
              @click="updateRoleAuthorized"
              >确定</NButton
            >
          </NGi>
        </NGrid>
        <div class="mt-4 mb-2 text-gray-500">
          提示：设置菜单权限后，对应的接口访问权限将自动关联
        </div>
        <NTree
          :data="menuOption"
          :checked-keys="menu_ids"
          :pattern="pattern"
          :show-irrelevant-nodes="false"
          key-field="id"
          label-field="name"
          checkable
          cascade
          :default-expand-all="true"
          :block-line="true"
          :selectable="false"
          @update:checked-keys="(v) => (menu_ids = v)"
        />
        <template #header> 设置菜单权限 </template>
      </NDrawerContent>
    </NDrawer>
  </CommonPage>
</template>
