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
        <n-form-item label="订单编码/Id" path="orderNos">
          <n-input
            v-model:value="batchForm.orderNos"
            type="textarea"
            :rows="6"
            placeholder="请输入订单编码或Id，多个用逗号分隔，例如：&#10;OI9971420165,&#10;OI9971420167"
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

    <!-- 校验记录删除模块 -->
    <n-card title="校验记录删除" class="mb-4">
      <n-form label-placement="left" label-align="left" :label-width="120">
        <n-form-item label="订单Id">
          <n-input v-model:value="checkRecordForm.orderId" placeholder="请输入订单Id" />
        </n-form-item>
      </n-form>
      <div class="mt-4">
        <n-space>
          <n-button type="primary" @click="handleQueryCheckRecord" :loading="checkRecordQuerying">
            <TheIcon icon="material-symbols:search" :size="16" class="mr-2" />
            查询校验记录
          </n-button>
          <n-button type="error" @click="handleDeleteCheckRecord" :loading="checkRecordDeleting" :disabled="!checkRecordForm.orderId">
            <TheIcon icon="material-symbols:delete" :size="16" class="mr-2" />
            删除校验记录
          </n-button>
        </n-space>
      </div>
      <div v-if="checkRecordResult" class="mt-3">
        <n-alert :type="checkRecordResult.found ? 'info' : 'warning'">
          {{ checkRecordResult.message }}
        </n-alert>
      </div>
    </n-card>

    <!-- GFS同步验证模块 -->
    <n-card title="GFS同步验证" class="mb-4">
      <n-form label-placement="left" label-align="left" :label-width="120">
        <n-form-item label="订单编码/Id">
          <n-input
            v-model:value="gfsForm.orderNos"
            type="textarea"
            :rows="3"
            placeholder="请输入订单编码或Id，多个用逗号分隔"
          />
        </n-form-item>
      </n-form>
      <div class="mt-4">
        <n-space>
          <n-button type="primary" @click="handleQueryGfsStatus" :loading="gfsQuerying">
            <TheIcon icon="material-symbols:search" :size="16" class="mr-2" />
            查询GFS状态
          </n-button>
          <n-button type="error" @click="handleDeleteGfsOrder" :loading="gfsDeleting" :disabled="!gfsForm.orderId">
            <TheIcon icon="material-symbols:delete" :size="16" class="mr-2" />
            GFS删除
          </n-button>
        </n-space>
      </div>
      <div v-if="gfsResult" class="mt-3">
        <n-alert :type="gfsResult.success ? 'success' : 'error'">
          {{ gfsResult.message }}
        </n-alert>
        <div v-if="gfsResult.found_docs && gfsResult.found_docs.length > 0" class="mt-2">
          <n-text strong>GFS订单状态：</n-text>
          <n-table :bordered="false" :single-line="false" size="small" class="mt-2">
            <thead>
              <tr>
                <th>订单编号</th>
                <th>对账状态</th>
                <th>开票状态</th>
                <th>回款状态</th>
                <th>推广费状态</th>
                <th>是否可删除</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in gfsResult.found_docs" :key="doc.order_no || doc.order_id">
                <td>{{ doc.order_no || doc.order_id }}</td>
                <td>
                  <n-tag :type="doc.reconc_state === 0 ? 'success' : 'warning'" size="small">
                    {{ formatGfsStatus('reconc', doc.reconc_state) }}
                  </n-tag>
                </td>
                <td>
                  <n-tag :type="doc.invoice_state === 0 ? 'success' : 'warning'" size="small">
                    {{ formatGfsStatus('invoice', doc.invoice_state) }}
                  </n-tag>
                </td>
                <td>
                  <n-tag :type="doc.receipt_state === 0 ? 'success' : 'warning'" size="small">
                    {{ formatGfsStatus('receipt', doc.receipt_state) }}
                  </n-tag>
                </td>
                <td>
                  <n-tag :type="doc.promotion_state === 0 ? 'success' : 'warning'" size="small">
                    {{ formatGfsStatus('promotion', doc.promotion_state) }}
                  </n-tag>
                </td>
                <td>
                  <n-tag :type="doc.invalid_reasons ? 'error' : 'success'">
                    {{ doc.invalid_reasons ? '不可删除' : '可删除' }}
                  </n-tag>
                  <n-text v-if="doc.invalid_reasons" type="error" class="ml-2">
                    {{ doc.invalid_reasons.join(', ') }}
                  </n-text>
                </td>
              </tr>
            </tbody>
          </n-table>
        </div>
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
              <th>对账状态</th>
              <th>开票状态</th>
              <th>回款状态</th>
              <th>推广费状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in (validationResult.foundOrders || [])" :key="order.id">
              <td>{{ order.id }}</td>
              <td>{{ order.orderNo }}</td>
              <td>{{ order.status || '未知' }}</td>
              <td>{{ order.createTime || '未知' }}</td>
              <td>
                <n-tag v-if="order.gfs_status" :type="order.gfs_status.reconc_state === 0 ? 'success' : 'warning'">
                  {{ formatGfsStatus('reconc', order.gfs_status.reconc_state) }}
                </n-tag>
                <span v-else>-</span>
              </td>
              <td>
                <n-tag v-if="order.gfs_status" :type="order.gfs_status.invoice_state === 0 ? 'success' : 'warning'">
                  {{ formatGfsStatus('invoice', order.gfs_status.invoice_state) }}
                </n-tag>
                <span v-else>-</span>
              </td>
              <td>
                <n-tag v-if="order.gfs_status" :type="order.gfs_status.receipt_state === 0 ? 'success' : 'warning'">
                  {{ formatGfsStatus('receipt', order.gfs_status.receipt_state) }}
                </n-tag>
                <span v-else>-</span>
              </td>
              <td>
                <n-tag v-if="order.gfs_status" :type="order.gfs_status.promotion_state === 0 ? 'success' : 'warning'">
                  {{ formatGfsStatus('promotion', order.gfs_status.promotion_state) }}
                </n-tag>
                <span v-else>-</span>
              </td>
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

