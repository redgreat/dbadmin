<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives, computed } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NPopconfirm,
  NSwitch,
  NTreeSelect,
  NRadio,
  NRadioGroup,
  NTag,
  NDrawer,
  NDrawerContent,
  NTree,
  NCollapse,
  NCollapseItem,
  NCheckbox,
  NCheckboxGroup,
  NScrollbar,
  NSelect,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import IconPicker from '@/components/icon/IconPicker.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import api from '@/api'

defineOptions({ name: '菜单管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

// 表单初始化内容
const initForm = {
  order: 1,
  keepalive: true,
}

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleAdd,
  handleDelete,
  handleEdit,
  handleSave,
  modalForm,
  modalFormRef,
} = useCRUD({
  name: '菜单',
  initForm,
  doCreate: api.createMenu,
  doDelete: api.deleteMenu,
  doUpdate: api.updateMenu,
  refresh: () => $table.value?.handleSearch(),
})

// API映射相关
const apiDrawerVisible = ref(false)
const currentMenuId = ref(0)
const currentMenuName = ref('')
const allApisRaw = ref([])  // 原始API列表
const selectedApiIds = ref([])
const searchKeyword = ref('')

// 按标签分组的API
const apisByTag = computed(() => {
  const grouped = {}
  allApisRaw.value.forEach(item => {
    const tag = item.tags || '其他'
    if (!grouped[tag]) {
      grouped[tag] = []
    }
    grouped[tag].push(item)
  })
  return grouped
})

// 过滤后的分组API
const filteredApisByTag = computed(() => {
  if (!searchKeyword.value) {
    return apisByTag.value
  }
  const keyword = searchKeyword.value.toLowerCase()
  const filtered = {}
  Object.entries(apisByTag.value).forEach(([tag, apis]) => {
    const matchedApis = apis.filter(api => 
      api.path.toLowerCase().includes(keyword) ||
      api.method.toLowerCase().includes(keyword) ||
      (api.summary && api.summary.toLowerCase().includes(keyword))
    )
    if (matchedApis.length > 0) {
      filtered[tag] = matchedApis
    }
  })
  return filtered
})

// 标签排序
const sortedTags = computed(() => {
  return Object.keys(filteredApisByTag.value).sort()
})

onMounted(() => {
  $table.value?.handleSearch()
  getTreeSelect()
})

// 是否展示 "菜单类型"
const showMenuType = ref(false)
const menuOptions = ref([])

const columns = [
  { title: 'ID', key: 'id', width: 50, ellipsis: { tooltip: true }, align: 'center' },
  { title: '菜单名称', key: 'name', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  {
    title: '菜单类型',
    key: 'menu_type',
    width: 80,
    align: 'center',
    ellipsis: { tooltip: true },
    render(row) {
      let round = false
      let bordered = false
      if (row.menu_type === 'catalog') {
        bordered = true
        round = false
      } else if (row.menu_type === 'menu') {
        bordered = false
        round = true
      }
      return h(
        NTag,
        { type: 'primary', round: round, bordered: bordered },
        { default: () => (row.menu_type === 'catalog' ? '目录' : '菜单') }
      )
    },
  },
  {
    title: '图标',
    key: 'icon',
    width: 40,
    align: 'center',
    render(row) {
      return h(TheIcon, { icon: row.icon, size: 20 })
    },
  },
  { title: '排序', key: 'order', width: 40, ellipsis: { tooltip: true }, align: 'center' },
  { title: '访问路径', key: 'path', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  { title: '跳转路径', key: 'redirect', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  { title: '组件路径', key: 'component', width: 80, ellipsis: { tooltip: true }, align: 'center' },
  {
    title: '保活',
    key: 'keepalive',
    width: 40,
    align: 'center',
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.keepalive,
        onUpdateValue: () => handleUpdateKeepalive(row),
      })
    },
  },
  {
    title: '隐藏',
    key: 'is_hidden',
    width: 40,
    align: 'center',
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.is_hidden,
        onUpdateValue: () => handleUpdateHidden(row),
      })
    },
  },
  {
    title: '创建日期',
    key: 'created_at',
    width: 80,
    align: 'center',
    render(row) {
      return h('span', formatDate(row.created_at))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'primary',
              style: `display: ${row.children && row.menu_type !== 'menu' ? '' : 'none'};`,
              onClick: () => {
                initForm.parent_id = row.id
                initForm.menu_type = 'menu'
                showMenuType.value = false
                handleAdd()
              },
            },
            { default: () => '子菜单', icon: renderIcon('material-symbols:add', { size: 16 }) }
          ),
          [[vPermission, 'post/api/v1/menu/create']]
        ),
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'info',
              onClick: () => {
                showMenuType.value = false
                handleEdit(row)
              },
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/menu/update']]
        ),
        // API映射按钮（仅菜单类型显示）
        withDirectives(
          h(
            NButton,
            {
              size: 'tiny',
              quaternary: true,
              type: 'warning',
              style: `display: ${row.menu_type === 'menu' ? '' : 'none'};`,
              onClick: () => openApiDrawer(row),
            },
            {
              default: () => 'API',
              icon: renderIcon('material-symbols:api', { size: 16 }),
            }
          ),
          [[vPermission, 'get/api/v1/menu/api/list']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ id: row.id }, false),
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'tiny',
                    quaternary: true,
                    type: 'error',
                    style: `display: ${row.children && row.children.length > 0 ? 'none' : ''};`, //有子菜单不允许删除
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/menu/delete']]
              ),
            default: () => h('div', {}, '确定删除该菜单吗?'),
          }
        ),
      ]
    },
  },
]
// 修改是否keepalive
async function handleUpdateKeepalive(row) {
  if (!row.id) return
  row.publishing = true
  row.keepalive = row.keepalive === false ? true : false
  await api.updateMenu(row)
  row.publishing = false
  $message?.success(row.keepalive ? '已开启' : '已关闭')
}

