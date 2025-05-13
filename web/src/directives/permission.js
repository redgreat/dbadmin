import { useUserStore, usePermissionStore } from '@/store'
import buttonApi from '@/api/button'

async function hasPermission(permission) {
  const userStore = useUserStore()
  const userPermissionStore = usePermissionStore()

  // 超级管理员拥有所有权限
  if (userStore.isSuperUser) {
    return true
  }

  // 检查API权限
  if (typeof permission === 'string') {
    const accessApis = userPermissionStore.apis
    return accessApis.includes(permission)
  }
  
  // 检查按钮权限
  if (permission.menuId && permission.code) {
    try {
      const { data: hasButtonPermission } = await buttonApi.checkButtonPermission(
        permission.menuId,
        permission.code
      )
      return hasButtonPermission
    } catch (error) {
      console.error('Failed to check button permission:', error)
      return false
    }
  }

  return false
}

export default function setupPermissionDirective(app) {
  async function updateElVisible(el, permission) {
    if (!permission) {
      throw new Error(`need permission: like v-permission="'get/api/v1/user/list'" or v-permission="{ menuId: 1, code: 'add' }"`)
    }
    if (!await hasPermission(permission)) {
      el.parentElement?.removeChild(el)
    }
  }

  const permissionDirective = {
    mounted(el, binding) {
      updateElVisible(el, binding.value)
    },
    beforeUpdate(el, binding) {
      updateElVisible(el, binding.value)
    },
  }

  app.directive('permission', permissionDirective)
}
