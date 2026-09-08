<template>
  <CommonPage show-footer>
    <n-card title="价格查询与修改" size="small">
      <n-form ref="priceFormRef" :model="priceForm" :rules="priceRules" label-placement="left" :label-width="100">
        <n-form-item label="单据编码" path="stock_code">
          <n-input v-model:value="priceForm.stock_code" clearable placeholder="请输入入库单或出库单编码" />
        </n-form-item>
        <n-form-item label="物料名称" path="material_name">
          <n-input v-model:value="priceForm.material_name" clearable placeholder="请输入物料名称" />
        </n-form-item>
        <n-form-item label="修改后价格" path="new_price">
          <n-input v-model:value="priceForm.new_price" clearable placeholder="请输入修改后价格（decimal(18,2)）" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="priceForm.remark" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="非必填，记录运维日志使用" />
        </n-form-item>
        <n-space>
          <n-button type="primary" :loading="priceQuerying" @click="handlePriceQuery">查询</n-button>
          <n-button type="warning" :loading="priceModifying" :disabled="!canModify" @click="handlePriceModify">{{ modifyButtonText }}</n-button>
          <n-button @click="handlePriceReset">重置</n-button>
        </n-space>
      </n-form>

      <n-divider />
      
      <n-data-table
        v-if="priceResults.length > 0"
        :columns="priceColumns"
        :data="priceResults"
        :bordered="false"
        size="small"
      />
      <n-empty v-else description="暂无查询结果" />
    </n-card>
  </CommonPage>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import { NCard, NSpace, NDataTable, NDivider, NEmpty } from 'naive-ui'
import api from '@/api'

defineOptions({ name: '价格修改' })

const message = useMessage()

const priceFormRef = ref(null)
const priceForm = ref({ stock_code: '', material_name: '', new_price: '', remark: '' })
const priceResults = ref([])
const priceQuerying = ref(false)
const priceModifying = ref(false)

const priceRules = {
  new_price: [
    {
      validator: (_, value) => {
        if (value && !/^\d+(\.\d{1,2})?$/.test(value)) {
          return new Error('价格格式不正确，应为decimal(18,2)')
        }
        return true
      },
    },
  ],
}

const docTypeMap = { instock: '入库单', outstock: '出库单' }
const tableTypeMap = { main: '进行中', his: '已完成' }

const priceColumns = [
  { title: '明细Id', key: 'detail_id' },
  { title: '单据编码', key: 'stock_no' },
  { title: '物料名称', key: 'material_name' },
  { title: '单据类型', key: 'doc_type', render: (row) => docTypeMap[row.doc_type] || row.doc_type },
  { title: '单据状态', key: 'table_type', render: (row) => tableTypeMap[row.table_type] || row.table_type },
  { title: '原价格', key: 'original_price' },
  { title: '数量', key: 'instocked_num' },
  { title: '新价格', key: 'new_price' },
  { title: '对账状态', key: 'can_modify', render: (row) => row.can_modify ? '可修改' : '已对账' },
  { title: '说明', key: 'reason' },
]

const canModify = computed(() => priceResults.value.some((r) => r.can_modify === true))

const modifyButtonText = computed(() => {
  const count = priceResults.value.filter((r) => r.can_modify === true).length
  return count > 1 ? `批量修改(${count})` : '修改'
})

const handlePriceQuery = async () => {
  priceQuerying.value = true
  try {
    const res = await api.queryPrice({
      stock_code: priceForm.value.stock_code,
      material_name: priceForm.value.material_name,
      new_price: priceForm.value.new_price,
      remark: priceForm.value.remark,
    })
    if (res.code === 200) {
      priceResults.value = res.data || []
      if (priceResults.value.length === 0) {
        message.warning('未查询到符合条件的记录')
      } else {
        const cannot = priceResults.value.filter((r) => r.can_modify === false)
        if (cannot.length > 0) {
          message.warning(`查询到 ${priceResults.value.length} 条记录，其中 ${cannot.length} 条已对账不可修改`)
        } else {
          message.success(`查询到 ${priceResults.value.length} 条记录，可批量修改`)
        }
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    priceQuerying.value = false
  }
}

const handlePriceModify = async () => {
  if (priceResults.value.length === 0) {
    message.error('请先查询出记录')
    return
  }

  // 过滤出可修改的记录，循环调用存储过程更新
  const modifiable = priceResults.value.filter((r) => r.can_modify === true)
  if (modifiable.length === 0) {
    message.error('查询到的记录均已对账，不允许修改价格')
    return
  }

  priceModifying.value = true
  let successCount = 0
  const failList = []
  try {
    for (const detail of modifiable) {
      try {
        const res = await api.modifyPrice({
          detail_id: detail.detail_id,
          new_price: priceForm.value.new_price,
          remark: priceForm.value.remark,
        })
        if (res.code === 200) {
          successCount++
        } else {
          failList.push(`${detail.material_name}：${res.msg || '失败'}`)
        }
      } catch (e) {
        failList.push(detail.material_name)
      }
    }
    if (failList.length === 0) {
      message.success(`价格修改成功，共 ${successCount} 条`)
    } else {
      message.warning(`修改完成：成功 ${successCount} 条，失败 ${failList.length} 条`)
    }
    // 重新查询以更新结果
    await handlePriceQuery()
  } finally {
    priceModifying.value = false
  }
}

const handlePriceReset = () => {
  priceForm.value = { stock_code: '', material_name: '', new_price: '', remark: '' }
  priceResults.value = []
}
</script>
