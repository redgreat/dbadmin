<template>
  <CommonPage show-footer>
    <n-space vertical :size="16">
      <!-- 查询条件 -->
      <n-card title="SIM卡批发数据补录" size="small">
        <template #header-extra>
          <n-tag type="info">仓储中心批发出库(OT3)未同步到SIM卡中心的数据补录 · 只写SIM卡中心</n-tag>
        </template>
        <n-form
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-placement="left"
          :label-width="110"
        >
          <n-form-item label="卡号/出库单号" path="keywords">
            <n-input
              v-model:value="formData.keywords"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 14 }"
              placeholder="每行一个，可混合输入：
SIM卡号，例如 610503500979702
仓储中心批发出库单号(OT3)，例如 OT2026...
按出库单号查询时，会带出该单全部流量卡"
            />
          </n-form-item>
          <n-space>
            <n-button type="primary" :loading="querying" @click="handleQuery">查询</n-button>
            <n-button @click="handleReset">重置</n-button>
          </n-space>
        </n-form>
        <n-alert type="warning" :show-icon="false" style="margin-top: 12px">
          补录规则：只写入 SIM 卡中心缺失字段（空值才补），已加装/已注销的卡自动跳过；
          出库时间/操作人取自仓储出库单，省市区取自出库单收货地址（页面可改），
          到期时间 = 仓储出库时间 + 卡年限 + 6 个月；跟踪记录按「批发出库 / 订单中心」补插。
        </n-alert>
      </n-card>

      <!-- 查询概要 -->
      <n-card v-if="summary" size="small" title="查询概要">
        <n-space>
          <n-tag type="info">命中 {{ summary.card_count || 0 }} 张卡</n-tag>
          <n-tag type="warning">待补录 {{ summary.pending_count || 0 }} 张</n-tag>
          <n-tag>跳过 {{ summary.skipped_count || 0 }} 张</n-tag>
          <n-tag v-if="summary.not_found?.length" type="error">
            未找到 {{ summary.not_found.length }} 个关键词
          </n-tag>
        </n-space>
        <n-alert
          v-if="summary.not_found?.length"
          type="error"
          title="以下关键词在仓储中心未找到批发出库(OT3)记录"
          style="margin-top: 12px"
        >
          <n-ul>
            <n-li v-for="(kw, idx) in summary.not_found" :key="idx">{{ kw }}</n-li>
          </n-ul>
        </n-alert>
      </n-card>

      <!-- 待补录明细 -->
      <n-card v-if="items.length" size="small" title="待补录数据（各表字段：当前值 → 待写入值）">
        <template #header-extra>
          <n-popconfirm @positive-click="handleExecute">
            <template #trigger>
              <n-button
                v-permission="'post/api/v1/sim/simfill/execute'"
                type="primary"
                size="small"
                :loading="executing"
                :disabled="!checkedKeys.length"
              >
                更新选中（{{ checkedKeys.length }}）
              </n-button>
            </template>
            确认对选中的 {{ checkedKeys.length }} 张卡执行补录？<br />
            只会写入 SIM 卡中心的缺失字段，可重复执行不覆盖已有数据。
          </n-popconfirm>
        </template>
        <n-data-table
          v-model:checked-row-keys="checkedKeys"
          :columns="columns"
          :data="items"
          :row-key="rowKey"
          :row-props="rowProps"
          :single-line="false"
          size="small"
          :scroll-x="1400"
        />
      </n-card>

      <!-- 执行结果 -->
      <n-card v-if="execResult" size="small" title="补录结果">
        <n-space style="margin-bottom: 12px">
          <n-tag type="info">共 {{ execResult.summary?.total || 0 }} 张</n-tag>
          <n-tag type="success">成功 {{ execResult.summary?.success_count || 0 }} 张</n-tag>
          <n-tag type="warning">跳过 {{ execResult.summary?.skipped_count || 0 }} 张</n-tag>
          <n-tag v-if="execResult.summary?.failed_count" type="error">
            失败 {{ execResult.summary?.failed_count }} 张
          </n-tag>
        </n-space>
        <n-alert
          v-if="execResult.summary?.updated_by_table && Object.keys(execResult.summary.updated_by_table).length"
          type="info"
          title="各表写入行数"
          style="margin-bottom: 12px"
        >
          <n-space>
            <n-tag v-for="(cnt, table) in execResult.summary.updated_by_table" :key="table" size="small">
              {{ table }}: {{ cnt }} 行
            </n-tag>
          </n-space>
        </n-alert>
        <n-data-table :columns="resultColumns" :data="execResult.results || []" size="small" :scroll-x="900" />
      </n-card>
    </n-space>
  </CommonPage>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { NInput, NInputNumber, NTag } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

