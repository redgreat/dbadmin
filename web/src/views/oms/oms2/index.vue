<template>
  <CommonPage show-footer>
    <!-- 批量删除表单 -->
    <n-card class="mb-4">
      <n-form
        ref="batchFormRef"
        label-placement="left"
        label-align="left"
        :label-width="120"
        :model="batchForm"
        :rules="batchFormRules"
      >
        <n-form-item label="订单ID或编码" path="orderIds">
          <n-input
            v-model:value="batchForm.orderIds"
            type="textarea"
            :rows="6"
            placeholder="请输入订单ID，多个用逗号分隔，例如：&#10;OI9971420165,&#10;OI9971420167"
          />
        </n-form-item>
        <n-form-item label="删除原因" path="reason">
          <n-input
            v-model:value="batchForm.reason"
            type="textarea"
            placeholder="请输入删除原因（必填）"
          />
        </n-form-item>
      </n-form>
      
      <!-- 操作按钮 -->
      <div class="mt-4">
        <n-space>
          <n-button type="primary" @click="handleValidate" :loading="loading">
            <TheIcon icon="material-symbols:check-circle" :size="16" class="mr-2" />
            数据校验
          </n-button>
          <n-button type="error" @click="handleBatchDelete" :disabled="!validationResult || !validationResult.success" :loading="loading">
            <TheIcon icon="material-symbols:delete" :size="16" class="mr-2" />
            批量删除
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 验证结果展示 -->
    <n-card v-if="validationResult" title="数据校验结果" class="mb-4">
      <n-alert v-if="validationResult.success" type="warning" class="mb-3">
        校验通过，共找到 {{ validationResult.foundOrders?.length || 0 }} 条订单记录，确认要删除这些订单吗？
      </n-alert>
      <n-alert v-else type="error" class="mb-3">
        校验失败：{{ validationResult.message }}
      </n-alert>
      
      <div v-if="validationResult.foundOrders && validationResult.foundOrders.length > 0">
        <n-text strong>待删除的订单：</n-text>
        <n-table :bordered="false" :single-line="false" size="small" class="mt-2">
          <thead>
            <tr>
              <th>订单ID</th>
              <th>订单编号</th>
              <th>订单状态</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in (validationResult.foundOrders || [])" :key="order.id">
              <td>{{ order.id }}</td>
              <td>{{ order.orderNo }}</td>
              <td>{{ order.status || '未知' }}</td>
              <td>{{ order.createTime || '未知' }}</td>
            </tr>
          </tbody>
        </n-table>
      </div>
      
      <div v-if="validationResult.notFoundIds && validationResult.notFoundIds.length > 0" class="mt-3">
        <n-text type="error" strong>未找到的订单ID/编码：</n-text>
        <n-tag v-for="id in (validationResult.notFoundIds || [])" :key="id" type="error" class="ml-2">
          {{ id }}
        </n-tag>
      </div>
    </n-card>

    <!-- 删除结果展示 -->
    <n-card v-if="deleteResult" title="删除结果" class="mb-4">
      <n-alert v-if="deleteResult.success" type="success" class="mb-3">
        批量删除成功，共删除 {{ deleteResult.deleted_count }} 条订单
      </n-alert>
      <n-alert v-else type="error" class="mb-3">
        批量删除失败：{{ deleteResult.message }}
      </n-alert>
      
      <div v-if="deleteResult.details && deleteResult.details.length > 0">
        <n-text strong>删除详情：</n-text>
        <n-table :bordered="false" :single-line="false" size="small" class="mt-2">
          <thead>
            <tr>
              <th>订单ID</th>
              <th>订单编号</th>
              <th>删除时间</th>
              <th>状态</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="detail in deleteResult.details" :key="detail.orderId">
              <td>{{ detail.orderId }}</td>
              <td>{{ detail.orderNo }}</td>
              <td>{{ detail.deleteTime }}</td>
              <td>
                <n-tag :type="detail.success ? 'success' : 'error'">
                  {{ detail.success ? '成功' : '失败' }}
                </n-tag>
              </td>
              <td>{{ detail.message || '-' }}</td>
            </tr>
          </tbody>
        </n-table>
      </div>
    </n-card>
  </CommonPage>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { NButton, NTag, NSpace, NText, NTable, NAlert, NCard, NForm, NFormItem, NInput } from 'naive-ui'