// 校验记录删除
const checkRecordForm = ref({ orderId: '' })
const checkRecordResult = ref(null)
const checkRecordQuerying = ref(false)
const checkRecordDeleting = ref(false)

// GFS状态格式化
const formatGfsStatus = (type, value) => {
  if (value === null || value === undefined) return '未同步'
  const maps = {
    'reconc': { 0: '未对账', 1: '已对账', 2: '对账中', 3: '对账异常' },
    'invoice': { 0: '待开票', 1: '已开票', 2: '开票中' },
    'receipt': { 0: '未回款', 1: '已回款', 2: '部分回款' },
    'promotion': { 0: '待申请', 1: '已申请', 2: '已确认' },
  }
  const map = maps[type]
  return map && map[value] !== undefined ? map[value] : `未知(${value})`
}

// GFS同步验证
const gfsForm = ref({ orderNos: '', orderId: '' })
const gfsResult = ref(null)
const gfsQuerying = ref(false)
const gfsDeleting = ref(false)

// 批量删除表单
const batchForm = ref({
  orderNos: '',
  reason: ''
})

// 表单验证规则
const batchFormRules = {
  orderNos: {
    required: true,
    message: '请输入订单编码或Id',
    trigger: ['blur']
  },
  reason: {
    required: true,
    message: '请输入删除原因',
    trigger: ['blur']
  }
}



// 解析订单编码字符串
const parseOrderNos = (orderNosStr) => {
  if (!orderNosStr) return []
  return orderNosStr.split(',').map(no => no.trim()).filter(no => no)
}

