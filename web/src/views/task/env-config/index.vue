<template>
  <CommonPage show-footer>
    <n-space vertical size="large">
      <!-- 环境变量配置 -->
      <n-card title="环境变量配置" size="small">
        <n-space justify="space-between" class="mb-3">
          <n-space>
            <n-input v-model:value="envSearchParams.key" clearable placeholder="搜索变量名" style="width: 200px" @keyup.enter="handleEnvSearch" />
            <n-button type="primary" @click="handleEnvSearch">搜索</n-button>
            <n-button @click="handleEnvReset">重置</n-button>
          </n-space>
          <n-button type="primary" @click="handleEnvCreate">新建变量</n-button>
        </n-space>

        <n-data-table
          ref="envTableRef"
          v-model:checked-row-keys="checkedEnvKeys"
          :row-key="(row) => row.id"
          :columns="envColumns"
          :data="envTableData"
          :loading="envLoading"
          :pagination="envPagination"
          :bordered="false"
          @update:page="handleEnvPageChange"
        />

        <n-space v-if="checkedEnvKeys.length > 0" class="mt-3" justify="start">
          <n-text type="info">已选择 {{ checkedEnvKeys.length }} 项</n-text>
          <n-button type="error" size="small" @click="handleBatchEnvDelete">批量删除</n-button>
        </n-space>
      </n-card>

      <!-- Python包管理 -->
      <n-card title="Python包管理" size="small">
        <n-space justify="space-between" class="mb-3">
          <n-space>
            <n-input v-model:value="pkgSearchParams.name" clearable placeholder="搜索包名" style="width: 200px" @keyup.enter="handlePkgSearch" />
            <n-select v-model:value="pkgSearchParams.is_installed" :options="installStatusOptions" clearable placeholder="安装状态" style="width: 120px" />
            <n-button type="primary" @click="handlePkgSearch">搜索</n-button>
            <n-button @click="handlePkgReset">重置</n-button>
          </n-space>
          <n-space>
            <n-button type="info" @click="showInstalledModal = true">查看已安装</n-button>
            <n-button type="primary" @click="handlePkgCreate">添加包</n-button>
          </n-space>
        </n-space>

        <n-data-table
          ref="pkgTableRef"
          v-model:checked-row-keys="checkedPkgKeys"
          :row-key="(row) => row.id"
          :columns="pkgColumns"
          :data="pkgTableData"
          :loading="pkgLoading"
          :pagination="pkgPagination"
          :bordered="false"
          @update:page="handlePkgPageChange"
        />

        <n-space v-if="checkedPkgKeys.length > 0" class="mt-3" justify="start">
          <n-text type="info">已选择 {{ checkedPkgKeys.length }} 项</n-text>
          <n-button type="success" size="small" @click="handleBatchInstall">批量安装</n-button>
          <n-button type="warning" size="small" @click="handleBatchUninstall">批量卸载</n-button>
        </n-space>
      </n-card>
    </n-space>

    <!-- 环境变量编辑弹窗 -->
    <n-modal v-model:show="showEnvModal" :title="envModalTitle" preset="card" style="width: 600px">
      <n-form ref="envFormRef" :model="envFormData" :rules="envFormRules" label-placement="left" :label-width="90">
        <n-form-item label="变量名" path="key">
          <n-input v-model:value="envFormData.key" placeholder="请输入变量名（大写字母_格式）" />
        </n-form-item>
        <n-form-item label="变量值" path="value">
          <n-input v-model:value="envFormData.value" placeholder="请输入变量值" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="envFormData.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="请输入描述" />
        </n-form-item>
        <n-form-item label="敏感信息" path="is_sensitive">
          <n-switch v-model:value="envFormData.is_sensitive">
            <template #checked>是</template>
            <template #unchecked>否</template>
          </n-switch>
          <n-text class="ml-2" depth="3">敏感信息会在列表中脱敏显示</n-text>
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showEnvModal = false">取消</n-button>
          <n-button type="primary" :loading="envSubmitting" @click="handleEnvSubmit">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 包编辑弹窗 -->
    <n-modal v-model:show="showPkgModal" :title="pkgModalTitle" preset="card" style="width: 600px">
      <n-form ref="pkgFormRef" :model="pkgFormData" :rules="pkgFormRules" label-placement="left" :label-width="90">
        <n-form-item label="包名" path="name">
          <n-input v-model:value="pkgFormData.name" placeholder="请输入包名" />
        </n-form-item>
        <n-form-item label="版本" path="version">
          <n-input v-model:value="pkgFormData.version" placeholder="请输入版本号（可选，如：1.0.0）" />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input v-model:value="pkgFormData.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="请输入描述" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showPkgModal = false">取消</n-button>
          <n-button type="primary" :loading="pkgSubmitting" @click="handlePkgSubmit">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 已安装包列表弹窗 -->
    <n-modal v-model:show="showInstalledModal" title="已安装的Python包" preset="card" style="width: 800px; max-width: 90vw">
      <n-data-table
        :columns="installedColumns"
        :data="installedPackages"
        :loading="installedLoading"
        :pagination="{ pageSize: 20 }"
        :bordered="false"
        style="max-height: 60vh; overflow-y: auto"
      />
    </n-modal>
  </CommonPage>
