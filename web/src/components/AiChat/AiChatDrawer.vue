<template>
  <n-drawer v-model:show="visible" :width="400" placement="right">
    <n-drawer-content title="AI 智能运维助手" closable>
      <div class="flex flex-col h-full">
        <!-- 聊天记录区域 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="messageListRef">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] rounded-lg p-3"
              :class="
                msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-tr-none'
                  : 'bg-gray-100 text-gray-800 rounded-tl-none dark:bg-gray-800 dark:text-gray-200'
              "
            >
              <div v-if="msg.role === 'assistant'" class="text-sm whitespace-pre-wrap leading-relaxed font-sans" v-html="formatMessage(msg.content)"></div>
              <div v-else class="text-sm whitespace-pre-wrap">{{ msg.content }}</div>
            </div>
          </div>
          
          <div v-if="isTyping" class="flex justify-start">
            <div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 rounded-tl-none">
              <span class="animate-pulse">思考中...</span>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="pt-4 border-t dark:border-gray-700">
          <n-input-group>
            <n-input
              v-model:value="inputValue"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="请输入问题或运维指令 (Shift+Enter换行)"
              @keydown.enter="handleEnter"
            />
            <n-button type="primary" :disabled="isTyping || !inputValue.trim()" @click="sendMessage">
              发送
            </n-button>
          </n-input-group>
        </div>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { NDrawer, NDrawerContent, NInputGroup, NInput, NButton, useMessage } from 'naive-ui'
import { marked } from 'marked' // 需要安装 marked，如果没有则用简单文本，dbadmin 应该有

const message = useMessage()
const visible = ref(false)
const inputValue = ref('')
const messages = ref([
  { role: 'assistant', content: '您好！我是您的智能运维助手。我可以帮您执行 SQL 查询、调整 Token 配额、审核和执行订单仓储的软删除等操作。请问有什么可以帮您？' }
])
const isTyping = ref(false)
const messageListRef = ref(null)
const sessionId = ref(null)

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
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

const sendMessage = async () => {
  const content = inputValue.value.trim()
  if (!content) return

  messages.value.push({ role: 'user', content })
  inputValue.value = ''
  isTyping.value = true
  scrollToBottom()

  const assistantMsgIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })

  try {
    // 假设 VITE_BASE_API 为 /api/v1，我们的路由是 /api/v1/ai/chat/
    const baseUrl = import.meta.env.VITE_BASE_API || '/api/v1'
    const response = await fetch(`${baseUrl}/ai/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
        // token 如果在 localStorage 可以加上: 'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        message: content,
        session_id: sessionId.value
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    isTyping.value = false

    while (true) {
      const { done, value } = await reader.read()
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
    message.error('发送失败: ' + error.message)
    messages.value[assistantMsgIndex].content = '抱歉，服务出现异常。请稍后再试。'
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}
</script>
