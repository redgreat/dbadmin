<template>
  <n-dropdown :options="options" @select="handleSelect">
    <div flex cursor-pointer items-center>
      <div class="flex items-center">
        <TheIcon icon="material-symbols:account-circle" :size="24" />
      </div>    </div>
  </n-dropdown>

  <!-- 修改密码模态框 -->
  <n-modal v-model:show="showPasswordModal">
    <n-card
      :title="t('header.label_change_password')"
      :bordered="false"
      size="huge"
      role="dialog"
      aria-modal="true"
      style="width: 400px"
    >      <n-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-placement="left"
        label-align="left"
        :label-width="100"
      >
        <n-form-item :label="t('views.profile.label_old_password')" path="old_password">
          <n-input
            v-model:value="passwordForm.old_password"
            type="password"
            :placeholder="t('views.profile.enter_old_password')"
            @keydown.enter.prevent
          />
        </n-form-item>
        <n-form-item :label="t('views.profile.label_new_password')" path="new_password">
          <n-input
            v-model:value="passwordForm.new_password"
            type="password"
            :placeholder="t('views.profile.enter_new_password')"
            @keydown.enter.prevent
          />
        </n-form-item>
        <n-form-item :label="t('views.profile.label_confirm_password')" path="confirm_password">
          <n-input
            v-model:value="passwordForm.confirm_password"
            type="password"
            :placeholder="t('views.profile.enter_confirm_password')"
            @keydown.enter.prevent
          />
        </n-form-item>
      </n-form>      <template #footer>
        <div flex justify-end gap-2>
          <n-button @click="showPasswordModal = false">{{ t('common.buttons.cancel') }}</n-button>
          <n-button type="primary" @click="handlePasswordSubmit">
            {{ t('common.buttons.confirm') }}
          </n-button>
        </div>
      </template>
    </n-card>
  </n-modal>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/store'
import { renderIcon } from '@/utils'
import { useDialog, useMessage, NModal, NCard, NForm, NFormItem, NInput } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import TheIcon from '@/components/icon/TheIcon.vue'
import api from '@/api'

const { t } = useI18n()

const userStore = useUserStore()
const $dialog = useDialog()
const $message = useMessage()

const showPasswordModal = ref(false)
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const passwordFormRef = ref(null)

const passwordRules = {
  old_password: {
    required: true,
    message: t('views.profile.old_password_required'),
    trigger: ['blur', 'input'],
  },
  new_password: {
    required: true,
    message: t('views.profile.new_password_required'),
    trigger: ['blur', 'input'],
  },
  confirm_password: {
    required: true,
    message: t('views.profile.confirm_password_required'),
    validator: (rule, value) => {
      if (!value) return false
      return value === passwordForm.value.new_password
    },
    trigger: ['blur', 'input'],
  },
}

const options = [
  {
    label: t('header.label_change_password'),
    key: 'change_password',
    icon: renderIcon('material-symbols:key-outline', { size: '14px' }),
  },
  {
    label: t('header.label_logout'),
    key: 'logout',
    icon: renderIcon('mdi:exit-to-app', { size: '14px' }),
  },
]

async function handlePasswordSubmit() {
  await passwordFormRef.value?.validate()
  try {    await api.updatePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    })
    $message.success(t('views.profile.password_updated'))
    showPasswordModal.value = false
    passwordForm.value = {
      old_password: '',
      new_password: '',
      confirm_password: '',
    }
  } catch (error) {
    $message.error(error.response?.data?.detail || t('views.profile.update_password_failed'))
  }
}

function handleSelect(key) {
  if (key === 'change_password') {
    showPasswordModal.value = true
  } else if (key === 'logout') {
    $dialog.confirm({
      title: t('header.label_logout_dialog_title'),
      type: 'warning',
      content: t('header.text_logout_confirm'),
      confirm() {
        userStore.logout()
        $message.success(t('header.text_logout_success'))
      },
    })
  }
}
</script>