// 修改是否隐藏
async function handleUpdateHidden(row) {
  if (!row.id) return
  row.publishing = true
  row.is_hidden = row.is_hidden === false ? true : false
  await api.updateMenu(row)
  row.publishing = false
  $message?.success(row.is_hidden ? '已隐藏' : '已取消隐藏')
}

// 新增菜单(可选目录)
function handleClickAdd() {
  initForm.parent_id = 0
  initForm.menu_type = 'catalog'
  initForm.is_hidden = false
  initForm.order = 1
  initForm.keepalive = true
  showMenuType.value = true
  handleAdd()
}

async function getTreeSelect() {
  const { data } = await api.getMenus()
  const menu = { id: 0, name: '根目录', children: [] }
  menu.children = data
  menuOptions.value = [menu]
}

// 打开API映射抽屉
async function openApiDrawer(row) {
  currentMenuId.value = row.id
  currentMenuName.value = row.name
  searchKeyword.value = ''
  
  // 获取所有可用API
  const apisRes = await api.getAvailableApis({ page: 1, page_size: 9999 })
  allApisRaw.value = apisRes.data
  
  // 获取当前菜单已关联的API
  const menuApisRes = await api.getMenuApis({ menu_id: row.id })
  selectedApiIds.value = menuApisRes.data.map(item => item.id)
  
  apiDrawerVisible.value = true
}

// 保存API映射
async function saveMenuApis() {
  const { code, msg } = await api.updateMenuApis({
    menu_id: currentMenuId.value,
    api_ids: selectedApiIds.value,
  })
  if (code === 200) {
    $message?.success('保存成功')
    apiDrawerVisible.value = false
  } else {
    $message?.error(msg || '保存失败')
  }
}

// 刷新菜单-API关系
// 刷新模式选项
const refreshModeOptions = [
  {
    label: '增量更新（推荐）',
    value: 'increment',
    description: '只新增不删除，保留所有手动配置'
  },
  {
    label: '智能更新',
    value: 'smart',
    description: '识别多菜单共用API并保留，更新其他关联'
  },
  {
    label: '完全刷新',
    value: 'full',
    description: '删除所有关联后重新创建（会丢失手动配置）'
  },
]

const selectedRefreshMode = ref('increment')