</template>

<script setup>
import { h, ref, reactive, onMounted } from 'vue'
import { useMessage, useDialog, NButton, NSpace, NTag, NText } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import api from '@/api'

defineOptions({ name: '环境配置管理' })

const message = useMessage()
const dialog = useDialog()

// 环境变量相关
const envLoading = ref(false)
const envSubmitting = ref(false)
const envTableData = ref([])
const envPagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })
const envSearchParams = reactive({ key: '' })
const showEnvModal = ref(false)
const envModalTitle = ref('')
const envFormRef = ref(null)
const envFormData = reactive({ id: null, key: '', value: '', description: '', is_sensitive: false })
const checkedEnvKeys = ref([])
const envTableRef = ref(null)

const envFormRules = {
  key: [{ required: true, message: '请输入变量名' }],
  value: [{ required: true, message: '请输入变量值' }],
}

// Python包相关
const pkgLoading = ref(false)
const pkgSubmitting = ref(false)
const pkgTableData = ref([])
const pkgPagination = reactive({ page: 1, pageSize: 10, itemCount: 0, showSizePicker: true, pageSizes: [10, 20, 50] })
const pkgSearchParams = reactive({ name: '', is_installed: null })
const showPkgModal = ref(false)
const pkgModalTitle = ref('')
const pkgFormRef = ref(null)
const pkgFormData = reactive({ id: null, name: '', version: '', description: '' })
const checkedPkgKeys = ref([])
const pkgTableRef = ref(null)

const pkgFormRules = {
  name: [{ required: true, message: '请输入包名' }],
}

const installStatusOptions = [
  { label: '已安装', value: true },
  { label: '未安装', value: false },
]

// 已安装包列表
const showInstalledModal = ref(false)
const installedLoading = ref(false)
const installedPackages = ref([])

const envColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '变量名', key: 'key', width: 150 },
  { title: '变量值', key: 'value', ellipsis: { tooltip: true } },
  { title: '描述', key: 'description', width: 200, render(row) { return row.description || '-' } },
  {
    title: '敏感',
    key: 'is_sensitive',
    width: 80,
    render(row) {
      return h(NTag, { type: row.is_sensitive ? 'warning' : 'default', size: 'small' }, { default: () => (row.is_sensitive ? '是' : '否') })
    },
  },
  { title: '创建时间', key: 'created_at', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render(row) {
      return h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => handleEnvEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', onClick: () => handleEnvDelete(row) }, { default: () => '删除' }),
        ],
      })
    },
  },
]

const pkgColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '包名', key: 'name', width: 150 },
  { title: '版本', key: 'version', width: 100, render(row) { return row.version || '-' } },
  { title: '描述', key: 'description', width: 200, render(row) { return row.description || '-' } },
  {
    title: '状态',
    key: 'is_installed',
    width: 100,
    render(row) {
      return h(NTag, { type: row.is_installed ? 'success' : 'default', size: 'small' }, { default: () => (row.is_installed ? '已安装' : '未安装') })
    },
  },
  { title: '安装时间', key: 'installed_at', width: 160, render(row) { return row.installed_at || '-' } },
  { title: '创建时间', key: 'created_at', width: 160 },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render(row) {
      return h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', disabled: row.is_installed, type: 'success', onClick: () => handlePkgInstall(row) }, { default: () => '安装' }),
          h(NButton, { size: 'small', disabled: !row.is_installed, type: 'warning', onClick: () => handlePkgUninstall(row) }, { default: () => '卸载' }),
          h(NButton, { size: 'small', onClick: () => handlePkgEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', type: 'error', onClick: () => handlePkgDelete(row) }, { default: () => '删除' }),
        ],
      })
    },
  },
]

const installedColumns = [
  { title: '包名', key: 'name', width: 200 },
  { title: '版本', key: 'version', width: 150 },
]

// 环境变量方法
const fetchEnvData = async () => {
  envLoading.value = true
  try {
    const res = await api.getEnvConfigs({
      page: envPagination.page,
      limit: envPagination.pageSize,
      key: envSearchParams.key || undefined,
    })
    if (res.code === 200) {
      envTableData.value = res.data || []
      envPagination.itemCount = res.total || 0
    }
  } catch (e) {
    message.error('获取环境变量列表失败')
  } finally {
    envLoading.value = false
  }
}

const handleEnvSearch = () => {
  envPagination.page = 1
  fetchEnvData()
}

const handleEnvReset = () => {
  envSearchParams.key = ''
  envPagination.page = 1
  fetchEnvData()
}

const handleEnvPageChange = (page) => {
  envPagination.page = page
  fetchEnvData()
}

const handleEnvCreate = () => {
  envModalTitle.value = '新建变量'
  envFormData.id = null
  envFormData.key = ''
  envFormData.value = ''
  envFormData.description = ''
  envFormData.is_sensitive = false
  showEnvModal.value = true
}

const handleEnvEdit = (row) => {
  envModalTitle.value = '编辑变量'
  envFormData.id = row.id
  envFormData.key = row.key
  envFormData.value = row.value === '******' ? '' : row.value
  envFormData.description = row.description
  envFormData.is_sensitive = row.is_sensitive
  showEnvModal.value = true
}

const handleEnvSubmit = async () => {
  try {
    await envFormRef.value?.validate()
  } catch (e) {
    return
  }

  envSubmitting.value = true
  try {
    if (envFormData.id) {
      await api.updateEnvConfig(envFormData.id, envFormData)
      message.success('更新成功')
    } else {
      await api.createEnvConfig(envFormData)
      message.success('创建成功')
    }
    showEnvModal.value = false
    fetchEnvData()
  } catch (e) {
    message.error('保存失败')
  } finally {
    envSubmitting.value = false
  }
}

const handleEnvDelete = (row) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除变量"${row.key}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteEnvConfig(row.id)
        message.success('删除成功')
        fetchEnvData()
      } catch (e) {
        message.error('删除失败')
      }
    },
  })
}

