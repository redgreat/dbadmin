<template>
  <CommonPage>
    <CrudTable ref="$table" v-model:query-items="queryItems" :columns="columns" :get-data="handleGetStat">
      <template #queryBar>
        <QueryBarItem label="修改人" :label-width="70">
          <NInput v-model:value="queryItems.username" clearable />
        </QueryBarItem>
        <QueryBarItem label="操作人Id" :label-width="70">
          <NInput v-model:value="queryItems.operator_id" clearable />
        </QueryBarItem>
        <QueryBarItem label="接口" :label-width="60">
          <NSelect v-model:value="queryItems.path" style="width: 240px" :options="interfaceOptions" clearable />
        </QueryBarItem>
        <QueryBarItem label="修改时间" :label-width="70">
          <NDatePicker v-model:value="datetimeRange" type="datetimerange" clearable @update:value="onRange" />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>

<script setup>
import { computed, onMounted, ref, h } from 'vue'
import { NInput, NSelect, NPopover } from 'naive-ui'
import TheIcon from '@/components/icon/TheIcon.vue'
import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import api from '@/api'
import { useUserStore } from '@/store'
import { formatDateTime } from '@/utils'

defineOptions({ name: '接口调用统计' })

const $table = ref(null)
const queryItems = ref({})
const userStore = useUserStore()
const isSuperUser = computed(() => !!userStore.isSuperUser)
const interfaceOptions = ref([])

async function handleGetStat(params = {}) {
  const cleaned = {}
  for (const [k, v] of Object.entries(params)) {
    if (v === '' || v === null) continue
    cleaned[k] = v
  }
  if (!isSuperUser.value) delete cleaned.username
  return api.getEhcfApiStatList(cleaned)
}

async function loadInterfaces() {
  try {
    const res = await api.getEhcfApiStatInterfaces()
    interfaceOptions.value = (res.data || []).map((it) => ({ label: it.label, value: it.path }))
  } catch { interfaceOptions.value = [] }
}

onMounted(() => { loadInterfaces(); $table.value?.handleSearch() })

function fmt(t) { return formatDateTime(t, 'YYYY-MM-DD HH:mm:ss') }
const s = new Date(); s.setHours(0, 0, 0, 0)
const e = new Date(); e.setHours(23, 59, 59, 999)
queryItems.value.start_time = fmt(s.getTime())
queryItems.value.end_time = fmt(e.getTime())
const datetimeRange = ref([s.getTime(), e.getTime()])
const onRange = (v) => {
  if (v == null) { queryItems.value.start_time = null; queryItems.value.end_time = null }
  else { queryItems.value.start_time = fmt(v[0]); queryItems.value.end_time = fmt(v[1]) }
}

function fmtJSON(d) {
  try { return typeof d === 'string' ? JSON.stringify(JSON.parse(d), null, 2) : JSON.stringify(d, null, 2) }
  catch { return d || 'empty' }
}
function cell(key) {
  return (row) => h(NPopover, { trigger: 'hover', placement: 'right' }, {
    trigger: () => h('div', { style: 'cursor:pointer;' }, [h(TheIcon, { icon: 'carbon:data-view' })]),
    default: () => h('pre', { style: 'max-height:400px;overflow:auto;background:#f5f5f5;padding:8px;' }, fmtJSON(row[key])),
  })
}

const columns = [
  { title: '修改人', key: 'username', width: 120, align: 'center', ellipsis: { tooltip: true } },
  { title: '接口', key: 'interface_label', align: 'center', width: 200, ellipsis: { tooltip: true } },
  { title: '操作摘要', key: 'summary', align: 'center', width: 300, ellipsis: { tooltip: true } },
  { title: '请求路径', key: 'path', align: 'center', width: 260, ellipsis: { tooltip: true } },
  { title: '请求体', key: 'request_body', align: 'center', width: 80, render: cell('request_body') },
  { title: '响应体', key: 'response_body', align: 'center', width: 80, render: cell('response_body') },
  { title: '修改时间', key: 'created_at', align: 'center', width: 170, ellipsis: { tooltip: true } },
]
</script>