async function handleRefreshMenuApi() {
  selectedRefreshMode.value = 'increment' // 重置为默认值
  
  await $dialog.confirm({
    title: '刷新菜单-API关系',
    type: 'warning',
    content: () => h('div', {}, [
      h('p', { style: 'margin-bottom: 12px;' }, '此操作会根据代码中的路由信息自动刷新菜单-API关系表。'),
      h('p', { style: 'margin-bottom: 12px; font-weight: bold;' }, '请选择刷新模式：'),
      h(NSelect, {
        value: selectedRefreshMode.value,
        'onUpdate:value': (val) => { selectedRefreshMode.value = val },
        options: refreshModeOptions,
        placeholder: '请选择刷新模式',
      }),
      h('div', { style: 'margin-top: 12px; padding: 8px; background: #f5f5f5; border-radius: 4px;' }, [
        h('p', { style: 'font-size: 12px; color: #666;' }, '模式说明：'),
        h('p', { style: 'font-size: 12px; color: #666; margin-top: 4px;' }, '• 增量更新：只新增不删除，保留所有手动配置'),
        h('p', { style: 'font-size: 12px; color: #666; margin-top: 4px;' }, '• 智能更新：识别多菜单共用API并保留'),
        h('p', { style: 'font-size: 12px; color: #666; margin-top: 4px;' }, '• 完全刷新：删除所有关联后重建（慎用）'),
      ]),
    ]),
    positiveText: '确定',
    negativeText: '取消',
    async onPositiveClick() {
      const { code, msg } = await api.refreshMenuApiRelations(selectedRefreshMode.value)
      if (code === 200) {
        $message?.info(msg || '刷新任务已启动')
        pollRefreshStatus()
      } else {
        $message?.error(msg || '启动失败')
      }
    },
  })
}

// 轮询查询刷新状态
async function pollRefreshStatus() {
  const checkStatus = async () => {
    const { code, data } = await api.getRefreshMenuApiStatus()
    if (code === 200) {
      if (data.running) {
        // 仍在执行，1秒后继续查询
        setTimeout(checkStatus, 1000)
      } else {
        // 执行完成，显示结果
        if (data.result) {
          $message?.success(data.result)
          $table.value?.handleSearch()
        }
      }
    }
  }
  checkStatus()
}

// 获取方法对应的颜色
function getMethodColor(method) {
  const colors = {
    GET: 'success',
    POST: 'info',
    PUT: 'warning',
    DELETE: 'error',
    PATCH: 'warning',
  }
  return colors[method] || 'default'
}
</script>

