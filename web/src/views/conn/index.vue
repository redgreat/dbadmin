<template>
  <CommonPage show-footer>
    <template #action>
      <div>
        <n-button class="float-right mr-15" type="primary" @click="handleAdd">
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新增连接
        </n-button>
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
        <QueryBarItem label="连接名称" :label-width="80">
          <n-input
            v-model:value="queryItems.name"
            clearable
            type="text"
            placeholder="请输入连接名称"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <!-- 新增/编辑 弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave"
    >
      <n-form
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="100"
        :model="modalForm"
        :rules="rules"
      >
        <n-form-item label="连接名称" path="name">
          <n-input v-model:value="modalForm.name" clearable placeholder="请输入连接名称" />
        </n-form-item>
        <n-form-item label="数据库类型" path="dbType">
          <n-select
            v-model:value="modalForm.dbType"
            :options="dbTypeOptions"
            placeholder="请选择数据库类型"
          />
        </n-form-item>
        <n-form-item label="主机地址" path="host">
          <n-input v-model:value="modalForm.host" clearable placeholder="请输入主机地址" />
        </n-form-item>
        <n-form-item label="端口" path="port">
          <n-input-number v-model:value="modalForm.port" clearable placeholder="请输入端口" />
        </n-form-item>
        <n-form-item label="用户名" path="username">
          <n-input v-model:value="modalForm.username" clearable placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="modalForm.password"
            type="password"
            show-password-on="click"
            clearable
            placeholder="请输入密码"
          />
        </n-form-item>
        <n-form-item label="数据库名" path="database">
          <n-input v-model:value="modalForm.database" clearable placeholder="请输入数据库名" />
        </n-form-item>
        <n-form-item label="连接参数" path="params">
          <n-input v-model:value="modalForm.params" type="textarea" placeholder="请输入连接参数" />
        </n-form-item>
        <n-form-item label="备注" path="remark">
          <n-input v-model:value="modalForm.remark" type="textarea" placeholder="请输入备注信息" />
        </n-form-item>
      </n-form>
    </CrudModal>
  </CommonPage>
</template>

<script setup>
import { h, onMounted, ref, resolveDirective } from 'vue'
import { NButton, NTag, NSpace } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { useCRUD } from '@/composables'
import api from '@/api'
import { useMessage } from 'naive-ui'

