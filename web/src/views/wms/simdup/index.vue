<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <!-- 说明 + 模板下载 -->
      <n-card title="使用说明" size="small">
        <n-alert type="info">
          <p>1. 点击「下载模板」获取固定模板 Excel（仅一列 SimNumber）。</p>
          <p>2. 按模板格式填入需要校验的 SIM 卡号（一列 SimNumber）。</p>
          <p>
            3. 上传文件执行验证：系统会将 SimNumber 写入仓储中心（WMS_CONN）临时表 tm_remano，再执行验证SQL，
            命中 <code>tb_materialinit</code>（未删除）的即视为「重复入库」，并保存验证记录、导出重复编码 Excel。
          </p>
        </n-alert>
      </n-card>

      <!-- 文件上传 + 验证 -->
      <n-card title="上传Excel并验证" size="small">
        <n-space vertical>
          <n-upload
            v-model:file-list="fileList"
            :max="1"
            :default-upload="false"
            accept=".xlsx,.xls,.csv"
            @before-upload="handleBeforeUpload"
            @change="handleUploadChange"
          >
            <n-button>
              <TheIcon icon="mdi:file-upload-outline" :size="16" class="mr-2" />
              选择文件
            </n-button>
          </n-upload>
          <n-text depth="3">支持 .xlsx / .xls / .csv，仅一列 SimNumber，最大 20MB。</n-text>
          <n-space>
            <n-button type="primary" v-permission="'get/api/v1/wms/simdup/template'" @click="handleDownloadTemplate">
              <TheIcon icon="mdi:download" :size="16" class="mr-2" />
              下载模板
            </n-button>
            <n-button
              type="primary"
              v-permission="'post/api/v1/wms/simdup/verify'"
              :loading="verifying"
              :disabled="!currentFile"
              @click="handleVerify"
            >
              <TheIcon icon="mdi:shield-check" :size="16" class="mr-2" />
              上传并验证
            </n-button>
          </n-space>
        </n-space>
      </n-card>

      <!-- 验证结果 -->
      <n-card v-if="verifyResult" title="验证结果" size="small">
        <n-alert :type="verifyResult.status === 'completed' ? 'success' : 'error'" class="mb-3">
          {{ verifyResult.message }}
        </n-alert>
        <n-descriptions :column="2" size="small" label-placement="left" bordered>
          <n-descriptions-item label="批次号">{{ verifyResult.batch_no }}</n-descriptions-item>
          <n-descriptions-item label="状态">{{ verifyResult.status }}</n-descriptions-item>
          <n-descriptions-item label="导入总数">{{ verifyResult.total_count }}</n-descriptions-item>
          <n-descriptions-item label="重复数">{{ verifyResult.duplicate_count }}</n-descriptions-item>
        </n-descriptions>
        <n-space class="mt-3">
          <n-button
            v-if="verifyResult.can_download"
            v-permission="'get/api/v1/wms/simdup/record/1/export'"
            type="primary"
            :loading="exporting"
            @click="handleExport(verifyResult.record_id)"
          >
            <TheIcon icon="mdi:file-excel" :size="16" class="mr-2" />
            导出重复编码
          </n-button>
          <n-text v-else depth="3">该批次未发现重复入库卡号，无需导出。</n-text>
        </n-space>
      </n-card>

      <!-- 验证记录列表 -->
      <n-card title="验证记录" size="small">
        <n-space class="mb-3">
          <n-select
            v-model:value="recordFilter.status"
            :options="statusOptions"
            placeholder="按状态筛选"
            style="width: 160px"
            clearable
          />
          <n-select
            v-model:value="recordFilter.source"
            :options="sourceOptions"
            placeholder="按来源筛选"
            style="width: 140px"
            clearable
          />
          <n-button @click="loadRecords">刷新</n-button>
        </n-space>
        <n-data-table :columns="recordColumns" :data="records" :loading="recordLoading" :bordered="false" size="small" />
        <n-space justify="end" class="mt-3">
          <n-pagination v-model:page="recordPage" :page-size="recordFilter.page_size" :item-count="recordTotal" />
        </n-space>
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { ref, h, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import api from '@/api'

defineOptions({ name: 'SIM卡重复入库验证' })

// Naive UI 组件：模板里的小写标签由构建自动注册，此处导入仅用于数据表格 render 函数中以 h() 渲染
import { NTag, NText, NButton } from 'naive-ui'

const message = useMessage()

// ── 上传验证 ──
const fileList = ref([])
const currentFile = ref(null)
const verifying = ref(false)
const exporting = ref(false)
const verifyResult = ref(null)

// ── 记录列表 ──
const records = ref([])
const recordLoading = ref(false)
const recordTotal = ref(0)
const recordPage = ref(1)
const recordFilter = ref({ status: null, source: null, page: 1, page_size: 20 })
const statusOptions = [
  { label: '进行中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]
const sourceOptions = [
  { label: '页面导入', value: 'web' },
  { label: '对外API', value: 'api' },
]

const handleBeforeUpload = ({ file }) => {
  const ext = file?.name?.split('.').pop()?.toLowerCase()
  if (!['xlsx', 'xls', 'csv'].includes(ext)) {
    message.error('仅支持 .xlsx / .xls / .csv 文件')
    return false
  }
  return true
}

const handleUploadChange = ({ fileList: fl, file }) => {
  if (fl && fl.length === 0) {
    currentFile.value = null
    return
  }
  const item = file || fl?.[0]
  currentFile.value = item?.file || item
}

const handleDownloadTemplate = async () => {
  try {
    const blob = await api.downloadSimDupTemplate()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'simdup_verify_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    message.error(e?.message || '模板下载失败')
  }
}

const handleVerify = async () => {
  if (!currentFile.value) {
    message.warning('请先选择Excel文件')
    return
  }
  verifying.value = true
  verifyResult.value = null
  try {
    const res = await api.verifySimDup(currentFile.value)
    if (res.code === 200) {
      verifyResult.value = {
        ...res.data,
        message: res.msg || res.data?.message || '验证完成',
      }
      message.success(res.msg || '验证完成')
      loadRecords()
    } else {
      message.error(res.msg || '验证失败')
    }
  } catch (e) {
    message.error(e?.message || '验证请求异常')
  } finally {
    verifying.value = false
  }
}

const handleExport = async (recordId) => {
  if (!recordId) return
  exporting.value = true
  try {
    const blob = await api.exportSimDupRecord(recordId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `simdup_${recordId}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    message.success('开始下载')
  } catch (e) {
    message.error(e?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

const loadRecords = async () => {
  recordLoading.value = true
  try {
    const res = await api.getSimDupRecordList({
      page: recordPage.value,
      page_size: recordFilter.value.page_size,
      status: recordFilter.value.status || '',
      source: recordFilter.value.source || '',
    })
    if (res.code === 200) {
      records.value = res.data || []
      recordTotal.value = res.total || 0
    } else {
      message.error(res.msg || '获取记录列表失败')
    }
  } catch (e) {
    message.error(e?.message || '获取记录列表失败')
  } finally {
    recordLoading.value = false
  }
}

const recordColumns = [
  { title: '批次号', key: 'batch_no', width: 220, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => {
      const map = { processing: '进行中', completed: '已完成', failed: '失败' }
      const type = row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : 'default'
      return h(NTag, { type, size: 'small' }, { default: () => map[row.status] || row.status })
    },
  },
  { title: '来源', key: 'source', width: 80 },
  { title: '导入总数', key: 'total_count', width: 90 },
  { title: '重复数', key: 'duplicate_count', width: 80 },
  { title: '操作人', key: 'username', width: 100, ellipsis: { tooltip: true } },
  { title: '时间', key: 'created_at', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => {
      if (!row.duplicate_count) {
        return h(NText, { depth: 3 }, { default: () => '无重复' })
      }
      return h(
        NButton,
        { size: 'small', type: 'primary', secondary: true, onClick: () => handleExport(row.id) },
        { default: () => '导出' },
      )
    },
  },
]

onMounted(loadRecords)
</script>
