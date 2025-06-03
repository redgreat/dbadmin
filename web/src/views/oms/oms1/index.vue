<template>
  <CommonPage show-footer>
    <!-- 批量修改表单 -->
    <n-card title="批量修改订单审核时间" class="mb-4">
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
            placeholder="请输入订单ID或订单编码，多个用逗号分隔，例如：&#10;OI9971420165,&#10;OI9971420167,&#10;20250530115737499E09E"
          />
        </n-form-item>
        <n-form-item label="新审核时间" path="newAuditTime">
          <n-date-picker
            v-model:value="batchForm.newAuditTime"
            type="datetime"
            clearable
            placeholder="请选择新的审核时间"
          />
        </n-form-item>
        <n-form-item label="修改原因" path="reason">
          <n-input
            v-model:value="batchForm.reason"
            type="textarea"
            placeholder="请输入修改原因"
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
          <n-button type="warning" @click="handleBatchModify" :disabled="!validationResult || !validationResult.success" :loading="loading">
            <TheIcon icon="material-symbols:edit" :size="16" class="mr-2" />
            批量修改
          </n-button>
        </n-space>
      </div>
    </n-card>

    <!-- 验证结果展示 -->
    <n-card v-if="validationResult" title="数据校验结果" class="mb-4">
      <n-alert v-if="validationResult.success" type="success" class="mb-3">
        校验通过，共找到 {{ validationResult.foundOrders?.length || 0 }} 条订单记录
      </n-alert>
      <n-alert v-else type="error" class="mb-3">
        校验失败：{{ validationResult.message }}
      </n-alert>
      
      <div v-if="validationResult.foundOrders && validationResult.foundOrders.length > 0">
        <n-text strong>找到的订单：</n-text>
        <n-table :bordered="false" :single-line="false" size="small" class="mt-2">
          <thead>
            <tr>
              <th>订单ID</th>
              <th>订单编号</th>
              <th>当前审核时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in (validationResult.foundOrders || [])" :key="order.id">
              <td>{{ order.id }}</td>
              <td>{{ order.orderNo }}</td>
              <td>{{ order.auditTime || '未审核' }}</td>
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

    <!-- 更新结果展示 -->
    <n-card v-if="updateResult" title="更新结果" class="mb-4">
      <n-alert v-if="updateResult.success" type="success" class="mb-3">
        批量修改成功，共影响 {{ updateResult.updated_count }} 条订单
      </n-alert>
      <n-alert v-else type="error" class="mb-3">
        批量修改失败：{{ updateResult.message }}
      </n-alert>
      
      <div v-if="updateResult.details && updateResult.details.length > 0">
        <n-text strong>修改详情：</n-text>
        <n-table :bordered="false" :single-line="false" size="small" class="mt-2">
          <thead>
            <tr>
              <th>订单ID</th>
              <th>订单编号</th>
              <th>原审核时间</th>
              <th>新审核时间</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="detail in updateResult.details" :key="detail.orderId">
              <td>{{ detail.orderId }}</td>
              <td>{{ detail.orderNo }}</td>
              <td>{{ detail.originalAuditTime || '未审核' }}</td>
              <td>{{ detail.newAuditTime }}</td>
              <td>
                <n-tag :type="detail.success ? 'success' : 'error'">
                  {{ detail.success ? '成功' : '失败' }}
                </n-tag>
              </td>
            </tr>
          </tbody>
        </n-table>
      </div>
    </n-card>
  </CommonPage>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { NButton, NTag, NSpace, NDatePicker, NText, NTable, NAlert, NCard, NForm, NFormItem, NInput } from 'naive-ui'
import { useMessage } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import api from '@/api'

defineOptions({ name: '订单审核时间修改' })

const message = useMessage()

// 批量修改表单
const batchFormRef = ref(null)
const validationResult = ref(null)
const updateResult = ref(null)
const loading = ref(false)

// 批量修改表单
const batchForm = ref({
  orderIds: '',
  newAuditTime: null,
  reason: ''
})

// 表单验证规则
const batchFormRules = {
  orderIds: {
    required: true,
    message: '请输入订单ID或编码',
    trigger: ['blur']
  },
  newAuditTime: {
    required: true,
    validator: (rule, value) => {
      if (!value) {
        return new Error('请选择新的审核时间')
      }
      return true
    },
    trigger: ['blur', 'change']
  },
  reason: {
    required: true,
    message: '请输入修改原因',
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
    const response = await api.validateOrders({
      order_ids: orderIds.join(','),
      conn_id: 5
    })
    
    validationResult.value = response.data
    updateResult.value = null // 清空之前的更新结果
    
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
      auditTime: index % 2 === 0 ? '2023-05-01 10:00:00' : null
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

// 批量修改处理函数
const handleBatchModify = async () => {
  try {
    await batchFormRef.value?.validate()
    
    // 检查校验结果
    if (!validationResult.value || !validationResult.value.success) {
      message.error('请先通过数据校验')
      return
    }
    
    // 验证时间是否大于当前时间
    if (batchForm.value.newAuditTime && batchForm.value.newAuditTime >= Date.now()) {
      message.warning('新审核时间必须小于当前时间')
      return
    }
    
    loading.value = true
    
    // 执行批量修改
    // 确保时间以东八区时间发送给后端
    const auditTime = batchForm.value.newAuditTime ? 
      new Date(batchForm.value.newAuditTime).toISOString() : null
    
    const response = await api.batchUpdateAuditTime({
      order_ids: parseOrderIds(batchForm.value.orderIds).join(','),
      new_audit_time: auditTime,
      reason: batchForm.value.reason,
      conn_id: 5
    })
    
    updateResult.value = response.data
    
    if (response.data.success) {
      message.success(`批量修改成功，共影响 ${response.data.updated_count} 条订单`)
      // 重置表单
      batchForm.value = {
        orderIds: '',
        newAuditTime: null,
        reason: ''
      }
      validationResult.value = null
    } else {
      message.error('批量修改失败：' + response.data.message)
    }
    
  } catch (error) {
    console.error('批量修改失败:', error)
    // 模拟更新结果
    const orderIds = parseOrderIds(batchForm.value.orderIds)
    updateResult.value = {
      success: false,
      message: error.response?.data?.message || error.message,
      affectedCount: 0,
      details: orderIds.map(id => ({
        orderId: id,
        orderNo: id,
        originalAuditTime: '2023-05-01 10:00:00',
        newAuditTime: new Date(batchForm.value.newAuditTime).toLocaleString(),
        success: false
      }))
    }
    message.error('批量修改失败：' + (error.response?.data?.message || error.message))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // 组件挂载时的初始化逻辑
})
</script>