// name 必须与后端菜单 name 一致（keep-alive）
defineOptions({ name: 'SIM卡批发数据补录' })

const message = useMessage()

const formRef = ref(null)
const querying = ref(false)
const executing = ref(false)
const items = ref([])
const summary = ref(null)
const execResult = ref(null)
const checkedKeys = ref([])

const formData = ref({ keywords: '' })

const rules = {
  keywords: [
    { required: true, message: '请输入 SIM 卡号或仓储出库单号' },
    {
      validator: (_, value) => {
        const lines = (value || '')
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean)
        if (!lines.length) return new Error('请输入至少一个 SIM 卡号或出库单号')
        if (lines.length > 200) return new Error('单次最多 200 个关键词')
        return true
      },
    },
  ],
}

const rowKey = (row) => row.sim_number
const rowProps = (row) => (row.blocked_reason ? { style: 'opacity: 0.55' } : {})

const statusTag = (row) => {
  if (row.blocked_reason)
    return h(NTag, { type: 'default', size: 'small' }, { default: () => '跳过' })
  if (!row.has_pending)
    return h(NTag, { type: 'success', size: 'small' }, { default: () => '已同步' })
  if (row.has_blocked)
    return h(NTag, { type: 'warning', size: 'small' }, { default: () => '待填写' })
  return h(NTag, { type: 'warning', size: 'small' }, { default: () => '待补录' })
}

const columns = [
  { type: 'selection', disabled: (row) => !row.has_pending || !!row.blocked_reason },
  { title: 'SIM卡号', key: 'sim_number', width: 150, fixed: 'left' },
  { title: '出库单号', key: 'out_stock_no', width: 190 },
  {
    title: '商品', key: 'goods_name', width: 150, ellipsis: { tooltip: true },
  },
  { title: '出库时间', key: 'out_stock_time', width: 165 },
  { title: '审核人', key: 'audit_name', width: 90 },
  {
    title: '卡年限(年)', key: 'sim_age', width: 110,
    render(row) {
      return h(NInputNumber, {
        value: row.sim_age,
        min: 0,
        max: 120,
        style: 'width: 100%',
        placeholder: '自动解析',
        'onUpdate:value': (v) => {
          row.sim_age = v
        },
      })
    },
  },
  {
    title: '省市区（收货地址，空才补）', key: 'region', width: 310,
    render(row) {
      const need = row.tables?.tb_simwarehouse?.steps?.region
      const mk = (key, ph, w) =>
        h(NInput, {
          value: row[key],
          size: 'small',
          style: `width:${w}px`,
          placeholder: ph,
          'onUpdate:value': (v) => {
            row[key] = v
          },
        })
      return h(
        'div',
        { style: 'display:flex;gap:4px;flex-wrap:wrap' },
        [
          mk('pro_code', '收货省编码', 76),
          mk('pro_name', need && !row.pro_name ? '省名(必填)' : '收货省名', 92),
          mk('city_code', '收货市编码', 76),
          mk('city_name', need && !row.city_name ? '市名(必填)' : '收货市名', 92),
        ]
      )
    },
  },
  {
    title: '待补录表', key: 'pending_tables', width: 280,
    render(row) {
      const pending = Object.entries(row.tables || {})
        .filter(([, v]) => v.pending)
        .map(([k]) => k)
      if (!pending.length) return h('span', '-')
      return h(
        'div',
        { style: 'display:flex;gap:4px;flex-wrap:wrap' },
        pending.map((t) => h(NTag, { size: 'small', type: 'info' }, { default: () => t }))
      )
    },
  },
  { title: '状态', key: 'status', width: 100, render: (row) => statusTag(row) },
  {
    type: 'expand',
    renderExpand(row) {
      const lines = []
      if (row.blocked_reason) {
        lines.push(h('div', { style: 'color:#d03050;margin-bottom:6px' }, `跳过原因：${row.blocked_reason}`))
      }
      if (row.delive_address || row.link_man) {
        lines.push(h('div', { style: 'font-weight:600;margin:6px 0 2px' }, '出库单收货地址'))
        lines.push(
          h(
            'div',
            { style: 'padding-left:12px;color:var(--text-color-2)' },
            `${row.link_man || '-'} ${row.link_tel || ''} ${row.delive_address || ''}`
          )
        )
      }
      for (const [table, info] of Object.entries(row.tables || {})) {
        if (!info.pending && !info.blocked) continue
        lines.push(h('div', { style: 'font-weight:600;margin:6px 0 2px' }, table))
        for (const f of info.fields || []) {
          lines.push(
            h(
              'div',
              { style: 'padding-left:12px;color:var(--text-color-2)' },
              `${f.field}：${f.current || '(空)'} → ${f.new ?? '(待填写)'}`
            )
          )
        }
      }
      if (!lines.length) lines.push(h('div', '各表数据均已同步，无需补录'))
      return h('div', { style: 'padding:8px 4px;font-size:12px' }, lines)
    },
  },
]

