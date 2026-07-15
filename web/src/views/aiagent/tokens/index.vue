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
            @keydown.enter="$table?.handleSearch"
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
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { NButton, NForm, NFormItem, NInput, NSwitch, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useCRUD } from '@/composables'
import aiApi from '@/api/ai'

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
} = useCRUD({
  name: 'Token',
  initForm: { allow_write: false },
  doCreate: aiApi.createToken,
  doUpdate: () => Promise.resolve(), // 暂时不支持修改
  doDelete: () => Promise.resolve(), // 暂时不支持删除
  refresh: () => $table.value?.handleSearch(),
})

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
      return (
        <NTag type={row.enabled ? 'success' : 'error'}>
          {row.enabled ? '启用' : '禁用'}
        </NTag>
      )
    },
  },
  {
    title: '允许写操作',
    key: 'allow_write',
    width: 100,
    align: 'center',
    render(row) {
      return row.allow_write ? <NTag type="warning">允许</NTag> : <NTag type="info">禁止</NTag>
    },
  },
  { title: '创建时间', key: 'created_at', width: 180, align: 'center' },
]

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}
</script>