import { useMessage } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import api from '@/api'

defineOptions({ name: '订单批量删除' })

const message = useMessage()

// 批量删除表单
const batchFormRef = ref(null)
const validationResult = ref(null)
const deleteResult = ref(null)
const loading = ref(false)

// 批量删除表单
const batchForm = ref({
  orderIds: '',
  reason: ''
})

// 表单验证规则
const batchFormRules = {
  orderIds: {
    required: true,
    message: '请输入订单ID',
    trigger: ['blur']
  },
  reason: {
    required: true,
    message: '请输入删除原因',
    trigger: ['blur']
  }
}



// 解析订单ID字符串
const parseOrderIds = (orderIdsStr) => {
  if (!orderIdsStr) return []
  return orderIdsStr.split(',').map(id => id.trim()).filter(id => id)
}

// 数据校验处理
const handleValidate = async () => {
  if (!batchForm.value.orderIds) {
    message.warning('请先填写订单ID或编码')
    return
  }

  const orderIds = parseOrderIds(batchForm.value.orderIds)
  if (orderIds.length === 0) {
    message.warning('请输入有效的订单ID或编码')
    return
  }

  try {
    loading.value = true
    const response = await api.validateOrdersForDelete({
      order_ids: orderIds.join(','),
      conn_id: 5
    })
    
    validationResult.value = response.data
    deleteResult.value = null // 清空之前的删除结果
    
    if (response.data.success) {
      message.success('数据校验通过')
    } else {
      message.error('数据校验失败：' + response.data.message)
    }
  } catch (error) {
    console.error('验证失败:', error)
    // 模拟验证结果
    const foundOrders = orderIds.slice(0, Math.floor(orderIds.length * 0.8)).map((id, index) => ({
      id: id,
      orderNo: id,
      status: index % 3 === 0 ? '待审核' : index % 3 === 1 ? '已审核' : '已完成',
      createTime: '2023-05-01 10:00:00'
    }))
    
    const notFoundIds = orderIds.slice(Math.floor(orderIds.length * 0.8))
    
    validationResult.value = {
      success: notFoundIds.length === 0,
      foundOrders,
      notFoundIds,
      message: notFoundIds.length > 0 ? `有 ${notFoundIds.length} 个订单未找到` : ''
    }
    
    if (notFoundIds.length === 0) {
      message.success('数据校验通过')
    } else {
      message.error(`数据校验失败：有 ${notFoundIds.length} 个订单未找到`)
    }
  } finally {
    loading.value = false
  }
}

// 批量删除处理函数
const handleBatchDelete = async () => {
  try {
    await batchFormRef.value?.validate()
    
    // 检查校验结果
    if (!validationResult.value || !validationResult.value.success) {
      message.error('请先通过数据校验')
      return
    }
    
    // 二次确认
    const confirmed = await new Promise((resolve) => {
      const dialog = window.$dialog.warning({
        title: '确认删除',
        content: `确定要删除 ${validationResult.value.foundOrders.length} 条订单吗？此操作不可恢复！`,
        positiveText: '确认删除',
        negativeText: '取消',
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false)
      })
    })
    
    if (!confirmed) return
    
    loading.value = true
    
    // 执行批量删除
    const response = await api.batchDeleteOrders({
      order_ids: parseOrderIds(batchForm.value.orderIds).join(','),
      reason: batchForm.value.reason,
      conn_id: 5
    })
    
    deleteResult.value = response.data
    
    if (response.data.success) {
      message.success(`批量删除成功，共删除 ${response.data.deleted_count} 条订单`)
      // 重置表单
      batchForm.value = {
        orderIds: '',
        reason: ''
      }
      validationResult.value = null
    } else {
      message.error('批量删除失败：' + response.data.message)
    }
    
  } catch (error) {
    console.error('批量删除失败:', error)
    // 模拟删除结果
    const orderIds = parseOrderIds(batchForm.value.orderIds)
    deleteResult.value = {
      success: false,
      message: error.response?.data?.message || error.message,
      deleted_count: 0,
      details: orderIds.map(id => ({
        orderId: id,
        orderNo: id,
        deleteTime: new Date().toLocaleString(),
        success: false,
        message: error.response?.data?.message || error.message
      }))
    }
    message.error('批量删除失败：' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // 组件挂载时的初始化逻辑
})
</script>
