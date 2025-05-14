<template>
  <div>
    <n-card title="按钮权限" :bordered="false">
      <n-space vertical>
        <n-table :bordered="false" size="small">
          <thead>
            <tr>
              <th>菜单</th>
              <th>按钮权限</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="menu in menuList" :key="menu.id">
              <tr>
                <td>{{ menu.name }}</td>
                <td>
                  <n-space>
                    <n-checkbox
                      v-for="button in menu.buttons"
                      :key="button.id"
                      :value="selectedButtons.includes(button.id)"
                      @update:value="(checked) => handleButtonCheck(button.id, checked)"
                    >
                      {{ button.name }}
                    </n-checkbox>
                  </n-space>
                </td>
              </tr>
            </template>
          </tbody>
        </n-table>
      </n-space>
    </n-card>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import buttonApi from '@/api/button'
import { useMessage } from 'naive-ui'

const props = defineProps({
  roleId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['update'])
const message = useMessage()

const menuList = ref([])
const selectedButtons = ref([])

// 加载菜单及其按钮
const loadMenuButtons = async () => {
  try {    // 获取所有按钮(按菜单分组)
    const { data } = await buttonApi.getButtonsMenuGroup()
    menuList.value = data
  } catch (error) {
    message.error('加载按钮权限失败')
    console.error('加载按钮权限失败:', error)
  }
}

// 加载角色已有的按钮权限
const loadRoleButtons = async () => {
  try {
    const { data } = await buttonApi.getRoleButtons(props.roleId)
    selectedButtons.value = data.map(button => button.id)
  } catch (error) {
    message.error('加载角色按钮权限失败')
  }
}

// 处理按钮选择
const handleButtonCheck = async (buttonId, checked) => {
  const newSelected = checked
    ? [...selectedButtons.value, buttonId]
    : selectedButtons.value.filter(id => id !== buttonId)
    
  try {
    // 设置角色按钮权限
    await buttonApi.setRoleButtons(props.roleId, newSelected)
    selectedButtons.value = newSelected
    emit('update')
    message.success('更新按钮权限成功')
  } catch (error) {
    console.error('更新按钮权限失败:', error)
    message.error('更新按钮权限失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 监听roleId变化
watch(() => props.roleId, () => {
  if (props.roleId) {
    loadRoleButtons()
  }
}, { immediate: true })

// 初始化加载
loadMenuButtons()
</script>