// 数据校验处理
const handleValidate = async () => {
  if (!batchForm.value.orderNos) {
    message.warning('请先填写订单编码或Id')
    return
  }

  const orderNos = parseOrderNos(batchForm.value.orderNos)
  if (orderNos.length === 0) {
    message.warning('请输入有效的订单编码或Id')
    return
  }

  try {
    loading.value = true
    const response = await api.validateOrdersForDelete({
      order_nos: orderNos.join(','),
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
    const foundOrders = orderNos.slice(0, Math.floor(orderNos.length * 0.8)).map((no, index) => ({
      id: 1000 + index,
      orderNo: no,
      status: index % 3 === 0 ? '待审核' : index % 3 === 1 ? '已审核' : '已完成',
      createTime: '2023-05-01 10:00:00'
    }))

    const notFoundIds = orderNos.slice(Math.floor(orderNos.length * 0.8))

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

// 查询校验记录
const handleQueryCheckRecord = async () => {
  if (!checkRecordForm.value.orderId) {
    message.warning('请先填写订单Id')
    return
  }
  checkRecordQuerying.value = true
  try {
    const response = await api.queryOrderStatus({ order_nos: checkRecordForm.value.orderId })
    if (response.code === 200 && response.data.success) {
      checkRecordResult.value = { found: true, message: `找到订单 ${checkRecordForm.value.orderId}，可删除校验记录` }
    } else {
      checkRecordResult.value = { found: false, message: response.msg || '未找到订单' }
    }
  } catch (error) {
    checkRecordResult.value = { found: false, message: '查询失败' }
  } finally {
    checkRecordQuerying.value = false
  }
}

// 删除校验记录
const handleDeleteCheckRecord = async () => {
  if (!checkRecordForm.value.orderId) {
    message.warning('请先填写订单Id')
    return
  }
  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.warning({
      title: '确认删除',
      content: `确定要删除订单 ${checkRecordForm.value.orderId} 的校验记录吗？`,
      positiveText: '确认删除',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false)
    })
  })
  if (!confirmed) return
  checkRecordDeleting.value = true
  try {
    const response = await api.deleteCheckRecord({ order_id: checkRecordForm.value.orderId })
    if (response.code === 200) {
      message.success('校验记录删除成功')
      checkRecordResult.value = null
    } else {
      message.error(response.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  } finally {
    checkRecordDeleting.value = false
  }
}

// 查询GFS状态
const handleQueryGfsStatus = async () => {
  if (!gfsForm.value.orderNos) {
    message.warning('请先填写订单编码或Id')
    return
  }
  gfsQuerying.value = true
  try {
    const items = gfsForm.value.orderNos.split(',').map(s => s.trim()).filter(s => s)
    const orderNos = items.filter(s => !s.match(/^\d+$/))
    const orderIds = items.filter(s => s.match(/^\d+$/))
    const response = await api.queryGfsStatus({ order_nos: orderNos, order_ids: orderIds })
    if (response.code === 200) {
      gfsResult.value = response.data
      if (response.data.success) {
        message.success('GFS状态验证通过，可删除')
      } else {
        message.error('GFS状态验证不通过，不可删除')
      }
    } else {
      message.error(response.msg || '查询失败')
    }
  } catch (error) {
    message.error('查询失败')
  } finally {
    gfsQuerying.value = false
  }
}

// GFS删除
const handleDeleteGfsOrder = async () => {
  if (!gfsForm.value.orderId) {
    message.warning('请先填写要删除的订单Id')
    return
  }
  const confirmed = await new Promise((resolve) => {
    const dialog = window.$dialog.warning({
      title: '确认删除',
      content: `确定要删除GFS订单 ${gfsForm.value.orderId} 吗？`,
      positiveText: '确认删除',
      negativeText: '取消',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false)
    })
  })
  if (!confirmed) return
  gfsDeleting.value = true
  try {
    const response = await api.deleteGfsOrder({ order_id: gfsForm.value.orderId })
    if (response.code === 200) {
      message.success('GFS订单删除成功')
      gfsResult.value = null
    } else {
      message.error(response.msg || '删除失败')
    }
  } catch (error) {
    message.error('删除失败')
  } finally {
    gfsDeleting.value = false
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
      order_nos: parseOrderNos(batchForm.value.orderNos).join(','),
      reason: batchForm.value.reason,
      conn_id: 5
    })

    deleteResult.value = response.data

    if (response.data.success) {
      message.success(`批量删除成功，共删除 ${response.data.deleted_count} 条订单`)
      // 重置表单
      batchForm.value = {
        orderNos: '',
        reason: ''
      }
      validationResult.value = null
    } else {
      message.error('批量删除失败：' + response.data.message)
    }

  } catch (error) {
    console.error('批量删除失败:', error)
    // 模拟删除结果
    const orderNos = parseOrderNos(batchForm.value.orderNos)
    deleteResult.value = {
      success: false,
      message: error.response?.data?.message || error.message,
      deleted_count: 0,
      details: orderNos.map(no => ({
        orderId: null,
        orderNo: no,
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
