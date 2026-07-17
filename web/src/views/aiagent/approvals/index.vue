<template>
  <CommonPage title="审批管理">
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :extra-params="extraParams"
      :scroll-x="1400"
      :columns="columns"
      :get-data="aiApi.listApprovals"
    >
      <template #queryBar>
        <QueryBarItem label="审批单号" :label-width="70">
          <n-input
            v-model:value="queryItems.approval_no"
            type="text"
            placeholder="请输入审批单号"
            @keydown="$event.key === 'Enter' && $table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <!-- 审批弹窗 -->
    <n-modal v-model:show="showApproveModal" preset="dialog" title="审批处理">
      <n-form :model="approveForm">
        <n-form-item label="审批意见">
          <n-input v-model:value="approveForm.comment" type="textarea" placeholder="选填，审批意见" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showApproveModal = false">取消</n-button>
          <n-button type="error" @click="handleReject" :loading="submitLoading">拒绝</n-button>
          <n-button type="success" @click="handleApprove" :loading="submitLoading">通过并执行</n-button>
        </n-space>
      </template>
    </n-modal>
  </CommonPage>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { NButton, NInput, NTag, NModal, NForm, NFormItem, NSpace, useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import aiApi from '@/api/ai'
import { formatDateTime } from '@/utils/common/common'

defineOptions({ name: 'ApprovalsManagement' })

const message = useMessage()
const $table = ref(null)
const queryItems = ref({})
const extraParams = ref({})

const showApproveModal = ref(false)
const currentApproval = ref(null)
const approveForm = ref({ comment: '' })
const submitLoading = ref(false)

onMounted(() => {
  $table.value?.handleSearch()
})

const openApprove = (row) => {
  currentApproval.value = row
  approveForm.value.comment = ''
  showApproveModal.value = true
}

const handleApprove = async () => {
  submitLoading.value = true
  try {
    await aiApi.approveApproval(currentApproval.value.approval_no, approveForm.value)
    message.success('审批通过并已执行')
    showApproveModal.value = false
    $table.value?.handleSearch()
  } catch (error) {
    message.error(error.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const handleReject = async () => {
  submitLoading.value = true
  try {
    await aiApi.rejectApproval(currentApproval.value.approval_no, approveForm.value)
    message.success('已拒绝')
    showApproveModal.value = false
    $table.value?.handleSearch()
  } catch (error) {
    message.error(error.message || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const columns = [
  { title: '单号', key: 'approval_no', width: 150, align: 'center' },
  { title: '模块', key: 'op_module', width: 100, align: 'center' },
  { title: '操作类型', key: 'op_type', width: 150, align: 'center' },
  { title: '操作参数', key: 'op_params', width: 250, ellipsis: { tooltip: true }, render(row) {
    return JSON.stringify(row.op_params || {})
  } },
  { title: '申请人', key: 'applicant_id', width: 120, align: 'center' },
  { title: '备注', key: 'remark', width: 150, ellipsis: { tooltip: true } },
  { title: '状态', key: 'status', width: 100, align: 'center', render(row) {
    const statusMap = {
      pending: { type: 'warning', label: '待审批' },
      executed: { type: 'success', label: '已执行' },
      rejected: { type: 'error', label: '已拒绝' }
    }
    const s = statusMap[row.status] || { type: 'default', label: row.status }
    return h(NTag, { type: s.type }, { default: () => s.label })
  } },
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
    width: 100,
    align: 'center',
    fixed: 'right',
    render(row) {
      if (row.status === 'pending') {
        return h(
          NButton,
          { size: 'small', type: 'primary', onClick: () => openApprove(row) },
          { default: () => '处理' }
        )
      }
      return h('span', { class: 'text-gray-400' }, '无')
    },
  },
]
</script>
