<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="info" @click="handleRefresh">
          <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />刷新数据
        </n-button>
      </div>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="getData"
    >
      <template #queryBar>
        <QueryBarItem label="系统名称" :label-width="80">
          <n-select
            v-model:value="queryItems.system_name"
            :options="systemNameOptions"
            clearable
            filterable
            placeholder="请选择系统名称"
          />
        </QueryBarItem>
        <QueryBarItem label="报表名称" :label-width="80">
          <n-input
            v-model:value="queryItems.report_name"
            clearable
            type="text"
            placeholder="请输入报表名称"
          />
        </QueryBarItem>
      </template>
    </CrudTable>
  </CommonPage>
</template>

<script setup>
import { h, ref, computed, onMounted } from 'vue'
import { NButton, NTag, NSpace, NIcon, useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '@/store'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import api from '@/api'

defineOptions({ name: '报表生成' })

const $table = ref(null)
const queryItems = ref({})
const $message = useMessage()
const $dialog = useDialog()
const userStore = useUserStore()

// 判断是否为管理员（超级管理员或拥有admin角色）
const isAdmin = computed(() => userStore.isSuperUser || userStore.role?.includes('admin'))

// 系统名称选项
const systemNameOptions = ref([])

// 状态选项
const statusOptions = [
  { label: '导出中', value: 'exporting' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' }
]

// 状态图标和颜色
const getStatusInfo = (status) => {
  switch (status) {
    case 'exporting':
      return { type: 'info', text: '导出中', icon: 'eos-icons:loading' }
    case 'completed':
      return { type: 'success', text: '已完成', icon: 'material-symbols:check-circle' }
    case 'failed':
      return { type: 'error', text: '失败', icon: 'material-symbols:cancel' }
    default:
      return { type: 'default', text: '未知', icon: 'material-symbols:help' }
  }
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '报表名称', key: 'report_name', width: 250 },
  { title: '生成人', key: 'generator', width: 100 },
  {
    title: '生成时间',
    key: 'generated_at',
    width: 180
  },
  {
    title: '完成时间',
    key: 'completed_at',
    width: 180,
    render: (row) => row.completed_at || '-'
  },
  {
    title: '报表状态',
    key: 'status',
    width: 120,
    render: (row) => {
      const statusInfo = getStatusInfo(row.status)
      return h(
        NTag,
        { type: statusInfo.type },
        {
          default: () =>
            h(NSpace, { align: 'center' }, {
              default: () => [
                h(NIcon, { size: 16, class: row.status === 'exporting' ? 'animate-spin' : '' }, {
                  default: () => h(TheIcon, { icon: statusInfo.icon })
                }),
                statusInfo.text
              ]
            })
        }
      )
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right',
    render: (row) => {
      const buttons = []

      // 下载按钮（仅完成状态可用）
      if (row.status === 'completed') {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: () => handleDownload(row)
            },
            { default: () => '下载' }
          )
        )
      }

      // 删除按钮（管理员可删除所有，普通用户只能删除自己生成的）
      if (isAdmin.value || row.generator === userStore.username) {
        buttons.push(
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              style: 'margin-left: 8px',
              onClick: () => handleDelete(row)
            },
            { default: () => '删除' }
          )
        )
      }

      return h(NSpace, null, { default: () => buttons })
    }
  }
]

// 获取数据的API
const getData = async (params) => {
  try {
    const res = await api.getReportGenerationList(params)
    if (res.code === 200) {
      return { data: res.data, total: res.total }
    } else {
      $message.error(res.msg || '获取数据失败')
      return { data: [], total: 0 }
    }
  } catch (error) {
    console.error('获取报表生成列表失败', error)
    $message.error('获取数据失败')
    return { data: [], total: 0 }
  }
}

// 刷新数据
const handleRefresh = () => {
  $table.value?.handleSearch()
}

// 下载报表
const handleDownload = async (row) => {
  try {
    $message.info('正在下载，请稍候...')
    const response = await api.downloadReport({ generation_id: row.id })

    // 创建下载链接
    const blob = new Blob([response])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // 从报表名称提取文件名
    const fileName = row.report_name.endsWith('.zip')
      ? `${row.report_name}.zip`
      : `${row.report_name}.xlsx`
    link.setAttribute('download', fileName)

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    $message.success('下载成功')
  } catch (error) {
    console.error('下载报表失败', error)
    $message.error('下载失败')
  }
}

// 删除报表
const handleDelete = (row) => {
  $dialog.warning({
    title: '确认删除',
    content: `确定要删除报表"${row.report_name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await api.deleteReportGeneration({ generation_id: row.id })
        if (res.code === 200) {
          $message.success('删除成功')
          handleRefresh()
        } else {
          $message.error(res.msg || '删除失败')
        }
      } catch (error) {
        console.error('删除报表失败', error)
        $message.error('删除失败')
      }
    }
  })
}

// 加载系统名称选项
const loadSystemNameOptions = async () => {
  try {
    const res = await api.getSystemNameOptions()
    if (res.code === 200) {
      systemNameOptions.value = res.data
    }
  } catch (error) {
    console.error('获取系统名称选项失败', error)
  }
}

onMounted(() => {
  loadSystemNameOptions()
  // 首次加载数据
  $table.value?.handleSearch()
})
</script>

<style scoped>
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