defineOptions({ name: '数据库连接管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')
const $message = useMessage()

// 数据库类型选项（与后端当前支持保持一致）
const dbTypeOptions = [
  { label: 'MySQL', value: 'mysql' },
  { label: 'PostgreSQL', value: 'postgresql' },
]

// 连接状态选项
const statusOptions = [
  { label: '已连接', value: 1 },
  { label: '未连接', value: 0 },
]

// 获取数据的API
const getData = async (params) => {
  try {
    const query = { ...params }
    if (Object.prototype.hasOwnProperty.call(query, 'dbType')) {
      query.db_type = query.dbType
      delete query.dbType
    }
    if (Object.prototype.hasOwnProperty.call(query, 'status') && query.status !== undefined && query.status !== null) {
      query.status = query.status === 1 || query.status === '1'
    }
    const res = await api.getConnList(query)
    if (res.code === 200) {
      const items = res.data.map(item => ({
        ...item,
        dbType: item.db_type,
        status: item.status ? 1 : 0,
        createTime: item.created_at,
        updateTime: item.updated_at
      }))
      return { data: items, total: res.total }
    } else {
      $message.error(res.msg || '获取数据失败')
      return { data: [], total: 0 }
    }
  } catch (error) {
    console.error('获取数据库连接列表失败', error)
    $message.error('获取数据库连接列表失败')
    return { data: [], total: 0 }
  }
}

// 获取状态标签类型
const getStatusType = (status) => {
  const map = {
    0: 'error',
    1: 'success',
  }
  return map[status] || 'default'
}

// 获取状态标签文本
const getStatusText = (status) => {
  const map = {
    0: '未连接',
    1: '已连接',
  }
  return map[status] || '未知状态'
}

// 获取数据库类型文本
const getDbTypeText = (dbType) => {
  const option = dbTypeOptions.find(item => item.value === dbType)
  return option ? option.label : dbType
}

// 表格列定义
const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '连接名称', key: 'name', width: 150 },
  {
    title: '数据库类型',
    key: 'dbType',
    width: 120,
    render(row) {
      return h('span', {}, getDbTypeText(row.dbType))
    }
  },
  { title: '主机地址', key: 'host', width: 150 },
  { title: '端口', key: 'port', width: 80 },
  { title: '用户名', key: 'username', width: 120 },
  { title: '数据库名', key: 'database', width: 120 },
  {
    title: '连接状态',
    key: 'status',
    width: 100,
    render(row) {
      return h(
        NTag,
        { type: getStatusType(row.status) },
        { default: () => getStatusText(row.status) }
      )
    },
  },
  { title: '创建时间', key: 'createTime', width: 180 },
  { title: '更新时间', key: 'updateTime', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 250,
    fixed: 'right',
    render(row) {
      return h(NSpace, { justify: 'center' }, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              onClick: () => handleEdit(row),
            },
            { default: () => '编辑' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'info',
              onClick: () => handleTest(row),
            },
            { default: () => '测试连接' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              onClick: () => handleDelete(row.id),
            },
            { default: () => '删除' }
          ),
        ],
      })
    },
  },
]

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: '数据库连接',
  initForm: {
    name: '',
    dbType: 'postgresql',
    host: 'localhost',
    port: 5432,
    username: '',
    password: '',
    database: '',
    params: '',
    remark: '',
  },
  doCreate: async (data) => {
    try {
      // 将前端字段名转换为后端字段名
      const apiData = {
        name: data.name,
        db_type: data.dbType,
        host: data.host,
        port: data.port,
        username: data.username,
        password: data.password,
        database: data.database,
        params: data.params,
        remark: data.remark,
      }
      const res = await api.createConn(apiData)
      if (res.code === 200) {
        $message.success(res.msg || '创建成功')
        return Promise.resolve()
      } else {
        $message.error(res.msg || '创建失败')
        return Promise.reject(new Error(res.msg || '创建失败'))
      }
    } catch (error) {
      console.error('创建数据库连接失败', error)
      $message.error('创建数据库连接失败')
      return Promise.reject(error)
    }
  },
  doUpdate: async (data) => {
    try {
      // 将前端字段名转换为后端字段名
      const apiData = {
        id: data.id,
        name: data.name,
        db_type: data.dbType,
        host: data.host,
        port: data.port,
        username: data.username,
        password: data.password,
        database: data.database,
        params: data.params,
        remark: data.remark,
      }
      const res = await api.updateConn(apiData)
      if (res.code === 200) {
        $message.success(res.msg || '更新成功')
        return Promise.resolve()
      } else {
        $message.error(res.msg || '更新失败')
        return Promise.reject(new Error(res.msg || '更新失败'))
      }
    } catch (error) {
      console.error('更新数据库连接失败', error)
      $message.error('更新数据库连接失败')
      return Promise.reject(error)
    }
  },
  doDelete: async (id) => {
    try {
      const res = await api.deleteConn({ conn_id: id })
      if (res.code === 200) {
        $message.success(res.msg || '删除成功')
        return Promise.resolve()
      } else {
        $message.error(res.msg || '删除失败')
        return Promise.reject(new Error(res.msg || '删除失败'))
      }
    } catch (error) {
      console.error('删除数据库连接失败', error)
      $message.error('删除数据库连接失败')
      return Promise.reject(error)
    }
  },
  refresh: () => $table.value?.handleSearch(),
})

// 表单校验规则（函数级中文注释）
const rules = {
  name: [{ required: true, message: '请输入连接名称' }],
  dbType: [{ required: true, message: '请选择数据库类型' }],
  host: [{ required: true, message: '请输入主机地址' }],
  port: [
    { required: true, message: '请输入端口' },
    {
      validator: (_, value) => {
        return typeof value === 'number' && value > 0
      },
      message: '端口必须为正整数',
    },
  ],
  username: [{ required: true, message: '请输入用户名' }],
  password: [
    {
      validator: (_, value) => {
        // 新增时必须填写密码，编辑时可选
        return modalForm.value?.id ? true : !!value
      },
      message: '请输入密码',
    },
  ],
  database: [{ required: true, message: '请输入数据库名' }],
}

// 测试连接
const handleTest = async (row) => {
  try {
    const password = window.prompt(`请输入连接 ${row.name} 的明文密码用于测试`)
    if (!password) {
      $message.error('请输入密码')
      return
    }
    $message.loading(`正在测试连接 ${row.name}...`)
    const res = await api.testConn({ id: row.id, password })
    if (res.code === 200) {
      $message.success(res.msg || `连接 ${row.name} 测试成功`)
      $table.value?.handleSearch()
    } else {
      $message.error(res.msg || `连接 ${row.name} 测试失败`)
      $table.value?.handleSearch()
    }
  } catch (error) {
    console.error('测试连接失败', error)
    $message.error(`测试连接 ${row.name} 失败`)
  }
}

// 刷新数据
const handleRefresh = () => {
  $table.value?.handleSearch()
}

onMounted(() => {
  $table.value?.handleSearch()
})
</script>
