<template>
  <CommonPage show-footer title="Token 管理">
    <template #action>
      <n-button type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" /> 新建 Token
      </n-button>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :extra-params="extraParams"
      :scroll-x="1200"
      :columns="columns"
      :get-data="aiApi.listTokens"
    >
      <template #queryBar>
        <QueryBarItem label="名称" :label-width="50">
          <n-input
            v-model:value="queryItems.name"
            type="text"
            placeholder="请输入名称"
            @keydown="$event.key === 'Enter' && $table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      :show-footer="true"
      @save="handleSave"
    >
      <n-form
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="名称" path="name">
          <n-input v-model:value="modalForm.name" placeholder="请输入Token名称" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="modalForm.description"
            type="textarea"
            placeholder="请输入描述信息"
          />
        </n-form-item>
        <n-form-item label="允许写操作" path="allow_write">
          <n-switch v-model:value="modalForm.allow_write" />
        </n-form-item>
      </n-form>
    </CrudModal>

    <!-- 分配权限弹窗 -->
    <CrudModal
      v-model:visible="permModalVisible"
      title="分配 MCP 工具权限"
      :loading="permModalLoading"
      :show-footer="true"
      @save="handleSavePerm"
    >
      <n-checkbox-group v-model:value="selectedTools">
        <n-space vertical align="start" :size="16">
          <n-checkbox v-for="tool in allTools" :key="tool.name" :value="tool.name">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-weight: bold;">{{ tool.name }}</span>
              <n-tag v-if="tool.is_write" type="warning" size="small">写操作</n-tag>
            </div>
            <div style="color: #999; font-size: 12px; margin-top: 4px;">{{ tool.description }}</div>
          </n-checkbox>
        </n-space>
      </n-checkbox-group>
    </CrudModal>

  </CommonPage>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NButton, NForm, NFormItem, NInput, NSwitch, NTag, NPopconfirm, NCheckboxGroup, NSpace, NCheckbox } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useCRUD } from '@/composables'
import aiApi from '@/api/ai'
import { formatDateTime } from '@/utils/common/common'

defineOptions({ name: 'TokenManagement' })

const $table = ref(null)
const queryItems = ref({})
const extraParams = ref({})

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleAdd,
  handleEdit,
  handleDelete,
} = useCRUD({
  name: 'Token',
  initForm: { allow_write: false },
  doCreate: aiApi.createToken,
  doUpdate: aiApi.updateToken,
  doDelete: aiApi.deleteToken,
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

const permModalVisible = ref(false)
const permModalLoading = ref(false)
const allTools = ref([])
const selectedTools = ref([])
const currentTokenId = ref(null)

async function fetchTools() {
  const res = await aiApi.listMcpTools()
  allTools.value = res.data || []
}

async function handleOpenPerm(row) {
  if (allTools.value.length === 0) {
    await fetchTools()
  }
  currentTokenId.value = row.id
  selectedTools.value = row.allow_tools || []
  permModalVisible.value = true
}

async function handleSavePerm() {
  permModalLoading.value = true
  try {
    await aiApi.updateToken({ id: currentTokenId.value, allow_tools: selectedTools.value })
    permModalVisible.value = false
    window.$message?.success('权限分配成功')
    $table.value?.handleSearch()
  } finally {
    permModalLoading.value = false
  }
}

async function handleToggleStatus(row) {
  await aiApi.updateToken({ id: row.id, enabled: !row.enabled })
  window.$message?.success('状态更新成功')
  $table.value?.handleSearch()
}

const columns = [
  { title: 'ID', key: 'id', width: 60, align: 'center' },
  { title: '名称', key: 'name', width: 150, align: 'center' },
  { title: 'Token', key: 'token', width: 250, align: 'center', ellipsis: { tooltip: true } },
  { title: '描述', key: 'description', width: 200, align: 'center' },
  {
    title: '状态',
    key: 'enabled',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.enabled ? 'success' : 'error' },
        { default: () => (row.enabled ? '启用' : '禁用') }
      )
    },
  },
  {
    title: '允许写操作',
    key: 'allow_write',
    width: 100,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.allow_write ? 'warning' : 'info' },
        { default: () => (row.allow_write ? '允许' : '禁止') }
      )
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    align: 'center',
    render(row) {
      return formatDateTime(row.created_at)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    align: 'center',
    fixed: 'right',
    render(row) {
      return h(
        NSpace,
        { justify: 'center' },
        {
          default: () => [
            h(
              NButton,
              { size: 'small', type: 'primary', secondary: true, onClick: () => handleEdit(row) },
              { default: () => '编辑' }
            ),
            h(
              NButton,
              { size: 'small', type: row.enabled ? 'warning' : 'success', secondary: true, onClick: () => handleToggleStatus(row) },
              { default: () => (row.enabled ? '停用' : '启用') }
            ),
            h(
              NButton,
              { size: 'small', type: 'info', secondary: true, onClick: () => handleOpenPerm(row) },
              { default: () => '分配权限' }
            ),
            h(
              NPopconfirm,
              {
                onPositiveClick: () => handleDelete({ id: row.id }),
              },
              {
                trigger: () => h(NButton, { size: 'small', type: 'error', secondary: true }, { default: () => '删除' }),
                default: () => '确定要删除此 Token 吗？',
              }
            ),
          ],
        }
      )
    },
  },
]

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}
</script>