<template>
  <!-- 业务页面 -->
  <CommonPage show-footer>
    <template #action>
      <div>
        <NButton
          v-permission="'post/api/v1/menu/create'"
          class="float-right mr-15"
          type="primary"
          @click="handleClickAdd"
        >
          <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建根菜单
        </NButton>
        <NButton
          v-permission="'post/api/v1/menu/api/refresh'"
          class="float-right mr-15"
          type="warning"
          @click="handleRefreshMenuApi"
        >
          <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />刷新API关系
        </NButton>
      </div>
    </template>

    <!-- 表格 -->
    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :is-pagination="false"
      :columns="columns"
      :get-data="api.getMenus"
      :single-line="true"
    >
    </CrudTable>

    <!-- 新增/编辑/查看 弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave(getTreeSelect)"
    >
      <!-- 表单 -->
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
      >
        <NFormItem label="菜单类型" path="menu_type">
          <NRadioGroup v-model:value="modalForm.menu_type">
            <NRadio label="目录" value="catalog" />
            <NRadio label="菜单" value="menu" />
          </NRadioGroup>
        </NFormItem>
        <NFormItem label="上级菜单" path="parent_id">
          <NTreeSelect
            v-model:value="modalForm.parent_id"
            key-field="id"
            label-field="name"
            :options="menuOptions"
            default-expand-all="true"
          />
        </NFormItem>
        <NFormItem
          label="菜单名称"
          path="name"
          :rule="{
            required: true,
            message: '请输入唯一菜单名称',
            trigger: ['input', 'blur'],
          }"
        >
          <NInput v-model:value="modalForm.name" placeholder="请输入唯一菜单名称" />
        </NFormItem>
        <NFormItem
          label="访问路径"
          path="path"
          :rule="{
            required: true,
            message: '请输入访问路径',
            trigger: ['blur'],
          }"
        >
          <NInput v-model:value="modalForm.path" placeholder="请输入访问路径" />
        </NFormItem>
        <NFormItem v-if="modalForm.menu_type === 'menu'" label="组件路径" path="component">
          <NInput
            v-model:value="modalForm.component"
            placeholder="请输入组件路径，例如：/system/user"
          />
        </NFormItem>
        <NFormItem label="跳转路径" path="redirect">
          <NInput
            v-model:value="modalForm.redirect"
            :disabled="modalForm.parent_id !== 0"
            :placeholder="
              modalForm.parent_id !== 0 ? '只有一级菜单可以设置跳转路径' : '请输入跳转路径'
            "
          />
        </NFormItem>
        <NFormItem label="菜单图标" path="icon">
          <IconPicker v-model:value="modalForm.icon" />
        </NFormItem>
        <NFormItem label="显示排序" path="order">
          <NInputNumber v-model:value="modalForm.order" :min="1" />
        </NFormItem>
        <NFormItem label="是否隐藏" path="is_hidden">
          <NSwitch v-model:value="modalForm.is_hidden" />
        </NFormItem>
        <NFormItem label="KeepAlive" path="keepalive">
          <NSwitch v-model:value="modalForm.keepalive" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- API映射抽屉 -->
    <NDrawer v-model:show="apiDrawerVisible" placement="right" :width="900">
      <NDrawerContent title="设置菜单关联API">
        <div class="mb-4 flex items-center gap-4">
          <NTag type="info" size="large">菜单：{{ currentMenuName }}</NTag>
          <NInput
            v-model:value="searchKeyword"
            placeholder="搜索API路径、方法或描述"
            clearable
            style="width: 300px"
          />
          <NTag type="success">已选 {{ selectedApiIds.length }} 个API</NTag>
        </div>
        <div class="mb-4 text-gray-500">
          提示：选择此菜单关联的API接口，拥有此菜单权限的角色将自动获得这些API的访问权限
        </div>
        
        <!-- 按标签分组的API列表 -->
        <NScrollbar style="max-height: calc(100vh - 280px)">
          <NCollapse :default-expanded-names="sortedTags">
            <NCollapseItem
              v-for="tag in sortedTags"
              :key="tag"
              :name="tag"
            >
              <template #header>
                <div class="flex items-center gap-2" @click.stop>
                  <NCheckbox
                    :checked="filteredApisByTag[tag].every(api => selectedApiIds.includes(api.id))"
                    :indeterminate="filteredApisByTag[tag].some(api => selectedApiIds.includes(api.id)) && !filteredApisByTag[tag].every(api => selectedApiIds.includes(api.id))"
                    @update:checked="(checked) => {
                      if (checked) {
                        filteredApisByTag[tag].forEach(api => {
                          if (!selectedApiIds.includes(api.id)) {
                            selectedApiIds.push(api.id)
                          }
                        })
                      } else {
                        filteredApisByTag[tag].forEach(api => {
                          const index = selectedApiIds.indexOf(api.id)
                          if (index > -1) selectedApiIds.splice(index, 1)
                        })
                      }
                    }"
                  />
                  <span class="text-[17px] font-semibold">{{ tag }} ({{ filteredApisByTag[tag].length }})</span>
                </div>
              </template>
              <div class="grid grid-cols-2 gap-3">
                <NCheckbox
                  v-for="apiItem in filteredApisByTag[tag]"
                  :key="apiItem.id"
                  :value="apiItem.id"
                  :checked="selectedApiIds.includes(apiItem.id)"
                  @update:checked="(checked) => {
                    if (checked) {
                      selectedApiIds.push(apiItem.id)
                    } else {
                      const index = selectedApiIds.indexOf(apiItem.id)
                      if (index > -1) selectedApiIds.splice(index, 1)
                    }
                  }"
                >
                  <div class="flex items-center gap-2 py-1">
                    <NTag :type="getMethodColor(apiItem.method)" size="small" round>
                      {{ apiItem.method }}
                    </NTag>
                    <span class="text-[15px]">{{ apiItem.path }}</span>
                  </div>
                  <div v-if="apiItem.summary" class="text-[13px] text-gray-400 mt-1 ml-6">
                    {{ apiItem.summary }}
                  </div>
                </NCheckbox>
              </div>
            </NCollapseItem>
          </NCollapse>
        </NScrollbar>
        
        <template #footer>
          <div class="flex justify-between">
            <div>
              <NButton 
                size="small" 
                @click="() => {
                  const allIds = allApisRaw.map(a => a.id)
                  selectedApiIds = [...allIds]
                }"
              >
                全选
              </NButton>
              <NButton 
                size="small" 
                @click="selectedApiIds = []"
                class="ml-2"
              >
                清空
              </NButton>
            </div>
            <div>
              <NButton type="primary" @click="saveMenuApis">保存</NButton>
              <NButton @click="apiDrawerVisible = false" class="ml-2">取消</NButton>
            </div>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>
  </CommonPage>
</template>
