<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <n-card title="附件管理" size="small">
        <n-form :model="queryForm" label-placement="left" :label-width="90">
          <n-grid :cols="24" :x-gap="12">
            <n-form-item-gi :span="6" label="工单编码/Id">
              <n-input
                v-model:value="queryForm.keyword"
                clearable
                placeholder="非必填，不填查全部"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="5" label="附件类型">
              <n-select
                v-model:value="queryForm.sourceType"
                :options="sourceTypeOptions"
                clearable
                placeholder="全部类型"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="6" label="删除人">
              <n-select
                v-model:value="queryForm.deletedById"
                filterable
                remote
                clearable
                placeholder="输入姓名搜索用户中心用户"
                :options="operatorOptions"
                :loading="operatorLoading"
                @search="handleSearchOperator"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="7" label=" ">
              <n-checkbox v-model:checked="queryForm.includeDeleted">包含已删除附件</n-checkbox>
            </n-form-item-gi>
            <n-form-item-gi :span="24">
              <n-space>
                <n-button type="primary" :loading="querying" @click="handleQuery(1)">查询</n-button>
                <n-button @click="handleReset">重置</n-button>
              </n-space>
            </n-form-item-gi>
          </n-grid>
        </n-form>
      </n-card>

      <n-card size="small">
        <n-form :model="operateForm" label-placement="left" :label-width="90">
          <n-grid :cols="24" :x-gap="12">
            <n-form-item-gi :span="7" label="操作人">
              <n-select
                v-model:value="operateForm.operatorId"
                filterable
                remote
                clearable
                placeholder="删除必填；恢复非必填（仅恢复该人删除的附件）"
                :options="operatorOptions"
                :loading="operatorLoading"
                @search="handleSearchOperator"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="9" label="原因备注">
              <n-input
                v-model:value="operateForm.remark"
                clearable
                placeholder="非必填，记录运维日志使用"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="8" label=" ">
              <n-space>
                <n-button
                  type="error"
                  :loading="deleting"
                  :disabled="!checkedRowKeys.length"
                  @click="handleDelete"
                >
                  批量删除
                </n-button>
                <n-button
                  type="primary"
                  :loading="restoring"
                  :disabled="!checkedRowKeys.length"
                  @click="handleRestore"
                >
                  批量恢复
                </n-button>
              </n-space>
            </n-form-item-gi>
          </n-grid>
        </n-form>

        <n-data-table
          :columns="columns"
          :data="list"
          :loading="querying"
          :row-key="(row) => row.resource_id"
          :checked-row-keys="checkedRowKeys"
          :scroll-x="1700"
          size="small"
          :max-height="520"
          @update:checked-row-keys="checkedRowKeys = $event"
        />

        <n-space justify="end" class="mt-3">
          <n-pagination
            v-model:page="queryForm.page"
            v-model:page-size="queryForm.pageSize"
            :page-count="pageCount"
            :item-count="total"
            show-size-picker
            :page-sizes="[10, 20, 50, 100]"
            @update:page="handleQuery"
            @update:page-size="handleQuery(1)"
          />
        </n-space>
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { NImage, NTag } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '附件管理' })

const message = useMessage()

// 附件类型枚举（tb_workresourceinfo.SourceType）
const SOURCE_TYPE_MAP = {
  1: '设备参照图片',
  2: 'AFC主单附件',
  3: 'AFC费用附件',
  4: 'AFC备案附件',
  5: '主单附件',
  6: '收件附件',
  7: 'VHS备案附件',
  8: '归还附件',
  9: '二手车检测报告',
  10: 'AFC路况异常附件',
  11: '在线支付费用附件',
  12: 'VHS服务凭证',
  13: '退单凭证',
  14: '回款提报还款凭证',
  15: '回款提报谈判记录',
  16: '回款提报其他',
  17: 'VHS邮寄凭证',
  18: '金融预约附件',
  19: '金融备案视频附件',
  20: '谈判记录附件',
  21: '营业执照',
  22: '相关资质证书',
  23: '车务ETC附件',
  24: '通用异常签到附件',
  25: '车管工单附件',
  26: 'AFC住宿打卡附件',
  27: 'VHS请求关闭退单凭证',
  28: '下单附件',
  29: '科目附件',
  30: '服务结果附件',
  31: '异常反馈附件',
  32: '勘测附件',
  33: '安装附件',
  34: '增项费附件',
  35: '增项费付款附件',
  36: '勘测费付款附件',
  37: 'AFC二访附件',
  38: '车务补录附件',
  39: '车务工单PDF报告',
}

const sourceTypeOptions = Object.entries(SOURCE_TYPE_MAP).map(([value, label]) => ({
  label,
  value: Number(value),
}))

const queryForm = ref({
  keyword: '',
  sourceType: null,
  deletedById: '',
  includeDeleted: false,
  page: 1,
  pageSize: 20,
})

const operateForm = ref({ operatorId: '', remark: '' })

const list = ref([])
const total = ref(0)
const querying = ref(false)
const deleting = ref(false)
const restoring = ref(false)
const checkedRowKeys = ref([])

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / queryForm.value.pageSize)))

const isImageUrl = (url) => /\.(png|jpe?g|gif|webp|bmp|svg)(\?.*)?$/i.test(String(url || ''))