const handleBatchEnvDelete = () => {
  if (checkedEnvKeys.value.length === 0) {
    message.warning('请先选择要删除的变量')
    return
  }
  dialog.warning({
    title: '确认批量删除',
    content: `确定要删除选中的 ${checkedEnvKeys.value.length} 个变量吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        for (const id of checkedEnvKeys.value) {
          await api.deleteEnvConfig(id)
        }
        message.success('删除成功')
        checkedEnvKeys.value = []
        fetchEnvData()
      } catch (e) {
        message.error('删除失败')
      }
    },
  })
}

// Python包方法
const fetchPkgData = async () => {
  pkgLoading.value = true
  try {
    const res = await api.getPythonPackages({
      page: pkgPagination.page,
      limit: pkgPagination.pageSize,
      name: pkgSearchParams.name || undefined,
      status: pkgSearchParams.is_installed,
    })
    if (res.code === 200) {
      pkgTableData.value = res.data || []
      pkgPagination.itemCount = res.total || 0
    }
  } catch (e) {
    message.error('获取包列表失败')
  } finally {
    pkgLoading.value = false
  }
}

const handlePkgSearch = () => {
  pkgPagination.page = 1
  fetchPkgData()
}

const handlePkgReset = () => {
  pkgSearchParams.name = ''
  pkgSearchParams.is_installed = null
  pkgPagination.page = 1
  fetchPkgData()
}

const handlePkgPageChange = (page) => {
  pkgPagination.page = page
  fetchPkgData()
}

const handlePkgCreate = () => {
  pkgModalTitle.value = '添加包'
  pkgFormData.id = null
  pkgFormData.name = ''
  pkgFormData.version = ''
  pkgFormData.description = ''
  showPkgModal.value = true
}

const handlePkgEdit = (row) => {
  pkgModalTitle.value = '编辑包'
  pkgFormData.id = row.id
  pkgFormData.name = row.name
  pkgFormData.version = row.version
  pkgFormData.description = row.description
  showPkgModal.value = true
}

const handlePkgSubmit = async () => {
  try {
    await pkgFormRef.value?.validate()
  } catch (e) {
    return
  }

  pkgSubmitting.value = true
  try {
    if (pkgFormData.id) {
      await api.updatePythonPackage(pkgFormData.id, pkgFormData)
      message.success('更新成功')
    } else {
      await api.createPythonPackage(pkgFormData)
      message.success('创建成功')
    }
    showPkgModal.value = false
    fetchPkgData()
  } catch (e) {
    message.error('保存失败')
  } finally {
    pkgSubmitting.value = false
  }
}

const handlePkgDelete = (row) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除包"${row.name}"吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deletePythonPackage(row.id)
        message.success('删除成功')
        fetchPkgData()
      } catch (e) {
        message.error('删除失败')
      }
    },
  })
}

const handlePkgInstall = async (row) => {
  try {
    const res = await api.installPythonPackage(row.id)
    if (res.code === 200) {
      message.success('安装成功')
      fetchPkgData()
    } else {
      message.error(res.msg || '安装失败')
    }
  } catch (e) {
    message.error('安装失败')
  }
}

const handlePkgUninstall = async (row) => {
  try {
    const res = await api.uninstallPythonPackage(row.id)
    if (res.code === 200) {
      message.success('卸载成功')
      fetchPkgData()
    } else {
      message.error(res.msg || '卸载失败')
    }
  } catch (e) {
    message.error('卸载失败')
  }
}

const handleBatchInstall = async () => {
  if (checkedPkgKeys.value.length === 0) {
    message.warning('请先选择要安装的包')
    return
  }
  for (const id of checkedPkgKeys.value) {
    await api.installPythonPackage(id)
  }
  message.success('批量安装完成')
  checkedPkgKeys.value = []
  fetchPkgData()
}

const handleBatchUninstall = async () => {
  if (checkedPkgKeys.value.length === 0) {
    message.warning('请先选择要卸载的包')
    return
  }
  for (const id of checkedPkgKeys.value) {
    await api.uninstallPythonPackage(id)
  }
  message.success('批量卸载完成')
  checkedPkgKeys.value = []
  fetchPkgData()
}

const fetchInstalledPackages = async () => {
  installedLoading.value = true
  try {
    const res = await api.getInstalledPackages()
    if (res.code === 200) {
      installedPackages.value = res.data || []
    }
  } catch (e) {
    message.error('获取已安装包列表失败')
  } finally {
    installedLoading.value = false
  }
}

watch(showInstalledModal, (val) => {
  if (val) {
    fetchInstalledPackages()
  }
})

onMounted(() => {
  fetchEnvData()
  fetchPkgData()
})
</script>
