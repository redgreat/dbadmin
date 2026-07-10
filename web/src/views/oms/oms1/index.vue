<template>
  <CommonPage show-footer>
    <n-form ref="formRef" :model="form" :rules="rules" label-placement="left" :label-width="100">
      <n-form-item label="订单Id/编码" path="orderIds">
        <n-input v-model:value="form.orderIds" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" placeholder="输入单个或多个订单Id或订单编码，逗号分隔" />
      </n-form-item>
      <n-form-item label="修改时间" path="auditTime">
        <n-date-picker v-model:value="form.auditTime" type="datetime" placeholder="请选择日期时间（东八区）" />
      </n-form-item>
      <n-form-item label="备注" path="remark">
        <n-input v-model:value="form.remark" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="非必填，记录运维日志使用" />
      </n-form-item>
      <n-space>
        <n-button :loading="querying" @click="handleQuery">查询</n-button>
        <n-button type="primary" :loading="executing" @click="handleExecute">执行</n-button>
        <n-button @click="handleReset">重置</n-button>
      </n-space>
      <n-table v-if="queryResult.length" :bordered="false" :single-line="false" size="small" class="mt-3">
        <thead>
          <tr>
            <th>订单Id</th>
            <th>订单编号</th>
            <th>审核时间</th>
            <th>删除状态</th>
            <th>删除人</th>
            <th>删除时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in queryResult" :key="item.id">
            <td>{{ item.id }}</td>
            <td>{{ item.order_no }}</td>
            <td>{{ item.audit_time || '-' }}</td>
            <td>
              <n-tag :type="item.deleted ? 'error' : 'success'" size="small">
                {{ item.deleted ? '已删除' : '正常' }}
              </n-tag>
            </td>
            <td>{{ item.deleted_by_name ? item.deleted_by_name + '-' + (item.deleted_by_code || '') + '-(' + item.deleted_by_id + ')' : (item.deleted_by_id || '-') }}</td>
            <td>{{ item.deleted_at || '-' }}</td>
          </tr>
        </tbody>
      </n-table>
    </n-form>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'
import dayjs from 'dayjs'

defineOptions({ name: '订单审核时间修改' })

const message = useMessage()
const formRef = ref(null)
const form = ref({ orderIds: '', auditTime: null, remark: '' })
const executing = ref(false)
const querying = ref(false)
const queryResult = ref([])

const rules = {
  orderIds: [
    { required: true, message: '请输入订单Id或订单编码' },
    {
      validator: (_, value) => {
        if (!value) return new Error('请输入订单Id或订单编码')
        const ids = value
          .split(',')
          .map((s) => s.trim())
          .filter((s) => s.length)
        if (!ids.length) return new Error('请输入订单Id或订单编码')
        return true
      },
    },
  ],
  auditTime: [{ required: true, message: '请选择修改时间' }],
}

const handleReset = () => {
  form.value = { orderIds: '', auditTime: null, remark: '' }
  queryResult.value = []
}

const handleQuery = async () => {
  const ids = form.value.orderIds
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length)
  if (!ids.length) {
    message.warning('请输入订单Id或订单编码')
    return
  }
  querying.value = true
  try {
    const res = await api.queryOrderStatus({ order_nos: ids })
    if (res.code === 200 || res.code === 0) {
      queryResult.value = res.data?.found_docs || []
      const notFound = res.data?.not_found_docs || []
      if (notFound.length) {
        message.warning(`查询完成，未找到 ${notFound.length} 条：${notFound.join(', ')}`)
      } else {
        message.success(`查询到 ${queryResult.value.length} 条`)
      }
    } else {
      message.error(res.msg || '查询失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    querying.value = false
  }
}

const handleExecute = async () => {
  await formRef.value?.validate()
  const ids = form.value.orderIds
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length)
  executing.value = true
  try {
    const audit_time = dayjs(form.value.auditTime).tz('Asia/Shanghai').format('YYYY-MM-DD HH:mm:ss')
    const remark = String(form.value.remark || '').trim()
    const payload = { order_nos: ids, audit_time, remark }
    const res = await api.updateOrdersAuditTimeBatch(payload)
    if (res.code === 200) {
      const { success_count = 0, failed_ids = [] } = res.data || {}
      if (failed_ids.length > 0) {
        message.warning(`执行完成：成功 ${success_count} 条，失败 ${failed_ids.length} 条。未找到的订单：${failed_ids.join(', ')}`)
      } else {
        message.success(`执行成功：${success_count} 条`)
      }
    } else {
      message.error(res.msg || '执行失败')
    }
  } catch (e) {
    message.error('请求异常')
  } finally {
    executing.value = false
  }
}
</script>