const columns = [
  { type: 'selection', fixed: 'left' },
  { title: '工单编码', key: 'app_code', width: 210, ellipsis: true, fixed: 'left' },
  { title: '工单类型', key: 'order_type_name', width: 120 },
  { title: '工单状态', key: 'work_status_name', width: 100 },
  { title: '附件类型', key: 'source_type_name', width: 160 },
  { title: '附件名称', key: 'resource_name', width: 220, ellipsis: true },
  { title: '备注', key: 'remark', width: 150, ellipsis: true },
  { title: '提醒内容', key: 'remind_content', width: 150, ellipsis: true },
  { title: '附件标记', key: 'resource_tag', width: 110, ellipsis: true },
  {
    title: '删除状态',
    key: 'deleted',
    width: 90,
    render: (row) =>
      h(
        NTag,
        { type: row.deleted ? 'error' : 'success', size: 'small' },
        { default: () => (row.deleted ? '已删除' : '正常') }
      ),
  },
  {
    title: '删除人',
    key: 'deleted_by_name',
    width: 240,
    render: (row) =>
      row.deleted_by_name
        ? `${row.deleted_by_name}-${row.deleted_by_code || ''}-(${row.deleted_by_id})`
        : row.deleted_by_id || '-',
  },
  { title: '删除时间', key: 'deleted_at', width: 170 },
  {
    title: '附件',
    key: 'url',
    width: 110,
    fixed: 'right',
    render: (row) =>
      isImageUrl(row.url)
        ? h(NImage, {
            src: row.url,
            width: 64,
            height: 42,
            previewSrc: row.url,
            style: 'cursor:pointer;border-radius:4px;',
          })
        : h('a', { href: row.url, target: '_blank', style: 'color:#2080f0;' }, '查看附件'),
  },
]

// 操作人远程搜索：从用户中心查
const operatorOptions = ref([])
const operatorLoading = ref(false)
let searchTimer = null

const handleSearchOperator = (query) => {
  if (!query) {
    operatorOptions.value = []
    return
  }
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    operatorLoading.value = true
    try {
      const res = await api.searchUserCenterUsers({ keyword: query, limit: 20 })
      if (res.code === 200) {
        operatorOptions.value = (res.data || []).map((u) => ({
          label: `${u.user_name}-${u.code}-(${u.user_center_user_id})`,
          value: u.user_center_user_id,
        }))
      } else {
        operatorOptions.value = []
      }
    } catch (e) {
      operatorOptions.value = []
    } finally {
      operatorLoading.value = false
    }
  }, 300)
}

const handleQuery = async (page) => {
  if (page) queryForm.value.page = page
  querying.value = true
  checkedRowKeys.value = []
  try {
    const res = await api.queryEhcfResources({
      keyword: queryForm.value.keyword.trim(),
      source_type: queryForm.value.sourceType,
      deleted_by_id: queryForm.value.deletedById || '',
      include_deleted: queryForm.value.includeDeleted,
      page: queryForm.value.page,
      page_size: queryForm.value.pageSize,
    })
    if (res.code === 200 || res.code === 0) {
      list.value = res.data?.items || []
      total.value = res.data?.total || 0
      message.success(res.data?.message || '查询成功')
    } else {
      list.value = []
      total.value = 0
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    list.value = []
    total.value = 0
    message.error('请求异常')
  } finally {
    querying.value = false
  }
}

const handleReset = () => {
  queryForm.value = {
    keyword: '',
    sourceType: null,
    deletedById: '',
    includeDeleted: false,
    page: 1,
    pageSize: 20,
  }
  list.value = []
  total.value = 0
  checkedRowKeys.value = []
}

const handleDelete = async () => {
  const operatorId = String(operateForm.value.operatorId || '').trim()
  if (!operatorId) {
    message.warning('删除操作必须选择操作人')
    return
  }
  const remark = String(operateForm.value.remark || '').trim()

  const confirmed = await new Promise((resolve) => {
    window.$dialog.error({
      title: '确认删除附件',
      content: `确定要删除选中的 ${checkedRowKeys.value.length} 条附件吗？此操作不可逆。`,
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  deleting.value = true
  try {
    const res = await api.deleteEhcfResources({
      resource_ids: checkedRowKeys.value,
      operator_id: operatorId,
      remark,
    })
    if (res.code === 200 || res.code === 0) {
      const { updated_count = 0, failed_count = 0 } = res.data || {}
      if (failed_count > 0) {
        message.warning(res.msg || `删除完成，成功 ${updated_count} 条，失败 ${failed_count} 条`)
      } else {
        message.success(res.msg || `删除成功：${updated_count} 条`)
      }
      operateForm.value.remark = ''
      handleQuery(queryForm.value.page)
    } else {
      message.error(res.msg || '删除失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    deleting.value = false
  }
}

const handleRestore = async () => {
  const operatorId = String(operateForm.value.operatorId || '').trim()
  const remark = String(operateForm.value.remark || '').trim()

  const confirmed = await new Promise((resolve) => {
    window.$dialog.warning({
      title: '确认恢复附件',
      content: operatorId
        ? `确定要恢复选中的 ${checkedRowKeys.value.length} 条附件吗？将仅恢复该操作人删除的附件。`
        : `未选择操作人，将恢复选中的 ${checkedRowKeys.value.length} 条附件（不限删除人）。`,
      positiveText: '确认',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
    })
  })
  if (!confirmed) return

  restoring.value = true
  try {
    const res = await api.restoreEhcfResources({
      resource_ids: checkedRowKeys.value,
      operator_id: operatorId,
      remark,
    })
    if (res.code === 200 || res.code === 0) {
      const { updated_count = 0, failed_count = 0 } = res.data || {}
      if (failed_count > 0) {
        message.warning(res.msg || `恢复完成，成功 ${updated_count} 条，失败 ${failed_count} 条`)
      } else {
        message.success(res.msg || `恢复成功：${updated_count} 条`)
      }
      operateForm.value.remark = ''
      handleQuery(queryForm.value.page)
    } else {
      message.error(res.msg || '恢复失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    restoring.value = false
  }
}
</script>
