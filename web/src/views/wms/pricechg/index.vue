<template>
  <CommonPage show-footer>
    <n-card title="价格查询与修改" size="small">
      <n-form ref="priceFormRef" :model="priceForm" :rules="priceRules" label-placement="left" :label-width="100">
        <n-form-item label="入库单编码" path="stock_code">
          <n-input v-model:value="priceForm.stock_code" clearable placeholder="请输入入库单编码" />
        </n-form-item>
        <n-form-item label="物料名称" path="material_name">
          <n-input v-model:value="priceForm.material_name" clearable placeholder="请输入物料名称" />
        </n-form-item>
        <n-form-item label="修改后价格" path="new_price">
          <n-input v-model:value="priceForm.new_price" clearable placeholder="请输入修改后价格（decimal(18,2)）" />
        </n-form-item>
        <n-space>
          <n-button type="primary" :loading="priceQuerying" @click="handlePriceQuery">查询</n-button>
          <n-button type="warning" :loading="priceModifying" :disabled="!canModify" @click="handlePriceModify">修改</n-button>
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
const priceForm = ref({ stock_code: '', material_name: '', new_price: '' })
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

const priceColumns = [
  { title: '明细Id', key: 'detail_id' },
  { title: '物料名称', key: 'material_name' },
  { title: '原价格', key: 'original_price' },
  { title: '新价格', key: 'new_price' },
]

const canModify = computed(() => priceResults.value.length === 1)

const handlePriceQuery = async () => {
  priceQuerying.value = true
  try {
    const res = await api.queryPrice({
      stock_code: priceForm.value.stock_code,
      material_name: priceForm.value.material_name,
      new_price: priceForm.value.new_price,
    })
    if (res.code === 200) {
      priceResults.value = res.data || []
      if (priceResults.value.length === 0) {
        message.warning('未查询到符合条件的记录')
      } else if (priceResults.value.length > 1) {
        message.warning('查询到多条记录，请缩小查询范围')
      } else {
        message.success('查询成功')
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
  if (priceResults.value.length !== 1) {
    message.error('请先查询出唯一一条记录')
    return
  }
  
  priceModifying.value = true
  try {
    const detail = priceResults.value[0]
    const res = await api.modifyPrice({
      detail_id: detail.detail_id,
      new_price: priceForm.value.new_price,
    })
    if (res.code === 200) {
      message.success('价格修改成功')
      // 重新查询以更新结果
      await handlePriceQuery()
    } else {
      message.error(res.msg || '价格修改失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    priceModifying.value = false
  }
}

const handlePriceReset = () => {
  priceForm.value = { stock_code: '', material_name: '', new_price: '' }
  priceResults.value = []
}
</script>
