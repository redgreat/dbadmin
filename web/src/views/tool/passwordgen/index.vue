<template>
  <CommonPage show-footer>
    <div class="passwordgen-container">
      <n-card title="密码生成选项" class="options-card" :bordered="false">
        <n-form :model="options" label-placement="left" :label-width="100">
          <n-form-item label="所用字符">
            <n-space>
              <n-checkbox v-model:checked="options.lowercase">
                a-z
              </n-checkbox>
              <n-checkbox v-model:checked="options.uppercase">
                A-Z
              </n-checkbox>
              <n-checkbox v-model:checked="options.digits">
                0-9
              </n-checkbox>
              <n-checkbox v-model:checked="options.specials">
                !@#$%^&amp;*()_+-=[]{}|;:,.
              </n-checkbox>
            </n-space>
          </n-form-item>

          <n-form-item label="排除字符">
            <n-input
              v-model:value="options.excludeChars"
              placeholder="输入需要排除的字符，如 il1o0O"
              clearable
              style="max-width: 400px"
            />
          </n-form-item>

          <n-form-item label="密码长度">
            <n-space align="center" style="width: 100%">
              <n-slider
                v-model:value="options.length"
                :min="4"
                :max="64"
                :step="1"
                style="flex: 1; max-width: 300px"
              />
              <n-input-number
                v-model:value="options.length"
                :min="4"
                :max="64"
                :step="1"
                style="width: 100px"
              >
                <template #suffix>位</template>
              </n-input-number>
            </n-space>
          </n-form-item>

          <n-form-item label="密码数量">
            <n-space align="center">
              <n-input-number
                v-model:value="options.count"
                :min="1"
                :max="100"
                :step="1"
                style="width: 100px"
              >
                <template #suffix>个</template>
              </n-input-number>
            </n-space>
          </n-form-item>

          <n-form-item label=" ">
            <n-space>
              <n-checkbox v-model:checked="recordHistory">
                记录历史记录
              </n-checkbox>
            </n-space>
          </n-form-item>

          <n-form-item label=" ">
            <n-space class="action-buttons">
              <n-button type="primary" size="medium" @click="handleGenerate">
                <template #icon>
                  <TheIcon icon="material-symbols:key" :size="18" />
                </template>
                生成密码
              </n-button>
              <n-button size="medium" @click="handleClearResult">
                <template #icon>
                  <TheIcon icon="material-symbols:clear-all" :size="18" />
                </template>
                清空
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>

      <n-card v-if="passwords.length > 0" title="生成结果" class="result-card" :bordered="false">
        <template #header-extra>
          <n-button type="primary" size="small" @click="handleCopyAll">
            <template #icon>
              <TheIcon icon="material-symbols:content-copy" :size="16" />
            </template>
            复制全部
          </n-button>
        </template>
        <div class="password-list">
          <div
            v-for="(pwd, idx) in passwords"
            :key="idx"
            class="password-item"
          >
            <span class="password-index">{{ idx + 1 }}.</span>
            <n-input
              :value="pwd.value"
              readonly
              class="password-input"
              :style="{ fontFamily: 'Consolas, Monaco, monospace' }"
            />
            <n-tag type="info" size="small" class="crack-time-tag">
              {{ pwd.crackTime }}
            </n-tag>
            <n-button size="tiny" @click="handleCopyOne(pwd.value)">
              <template #icon>
                <TheIcon icon="material-symbols:content-copy" :size="14" />
              </template>
            </n-button>
          </div>
        </div>
      </n-card>

      <n-card title="历史记录" class="history-card" :bordered="false">
        <template #header-extra>
          <n-space>
            <n-button
              size="small"
              type="info"
              :loading="historyLoading"
              @click="handleToggleHistory"
            >
              {{ showHistory ? '隐藏历史记录' : '查看历史记录' }}
            </n-button>
            <n-popconfirm @positive-click="handleClearHistory">
              <template #trigger>
                <n-button size="small" type="error" :disabled="historyTotal === 0">
                  清空历史
                </n-button>
              </template>
              确定要清空所有历史记录吗？
            </n-popconfirm>
          </n-space>
        </template>

        <div v-if="showHistory">
          <n-data-table
            v-if="historyData.length > 0"
            :columns="historyColumns"
            :data="historyData"
            :bordered="false"
            :single-line="false"
            size="small"
          />

          <n-empty v-else description="暂无历史记录" class="empty-state" />

          <n-pagination
            v-if="historyTotal > historyPageSize"
            v-model:page="historyPage"
            :page-size="historyPageSize"
            :item-count="historyTotal"
            :page-slot="7"
            class="history-pagination"
            @update:page="fetchHistory"
          />
        </div>
      </n-card>

      <n-alert type="info" class="usage-guide" :bordered="false">
        <template #icon>
          <TheIcon icon="material-symbols:info-outline" :size="20" />
        </template>
        <div class="guide-content">
          <div class="guide-title">使用说明</div>
          <ul class="guide-list">
            <li>选择需要的字符类型（至少选一种），设置密码长度和数量</li>
            <li>可在"排除字符"中排除容易混淆的字符（如 1、l、0、O 等）</li>
            <li>密码在前端本地生成，确保安全性</li>
            <li>勾选"记录历史记录"可将生成的密码保存到服务器</li>
            <li>破解耗时根据当前选用字符集大小和密码长度估算（假设攻击速度 10^9 次/秒）</li>
          </ul>
        </div>
      </n-alert>
    </div>
  </CommonPage>
