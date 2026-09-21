<template>
  <n-drawer v-model:show="visible" :width="400" placement="right">
    <n-drawer-content title="AI 智能运维助手" closable>
      <div class="h-full flex flex-col">
        <!-- 快捷提问 -->
        <n-space size="small" class="px-4 pt-2" wrap>
          <n-button
            v-for="item in quickQuestions"
            :key="item"
            size="small"
            quaternary
            type="primary"
            @click="sendQuick(item)"
          >
            {{ item }}
          </n-button>
        </n-space>

        <!-- 聊天记录区域 -->
        <div ref="messageListRef" class="flex-1 overflow-y-auto p-4 space-y-4">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] rounded-[8px] p-[12px]"
              :class="
                msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-tr-none'
                  : 'bg-gray-100 text-gray-800 rounded-tl-none dark:bg-gray-800 dark:text-gray-200'
              "
            >
              <div
                v-if="msg.role === 'assistant'"
                class="whitespace-pre-wrap text-[14px] leading-[1.6] font-sans"
                v-html="formatMessage(msg.content)"
              ></div>
              <div v-else class="whitespace-pre-wrap text-[14px] leading-[1.6]">
                {{ msg.content }}
              </div>
            </div>
          </div>

          <div v-if="isTyping" class="flex justify-start">
            <div class="rounded-[8px] rounded-tl-none bg-gray-100 p-[12px] dark:bg-gray-800">
              <span class="animate-pulse text-[14px]">思考中...</span>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="border-t pt-4 dark:border-gray-700">
          <n-input-group>
            <n-input
              ref="inputRef"
              v-model:value="inputValue"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="请输入问题或运维指令 (Shift+Enter换行)"
              @keydown="handleEnter"
            />
            <n-button
              type="primary"
              :disabled="isTyping || !inputValue.trim()"
              @click="sendMessage"
            >
              发送
            </n-button>
          </n-input-group>
        </div>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { NDrawer, NDrawerContent, NInput, NInputGroup, NSpace } from 'naive-ui'
import { marked } from 'marked'
import { getToken } from '@/utils'

const visible = ref(false)
const inputValue = ref('')
const messages = ref([
  {
    role: 'assistant',
    content:
      '您好！我是您的智能运维助手。我可以帮您执行 SQL 查询、调整 Token 配额、审核和执行订单仓储的软删除等操作。请问有什么可以帮您？',
  },
])
const isTyping = ref(false)
const messageListRef = ref(null)
const sessionId = ref(null)

const quickQuestions = ['最近任务执行情况如何', '哪些任务失败了', '帮我生成一份SQL备份方案']

const open = () => {
  visible.value = true
}

const close = () => {
  visible.value = false
}

defineExpose({ open, close })

const formatMessage = (text) => {
  try {
    return marked(text || '')
  } catch (e) {
    return text
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const handleEnter = (e) => {
  if (e.key !== 'Enter') return
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

const sendQuick = (text) => {
  inputValue.value = text
  sendMessage()
}

const sendMessage = async () => {
  const content = inputValue.value.trim()
  if (!content || isTyping.value) return

  messages.value.push({ role: 'user', content })
  inputValue.value = ''
  isTyping.value = true
  scrollToBottom()

  const assistantMsgIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

  try {
    // 项目 http 层使用 `token` header 传递用户 token，SSE 请求保持一致
    const baseUrl = import.meta.env.VITE_BASE_API || '/api/v1'
    const headers = { 'Content-Type': 'application/json' }
    const token = getToken()
    if (token) headers.token = token
    const response = await fetch(`${baseUrl}/ai/chat/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message: content,
        session_id: sessionId.value,
      }),
    })

    if (response.status === 401) {
      messages.value[assistantMsgIndex].content = '登录已过期，请重新登录后再试。'
      return
    }
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    isTyping.value = false

    let reading = true
    while (reading) {
      const { done, value } = await reader.read()
      reading = !done
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          if (dataStr === '[DONE]') {
            break
          }
          try {
            const data = JSON.parse(dataStr)
            if (data.session_id) {
              sessionId.value = data.session_id
            }
            if (data.text) {
              messages.value[assistantMsgIndex].content += data.text
              scrollToBottom()
            }
          } catch (e) {
            console.error('SSE parsing error', e, dataStr)
          }
        }
      }
    }
  } catch (error) {
    console.error('Chat error:', error)
    messages.value[assistantMsgIndex].content =
      error?.message === 'HTTP error! status: 401'
        ? '登录已过期，请重新登录后再试。'
        : '抱歉，服务出现异常。请稍后再试。'
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}
</script>
