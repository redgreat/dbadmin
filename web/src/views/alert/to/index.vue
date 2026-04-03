<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button v-permission="'post/api/v1/alert/to/create'" class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增发送人
        </n-button>
        <n-button class="float-right mr-15" type="info" @click="handleRefresh">
          <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />刷新数据
        </n-button>
      </div>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="getData"
    >
      <template #queryBar>
        <QueryBarItem label="发送人名称" :label-width="90">
          <n-input
            v-model:value="queryItems.sender_name"
            clearable
            placeholder="请输入发送人名称"
          />
        </QueryBarItem>
        <QueryBarItem label="启用状态" :label-width="90">
          <n-select
            v-model:value="queryItems.is_enabled"
            clearable
            :options="enabledOptions"
            placeholder="请选择启用状态"
            style="width: 180px"
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
      <n-form
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="100"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="发送人名称" path="sender_name">
          <n-input v-model:value="modalForm.sender_name" clearable placeholder="请输入发送人名称" />
        </n-form-item>
        <n-form-item label="发送渠道" path="channel_type">
          <n-select v-model:value="modalForm.channel_type" :options="channelOptions" :disabled="true" />
        </n-form-item>
        <n-form-item label="企业微信群ID" path="channel_target">
          <n-input v-model:value="modalForm.channel_target" clearable placeholder="请输入企业微信群ID" />
        </n-form-item>
        <n-form-item label="启用状态" path="is_enabled">
          <n-switch v-model:value="modalForm.is_enabled" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="modalForm.remark" type="textarea" placeholder="请输入备注" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import { NButton, NPopconfirm, NSpace, NTag } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '预警发送人' })

const $table = ref(null)
const queryItems = ref({
  sender_name: '',
  is_enabled: null,
})
const vPermission = resolveDirective('permission')

const channelOptions = [{ label: '企业微信群', value: 'wechat_group' }]
const enabledOptions = [
  { label: '启用', value: '1' },
  { label: '停用', value: '0' },
]

const getData = async (params = {}) => {
  try {
    const query = { ...params }
    if (query.is_enabled === '1') query.is_enabled = true
    if (query.is_enabled === '0') query.is_enabled = false

    const response = await api.getAlertSenderList(query)
    return {
      data: response.data || [],
      total: response.total || 0,
    }
  } catch (error) {
    return { data: [], total: 0 }
  }
}

const getChannelText = (channelType) => {
  const option = channelOptions.find((item) => item.value === channelType)
  return option ? option.label : channelType
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '发送人名称', key: 'sender_name', width: 160 },
  {
    title: '发送渠道',
    key: 'channel_type',
    width: 120,
    render(row) {
      return h('span', null, getChannelText(row.channel_type))
    },
  },
  { title: '企业微信群ID', key: 'channel_target', width: 220 },
  {
    title: '状态',
    key: 'is_enabled',
    width: 100,
    render(row) {
      return h(NTag, { type: row.is_enabled ? 'success' : 'warning' }, { default: () => (row.is_enabled ? '启用' : '停用') })
    },
  },
  { title: '备注', key: 'remark', width: 180 },
  { title: '更新时间', key: 'updated_at', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    fixed: 'right',
    render(row) {
      return h(NSpace, { justify: 'center' }, {
        default: () => [
          withDirectives(
            h(
              NButton,
              { size: 'small', type: 'primary', onClick: () => handleEdit(row) },
              { default: () => '编辑' }
            ),
            [[vPermission, 'post/api/v1/alert/to/update']]
          ),
          h(
            NPopconfirm,
            { onPositiveClick: () => handleDelete({ id: row.id }) },
            {
              trigger: () =>
                withDirectives(
                  h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
                  [[vPermission, 'delete/api/v1/alert/to/delete']]
                ),
              default: () => h('div', {}, '确定删除该发送人吗?'),
            }
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
  name: '预警发送人',
  initForm: {
    sender_name: '',
    channel_type: 'wechat_group',
    channel_target: '',
    is_enabled: true,
    remark: '',
  },
  doCreate: (data) => api.createAlertSender(data),
  doUpdate: (data) => api.updateAlertSender(data),
  doDelete: (params) => api.deleteAlertSender(params),
  refresh: () => $table.value?.handleSearch(),
})

const rules = {
  sender_name: [{ required: true, message: '请输入发送人名称', trigger: ['input', 'blur'] }],
  channel_target: [{ required: true, message: '请输入企业微信群ID', trigger: ['input', 'blur'] }],
}

const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(() => {
  $table.value?.handleSearch()
})
</script>
