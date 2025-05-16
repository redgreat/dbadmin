<template>
  <AppPage :show-footer="false">
    <div flex-1>
      <!-- Content will be added later -->
    </div>
  </AppPage>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>