</template>

<script setup>
import { ref, h } from 'vue'
import { useMessage, NButton, NPopconfirm } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import api from '@/api'

defineOptions({ name: '密码生成器' })

const message = useMessage()

const options = ref({
  lowercase: true,
  uppercase: true,
  digits: true,
  specials: false,
  excludeChars: '',
  length: 16,
  count: 1,
})

const recordHistory = ref(true)
const passwords = ref([])
const showHistory = ref(false)
const historyData = ref([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyTotal = ref(0)

const CHAR_SETS = {
  lowercase: 'abcdefghijklmnopqrstuvwxyz',
  uppercase: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  digits: '0123456789',
  specials: '!@#$%^&*()_+-=[]{}|;:,.<>?',
}

function getEffectiveCharSet() {
  let chars = ''
  if (options.value.lowercase) chars += CHAR_SETS.lowercase
  if (options.value.uppercase) chars += CHAR_SETS.uppercase
  if (options.value.digits) chars += CHAR_SETS.digits
  if (options.value.specials) chars += CHAR_SETS.specials

  const excludeSet = new Set(options.value.excludeChars.split(''))
  chars = [...chars].filter(c => !excludeSet.has(c)).join('')

  if (chars.length === 0) {
    message.error('请至少选择一种字符类型，并确保排除字符后仍有可用字符')
  }

  return chars
}

function estimateCrackTime(charSetSize, length) {
  const guessesPerSecond = 1e9
  const entropy = Math.pow(charSetSize, length)
  const seconds = entropy / guessesPerSecond

  if (seconds < 60) return { seconds, text: `${Math.round(seconds)} 秒` }
  if (seconds < 3600) return { seconds, text: `${Math.round(seconds / 60)} 分钟` }
  if (seconds < 86400) return { seconds, text: `${Math.round(seconds / 3600)} 小时` }
  if (seconds < 31536000) return { seconds, text: `${Math.round(seconds / 86400)} 天` }
  if (seconds < 31536000 * 100) return { seconds, text: `${Math.round(seconds / 31536000)} 年` }
  if (seconds < 31536000 * 1e6) return { seconds, text: `${Math.round(seconds / 31536000 / 1000)} 千年` }
  if (seconds < 31536000 * 1e9) return { seconds, text: `${Math.round(seconds / 31536000 / 1e6)} 百万年` }
  return { seconds, text: `${Math.round(seconds / 31536000 / 1e9)} 十亿年` }
}

function generateSecureRandom(length, chars) {
  const array = new Uint32Array(length)
  crypto.getRandomValues(array)

  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars[array[i] % chars.length]
  }

  let hasLower = /[a-z]/.test(result)
  let hasUpper = /[A-Z]/.test(result)
  let hasDigit = /[0-9]/.test(result)
  let hasSpecial = /[^a-zA-Z0-9]/.test(result)

  let neededTypes = 0
  const needLower = options.value.lowercase && !hasLower
  const needUpper = options.value.uppercase && !hasUpper
  const needDigit = options.value.digits && !hasDigit
  const needSpecial = options.value.specials && !hasSpecial

  if (needLower) neededTypes++
  if (needUpper) neededTypes++
  if (needDigit) neededTypes++
  if (needSpecial) neededTypes++

  if (neededTypes > 0) {
    const positions = new Set()
    while (positions.size < neededTypes) {
      positions.add(Math.floor(Math.random() * length))
    }
    const posArr = [...positions]
    let idx = 0

    if (needLower) {
      const lowerChars = [...CHAR_SETS.lowercase].filter(c => !new Set(options.value.excludeChars).has(c)).join('')
      if (lowerChars.length > 0) {
        result = result.substring(0, posArr[idx]) + lowerChars[Math.floor(Math.random() * lowerChars.length)] + result.substring(posArr[idx] + 1)
        idx++
      }
    }
    if (needUpper) {
      const upperChars = [...CHAR_SETS.uppercase].filter(c => !new Set(options.value.excludeChars).has(c)).join('')
      if (upperChars.length > 0) {
        result = result.substring(0, posArr[idx]) + upperChars[Math.floor(Math.random() * upperChars.length)] + result.substring(posArr[idx] + 1)
        idx++
      }
    }
    if (needDigit) {
      const digitChars = [...CHAR_SETS.digits].filter(c => !new Set(options.value.excludeChars).has(c)).join('')
      if (digitChars.length > 0) {
        result = result.substring(0, posArr[idx]) + digitChars[Math.floor(Math.random() * digitChars.length)] + result.substring(posArr[idx] + 1)
        idx++
      }
    }
    if (needSpecial) {
      const specialChars = [...CHAR_SETS.specials].filter(c => !new Set(options.value.excludeChars).has(c)).join('')
      if (specialChars.length > 0) {
        result = result.substring(0, posArr[idx]) + specialChars[Math.floor(Math.random() * specialChars.length)] + result.substring(posArr[idx] + 1)
        idx++
      }
    }
  }

  return result
}

async function handleGenerate() {
  const chars = getEffectiveCharSet()
  if (!chars) return

  const list = []
  for (let i = 0; i < options.value.count; i++) {
    const pwd = generateSecureRandom(options.value.length, chars)
    const crackEstimate = estimateCrackTime(chars.length, options.value.length)
    list.push({ value: pwd, crackTime: crackEstimate.text })
  }

  passwords.value = list

  if (recordHistory.value) {
    try {
      const charTypes = []
      if (options.value.lowercase) charTypes.push('a-z')
      if (options.value.uppercase) charTypes.push('A-Z')
      if (options.value.digits) charTypes.push('0-9')
      if (options.value.specials) charTypes.push('特殊字符')

      const fd = new FormData()
      fd.append('passwords', JSON.stringify(list.map(p => p.value)))
      fd.append('length', options.value.length.toString())
      fd.append('char_types', JSON.stringify(charTypes))
      fd.append('exclude_chars', options.value.excludeChars)
      fd.append('count', options.value.count.toString())

      await api.savePasswordHistory(fd)
    } catch (e) {
      console.error('Save history failed:', e)
    }
  }

  message.success(`已生成 ${list.length} 个密码`)
}

function handleClearResult() {
  passwords.value = []
}

async function handleCopyOne(text) {
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

async function handleCopyAll() {
  const all = passwords.value.map(p => p.value).join('\n')
  try {
    await navigator.clipboard.writeText(all)
    message.success('已复制全部密码到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = await api.getPasswordHistory({
      page: historyPage.value,
      page_size: historyPageSize.value,
    })
    if (res.code === 200) {
      historyData.value = (res.data || []).map(item => ({
        id: item.id,
        password: item.password,
        length: item.length,
        charTypes: (item.char_types || []).join(', '),
        excludeChars: item.exclude_chars || '-',
        count: item.count,
        createdTime: item.created_at,
      }))
      historyTotal.value = res.total || 0
    }
  } catch (e) {
    message.error('获取历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

async function handleToggleHistory() {
  showHistory.value = !showHistory.value
  if (showHistory.value && historyData.value.length === 0) {
    await fetchHistory()
  }
}

async function handleClearHistory() {
  try {
    await api.deletePasswordHistory()
    historyData.value = []
    historyTotal.value = 0
    message.success('历史记录已清空')
  } catch (e) {
    message.error('清空失败')
  }
}

async function handleDeleteHistory(id) {
  try {
    await api.deletePasswordHistory({ ids: String(id) })
    message.success('已删除')
    await fetchHistory()
  } catch (e) {
    message.error('删除失败')
  }
}

const historyColumns = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '密码', key: 'password', width: 280, ellipsis: { tooltip: true } },
  { title: '长度', key: 'length', width: 60 },
  { title: '字符类型', key: 'charTypes', width: 140 },
  { title: '排除字符', key: 'excludeChars', width: 100, ellipsis: { tooltip: true } },
  { title: '批量数量', key: 'count', width: 70 },
  { title: '生成时间', key: 'createdTime', width: 170 },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render(row) {
      return h(
        NPopconfirm,
        { onPositiveClick: () => handleDeleteHistory(row.id) },
        {
          trigger: () =>
            h(NButton, { size: 'tiny', type: 'error' }, { default: () => '删除' }),
          default: () => '确定要删除这条记录吗？',
        }
      )
    },
  },
]
</script>

<style scoped>
.passwordgen-container {
  max-width: 1200px;
  margin: 0 auto;
}

.options-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.action-buttons {
  width: 100%;
}

.result-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  animation: fadeIn 0.3s ease-in;
}

.password-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.password-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.password-index {
  min-width: 32px;
  color: #666;
  font-size: 13px;
  text-align: right;
}

.password-input {
  flex: 1;
  max-width: 600px;
}

.crack-time-tag {
  white-space: nowrap;
  flex-shrink: 0;
}

.history-card {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.history-pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.empty-state {
  padding: 32px 0;
}

.usage-guide {
  margin-top: 24px;
  background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
}

.guide-content {
  padding: 4px 0;
}

.guide-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1976d2;
}

.guide-list {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
  color: #424242;
}

.guide-list li {
  margin-bottom: 4px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .passwordgen-container {
    padding: 0 8px;
  }

  .password-item {
    flex-wrap: wrap;
  }

  .password-input {
    max-width: 100%;
  }

  .options-card {
    margin-bottom: 16px;
  }

  .result-card {
    margin-bottom: 16px;
  }

  .history-card {
    margin-bottom: 16px;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .action-buttons :deep(.n-button) {
    width: 100%;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .passwordgen-container {
    padding: 0 16px;
  }
}

@media (min-width: 1440px) {
  .passwordgen-container {
    max-width: 1400px;
  }
}
</style>
