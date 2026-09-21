<template>
  <AppPage :show-footer="false">
    <div flex-1>
      <!-- 欢迎语 + 操作 -->
      <n-card :bordered="false" mb-20>
        <n-space align="center" justify="space-between">
          <div>
            <n-text strong depth="3">
              {{ t('views.workbench.text_hello', { username: userStore.name || '-' }) }}
            </n-text>
            <n-text depth="3" class="mt-4 block">{{ t('views.workbench.text_welcome') }}</n-text>
          </div>
          <n-space>
            <n-button @click="handleRefresh">
              <TheIcon icon="material-symbols:refresh" :size="18" class="mr-5" />{{
                t('views.workbench.label_refresh')
              }}
            </n-button>
            <n-button type="primary" @click="handleOpenAiChat">
              <TheIcon icon="mdi:robot-excited-outline" :size="18" class="mr-5" />{{
                t('views.workbench.label_ai_assistant')
              }}
            </n-button>
          </n-space>
        </n-space>
      </n-card>

      <!-- 统计卡片 -->
      <n-grid :x-gap="16" :y-gap="16" cols="1 s:2 m:4" responsive="screen" mb-20>
        <n-grid-item v-for="card in statCards" :key="card.key">
          <n-card :bordered="false">
            <n-space align="center" justify="space-between">
              <div>
                <n-text depth="3">{{ card.label }}</n-text>
                <n-text strong class="mt-4 block text-28px" :style="{ color: card.color }">
                  {{ card.value }}
                </n-text>
                <n-text depth="3" class="mt-4 block text-12px">{{ card.sub }}</n-text>
              </div>
              <div
                class="flex-center h-56 w-56 rounded-16"
                :style="{ backgroundColor: card.color + '1a' }"
              >
                <TheIcon :icon="card.icon" :size="28" :color="card.color" />
              </div>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>

      <!-- 详情列表 -->
      <n-grid :x-gap="16" :y-gap="16" cols="1 m:2" responsive="screen">
        <!-- 最近任务日志 -->
        <n-grid-item>
          <n-card
            :bordered="false"
            :title="t('views.workbench.label_recent_task_logs')"
            size="small"
          >
            <template #header-extra>
              <n-button text type="primary" @click="router.push('/task')">
                {{ t('views.workbench.label_more') }}
              </n-button>
            </template>
            <n-table :bordered="true" size="small">
              <template #header>
                <tr>
                  <th>{{ t('views.workbench.label_task_name') }}</th>
                  <th>{{ t('views.workbench.label_task_status') }}</th>
                  <th>{{ t('views.workbench.label_task_start_time') }}</th>
                  <th>{{ t('views.workbench.label_task_duration') }}</th>
                </tr>
              </template>
              <template #default>
                <tr v-for="(log, i) in summary.recent_task_logs" :key="i">
                  <td>{{ log.task_name || log.task_id }}</td>
                  <td>
                    <n-tag
                      :type="
                        log.status === 'success'
                          ? 'success'
                          : log.status === 'running'
                          ? 'info'
                          : 'error'
                      "
                      size="small"
                    >
                      {{ taskStatusMap[log.status] || log.status }}
                    </n-tag>
                  </td>
                  <td>{{ log.start_time }}</td>
                  <td>{{ log.duration ?? '-' }}</td>
                </tr>
                <tr v-if="!summary.recent_task_logs.length">
                  <td colspan="4">
                    <n-empty
                      size="small"
                      :description="t('views.workbench.text_no_task_logs')"
                      class="my-20"
                    />
                  </td>
                </tr>
              </template>
            </n-table>
          </n-card>
        </n-grid-item>

        <!-- 最近告警发送 -->
        <n-grid-item>
          <n-card :bordered="false" :title="t('views.workbench.label_recent_alerts')" size="small">
            <template #header-extra>
              <n-button text type="primary" @click="router.push('/alert/log')">
                {{ t('views.workbench.label_more') }}
              </n-button>
            </template>
            <n-table :bordered="true" size="small">
              <template #header>
                <tr>
                  <th>{{ t('views.workbench.label_alert_sender') }}</th>
                  <th>{{ t('views.workbench.label_alert_channel') }}</th>
                  <th>{{ t('views.workbench.label_alert_status') }}</th>
                  <th>{{ t('views.workbench.label_alert_time') }}</th>
                </tr>
              </template>
              <template #default>
                <tr v-for="(log, i) in summary.recent_alert_logs" :key="i">
                  <td>{{ log.sender_name }}</td>
                  <td>{{ log.channel_type }}</td>
                  <td>
                    <n-tag :type="log.send_status ? 'success' : 'error'" size="small">
                      {{
                        log.send_status
                          ? t('views.workbench.text_alert_success')
                          : t('views.workbench.text_alert_failed')
                      }}
                    </n-tag>
                  </td>
                  <td>{{ log.sent_at }}</td>
                </tr>
                <tr v-if="!summary.recent_alert_logs.length">
                  <td colspan="4">
                    <n-empty
                      size="small"
                      :description="t('views.workbench.text_no_alert_logs')"
                      class="my-20"
                    />
                  </td>
                </tr>
              </template>
            </n-table>
          </n-card>
        </n-grid-item>
      </n-grid>
    </div>

    <!-- AI 助手抽屉（复用公共组件，供"AI 运维助手"按钮唤起） -->
    <AiChatDrawer ref="aiChatDrawerRef" />
  </AppPage>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { NCard, NEmpty, NGrid, NGridItem, NSpace, NTable, NTag, NText, useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppPage from '@/components/page/AppPage.vue'
import AiChatDrawer from '@/components/AiChat/AiChatDrawer.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import api from '@/api'
import { useUserStore } from '@/store'

defineOptions({ name: '工作台' })

const { t } = useI18n({ useScope: 'global' })
const message = useMessage()
const router = useRouter()
const userStore = useUserStore()
const aiChatDrawerRef = ref(null)

const summary = ref({
  counts: {},
  recent_task_logs: [],
  recent_alert_logs: [],
})

const statCards = computed(() => [
  {
    key: 'task',
    label: t('views.workbench.label_stat_task'),
    value: summary.value.counts?.task ?? 0,
    sub: `${t('views.workbench.label_stat_task_enabled')} ${
      summary.value.counts?.task_enabled ?? 0
    }`,
    icon: 'mdi:calendar-check-outline',
    color: '#33adff',
  },
  {
    key: 'task_log',
    label: t('views.workbench.label_stat_task_log'),
    value: summary.value.counts?.task_log ?? 0,
    sub: `${t('views.workbench.text_stat_task_log_failed')} ${
      summary.value.counts?.task_log_failed ?? 0
    } · ${t('views.workbench.text_stat_task_log_running')} ${
      summary.value.counts?.task_log_running ?? 0
    }`,
    icon: 'mdi:console-line',
    color: '#f40',
  },
  {
    key: 'alert',
    label: t('views.workbench.label_stat_alert'),
    value: summary.value.counts?.alert_log ?? 0,
    sub: `${t('views.workbench.text_stat_alert_failed')} ${
      summary.value.counts?.alert_log_failed ?? 0
    }`,
    icon: 'mdi:bell-alert-outline',
    color: '#d03050',
  },
  {
    key: 'report',
    label: t('views.workbench.label_stat_report'),
    value: summary.value.counts?.report_generation ?? 0,
    sub: `${t('views.workbench.text_stat_sql_alert_task')} ${
      summary.value.counts?.sql_alert_task ?? 0
    }`,
    icon: 'mdi:file-chart-outline',
    color: '#18cc8c',
  },
])

const taskStatusMap = {
  success: t('views.workbench.text_task_status_success'),
  failed: t('views.workbench.text_task_status_failed'),
  timeout: t('views.workbench.text_task_status_timeout'),
  running: t('views.workbench.text_task_status_running'),
}

const loadSummary = async () => {
  try {
    const res = await api.getWorkbenchSummary()
    summary.value = res.data || { counts: {}, recent_task_logs: [], recent_alert_logs: [] }
  } catch (e) {
    message.error(t('views.workbench.message_load_failed'))
  }
}

const handleRefresh = () => loadSummary()
const handleOpenAiChat = () => aiChatDrawerRef.value?.open()

onMounted(loadSummary)
</script>
