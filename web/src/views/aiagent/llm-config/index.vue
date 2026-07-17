<template>
  <CommonPage show-footer title="大模型配置">
    <template #action>
      <n-button type="primary" @click="handleAdd">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" /> 新建配置
      </n-button>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :extra-params="extraParams"
      :scroll-x="1200"
      :columns="columns"
      :get-data="aiApi.listLlmConfigs"
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
        :label-width="100"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="提供商" path="provider">
          <n-select v-model:value="modalForm.provider" :options="providerOptions" />
        </n-form-item>
        <n-form-item label="名称" path="name">
          <n-input v-model:value="modalForm.name" placeholder="如：DeepSeek Default" />
        </n-form-item>
        <n-form-item label="模型名称" path="model_name">
          <n-input v-model:value="modalForm.model_name" placeholder="如：deepseek-chat" />
        </n-form-item>
        <n-form-item label="API Base URL" path="base_url">
          <n-input v-model:value="modalForm.base_url" placeholder="可选，自定义端点" />
        </n-form-item>
        <n-form-item label="API Key" path="api_key_enc">
          <n-input
            v-model:value="modalForm.api_key_enc"
            type="password"
            show-password-on="click"
            placeholder="请输入API Key"
          />
        </n-form-item>
        <n-form-item label="是否激活" path="is_active">
          <n-switch v-model:value="modalForm.is_active" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NButton, NForm, NFormItem, NInput, NSelect, NSwitch, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useCRUD } from '@/composables'
import aiApi from '@/api/ai'
import { formatDateTime } from '@/utils/common/common'

defineOptions({ name: 'LlmConfigManagement' })

const $table = ref(null)
const queryItems = ref({})
const extraParams = ref({})

const providerOptions = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Qwen', value: 'qwen' },
  { label: 'Ollama', value: 'ollama' },
]

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleAdd,
  handleEdit,
} = useCRUD({
  name: '配置',
  initForm: { is_active: false, provider: 'deepseek' },
  doCreate: aiApi.createLlmConfig,
  doUpdate: aiApi.updateLlmConfig,
  doDelete: () => Promise.resolve(), // 暂时不支持删除
  refresh: () => $table.value?.handleSearch(),
})

onMounted(() => {
  $table.value?.handleSearch()
})

const columns = [
  { title: 'ID', key: 'id', width: 60, align: 'center' },
  { title: '提供商', key: 'provider', width: 100, align: 'center' },
  { title: '名称', key: 'name', width: 150, align: 'center' },
  { title: '模型名称', key: 'model_name', width: 150, align: 'center' },
  { title: 'Base URL', key: 'base_url', width: 200, align: 'center', ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'is_active',
    width: 80,
    align: 'center',
    render(row) {
      return h(
        NTag,
        { type: row.is_active ? 'success' : 'default' },
        { default: () => (row.is_active ? '激活' : '未激活') }
      )
    },
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 180,
    align: 'center',
    render(row) {
      return formatDateTime(row.updated_at)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    align: 'center',
    fixed: 'right',
    render(row) {
      return h(
        NButton,
        { size: 'small', type: 'primary', onClick: () => handleEdit(row) },
        { default: () => '编辑' }
      )
    },
  },
]

const rules = {
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}
</script>