const resultColumns = [
  { title: 'SIM卡号', key: 'sim_number', width: 170 },
  {
    title: '结果', key: 'success', width: 80,
    render(row) {
      return h(
        NTag,
        { type: row.success ? 'success' : 'default', size: 'small' },
        { default: () => (row.success ? '成功' : '未执行') }
      )
    },
  },
  {
    title: '各表写入行数', key: 'updated_by_table', width: 300,
    render(row) {
      const entries = Object.entries(row.updated_by_table || {})
      if (!entries.length) return h('span', '-')
      return h(
        'div',
        { style: 'display:flex;gap:4px;flex-wrap:wrap' },
        entries.map(([t, c]) =>
          h(NTag, { size: 'small', type: 'info' }, { default: () => `${t}:${c}行` })
        )
      )
    },
  },
  {
    title: '说明', key: 'remark',
    render(row) {
      return row.skipped_reason || row.error || '-'
    },
  },
]

const checkedItems = computed(() =>
  items.value.filter((i) => checkedKeys.value.includes(i.sim_number))
)

const handleQuery = async () => {
  await formRef.value?.validate()
  querying.value = true
  execResult.value = null
  checkedKeys.value = []
  try {
    const res = await api.querySimFillPending({ keywords: formData.value.keywords })
    items.value = res.data?.items || []
    summary.value = res.data?.summary || null
    if (!items.value.length) message.warning(res.msg || '未查询到数据')
    else message.success(res.msg)
  } catch (e) {
    message.error(e.message || '查询失败')
  } finally {
    querying.value = false
  }
}

const handleExecute = async () => {
  if (!checkedKeys.value.length) return
  executing.value = true
  try {
    const payload = {
      items: checkedItems.value.map((row) => ({
        sim_number: row.sim_number,
        sim_age: row.sim_age,
        pro_code: row.pro_code || '',
        pro_name: row.pro_name || '',
        city_code: row.city_code || '',
        city_name: row.city_name || '',
      })),
    }
    const res = await api.executeSimFill(payload)
    execResult.value = res.data
    const s = res.data?.summary || {}
    if (s.failed_count) message.warning(res.msg)
    else message.success(res.msg)
    // 刷新现状（补录后应显示「已同步」）
    const keywords = formData.value.keywords
    try {
      const refresh = await api.querySimFillPending({ keywords })
      items.value = refresh.data?.items || []
      summary.value = refresh.data?.summary || null
      checkedKeys.value = []
    } catch {
      /* 刷新失败不影响主流程 */
    }
  } catch (e) {
    message.error(e.message || '补录执行失败')
  } finally {
    executing.value = false
  }
}

const handleReset = () => {
  formData.value = { keywords: '' }
  items.value = []
  summary.value = null
  execResult.value = null
  checkedKeys.value = []
}
</script>
