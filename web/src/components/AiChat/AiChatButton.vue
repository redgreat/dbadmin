<template>
  <div class="fixed bottom-10 right-10 z-50">
    <div
      class="group relative flex h-[56px] w-[56px] cursor-pointer items-center justify-center rounded-full bg-blue-600 text-white shadow-lg shadow-blue-500/30 transition-all hover:scale-110 active:scale-95"
      @click="toggleChat"
    >
      <TheIcon icon="mdi:robot-excited-outline" :size="28" class="transition-transform group-hover:rotate-12" />
      <!-- 提示冒泡 -->
      <div class="pointer-events-none absolute -top-[48px] right-0 w-[130px] origin-bottom-right scale-0 rounded-lg bg-gray-800 px-[12px] py-[8px] text-center text-[12px] text-white opacity-0 transition-all group-hover:scale-100 group-hover:opacity-100 dark:bg-gray-100 dark:text-gray-800">
        AI 智能运维助手
        <!-- 小三角 -->
        <div class="absolute -bottom-1 right-5 h-2 w-2 rotate-45 bg-gray-800 dark:bg-gray-100"></div>
      </div>
    </div>

    <!-- 挂载聊天抽屉 -->
    <AiChatDrawer ref="drawerRef" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import AiChatDrawer from './AiChatDrawer.vue'

const drawerRef = ref(null)

const toggleChat = () => {
  if (drawerRef.value) {
    // 假设 AiChatDrawer 内部维护了 visible 状态，如果是对外暴露了 open 方法
    drawerRef.value.open()
  }
}
</script>
