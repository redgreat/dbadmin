<template>
  <CommonPage show-footer>
    <template #action>
      <n-button class="float-right mr-15" type="info" @click="handleRefresh">
        <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />刷新数据
      </n-button>
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
        <QueryBarItem label="发送状态" :label-width="90">
          <n-select
            v-model:value="queryItems.send_status"
            clearable
            :options="statusOptions"
            placeholder="请选择发送状态"
            style="width: 180px"
          />
        </QueryBarItem>
        <QueryBarItem label="开始时间" :label-width="90">
          <n-date-picker
            v-model:value="queryItems.start_time"
            type="datetime"
            clearable
            placeholder="请选择开始时间"
            format="yyyy-MM-dd HH:mm:ss"
          />
        </QueryBarItem>
        <QueryBarItem label="结束时间" :label-width="90">
          <n-date-picker
            v-model:value="queryItems.end_time"
            type="datetime"
            clearable
            placeholder="请选择结束时间"
            format="yyyy-MM-dd HH:mm:ss"
          />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref } from 'vue'
import { NButton, NTag } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import api from '@/api'
import { formatDateTime } from '@/utils'

defineOptions({ name: '预警日志' })

const $table = ref(null)
const queryItems = ref({
  sender_name: '',
  send_status: null,
  start_time: null,
  end_time: null,
})

const statusOptions = [
  { label: '成功', value: '1' },
  { label: '失败', value: '0' },
]

const channelTextMap = {
  wechat_group: '企业微信群',
  email: '邮件',
  wechat_app: '企业微信应用',
  feishu: '飞书',
  dingtalk: '钉钉',
}

const normalizeDateTime = (value) => {
  if (!value) return undefined
  if (typeof value === 'number') {
    return formatDateTime(value, 'YYYY-MM-DD HH:mm:ss')
  }
  return value
}

const getData = async (params = {}) => {
  try {
    const query = { ...params }
    if (query.send_status === '1') query.send_status = 1
    if (query.send_status === '0') query.send_status = 0
    query.start_time = normalizeDateTime(query.start_time)
    query.end_time = normalizeDateTime(query.end_time)

    const response = await api.getAlertLogList(query)
    return {
      data: response.data || [],
      total: response.total || 0,
    }
  } catch (error) {
    return { data: [], total: 0 }
  }
}

const renderLongText = (value) => {
  if (!value) return '-'
  const shortValue = value.length > 60 ? `${value.slice(0, 60)}...` : value
  return h(
    'span',
    {
      title: value,
      style: {
        display: 'inline-block',
        maxWidth: '100%',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      },
    },
    shortValue
  )
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '发送人名称', key: 'sender_name', width: 160 },
  {
    title: '发送渠道',
    key: 'channel_type',
    width: 120,
    render(row) {
      return channelTextMap[row.channel_type] || row.channel_type
    },
  },
  { title: '目标标识', key: 'channel_target', width: 220 },
  {
    title: '预警文本',
    key: 'alert_text',
    width: 300,
    render(row) {
      return renderLongText(row.alert_text)
    },
  },
  {
    title: '发送状态',
    key: 'send_status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: row.send_status === 1 ? 'success' : 'error' },
        { default: () => (row.send_status === 1 ? '成功' : '失败') }
      )
    },
  },
  {
    title: '返回信息',
    key: 'response_text',
    width: 260,
    render(row) {
      return renderLongText(row.response_text)
    },
  },
  { title: '发送时间', key: 'sent_at', width: 180 },
]

const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(() => {
  $table.value?.handleSearch()
})
</script>
