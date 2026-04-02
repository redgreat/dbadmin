<template>
  <CommonPage show-footer>
    <div class="wherein-container">
      <!-- 输入区域 -->
      <n-card class="input-card" :bordered="false">
        <n-form ref="formRef" :model="form" label-placement="left" :label-width="100">
          <!-- 输入框 -->
          <n-form-item label="输入数据" path="inputData">
            <n-input
              v-model:value="form.inputData"
              type="textarea"
              :rows="10"
              placeholder="请输入数据，每行一个值&#10;例如：&#10;ZR25100082&#10;ZR25120094&#10;ZR25100083"
              clearable
            />
          </n-form-item>

          <!-- 数据库类型选择 -->
          <n-form-item label="数据库类型" path="dbType">
            <n-radio-group v-model:value="form.dbType" size="medium">
              <n-space>
                <n-radio value="mysql">MySQL</n-radio>
                <n-radio value="postgresql">PostgreSQL</n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>

          <!-- 操作按钮 -->
          <n-form-item label=" " :show-label="true">
            <n-space class="action-buttons">
              <n-button
                type="primary"
                size="medium"
                :disabled="!form.inputData"
                @click="handleFormatIn"
              >
                <template #icon>
                  <TheIcon icon="material-symbols:code" :size="18" />
                </template>
                格式化为 IN 语句
              </n-button>
              <n-button
                type="info"
                size="medium"
                :disabled="!form.inputData"
                @click="handleFormatValues"
              >
                <template #icon>
                  <TheIcon icon="material-symbols:data-object" :size="18" />
                </template>
                格式化为 VALUES
              </n-button>
              <n-button
                type="success"
                size="medium"
                :disabled="!form.inputData"
                @click="handleFormatTempTable"
              >
                <template #icon>
                  <TheIcon icon="material-symbols:table-add" :size="18" />
                </template>
                生成临时表SQL
              </n-button>
              <n-button size="medium" @click="handleClear">
                <template #icon>
                  <TheIcon icon="material-symbols:clear-all" :size="18" />
                </template>
                清空
              </n-button>
            </n-space>
          </n-form-item>
        </n-form>
      </n-card>

      <!-- 结果显示区域 -->
      <n-card v-if="sqlResult" title="生成的SQL语句" class="result-card" :bordered="false">
        <template #header-extra>
          <n-space>
            <n-button type="primary" size="small" @click="handleCopy">
              <template #icon>
                <TheIcon icon="material-symbols:content-copy" :size="16" />
              </template>
              复制到剪贴板
            </n-button>
          </n-space>
        </template>
        <n-input
          v-model:value="sqlResult"
          type="textarea"
          :rows="15"
          readonly
          placeholder="生成的SQL语句将显示在这里..."
          class="sql-textarea"
        />
      </n-card>

      <!-- 使用说明 -->
      <n-alert type="info" class="usage-guide" :bordered="false">
        <template #icon>
          <TheIcon icon="material-symbols:info-outline" :size="20" />
        </template>
        <div class="guide-content">
          <div class="guide-title">使用说明</div>
          <ul class="guide-list">
            <li>在输入框中输入数据，每行一个值</li>
            <li><strong>格式化为 IN 语句</strong>：生成 WHERE IN 条件语句，如 ('value1', 'value2', ...)</li>
            <li><strong>格式化为 VALUES</strong>：生成 INSERT VALUES 语句，如 VALUES ('value1'), ('value2'), ...</li>
            <li><strong>生成临时表SQL</strong>：创建临时表 tm_年月日时分秒，包含自增主键和 InsValues 字段，并插入数据</li>
          </ul>
        </div>
      </n-alert>
    </div>
  </CommonPage>
</template>

<script setup>
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

defineOptions({ name: 'IN语句拼接' })

const message = useMessage()
const formRef = ref(null)
const sqlResult = ref('')

const form = ref({
  inputData: '',
  dbType: 'mysql'
})

/** 处理输入数据，去除空行和首尾空格 */
const processInputData = () => {
  if (!form.value.inputData) {
    message.warning('请输入数据')
    return null
  }

  const lines = form.value.inputData
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)

  if (lines.length === 0) {
    message.warning('没有有效的数据')
    return null
  }

  return lines
}

/** 格式化为 IN 语句 */
const handleFormatIn = () => {
  const lines = processInputData()
  if (!lines) return

  const quotedLines = lines.map(line => `'${line}'`)
  const result = `(${quotedLines.join(',\n')})`
  
  sqlResult.value = result
  message.success('IN 语句生成成功')
}

/** 格式化为 VALUES 语句 */
const handleFormatValues = () => {
  const lines = processInputData()
  if (!lines) return

  const valuesLines = lines.map(line => `('${line}')`)
  const result = `VALUES ${valuesLines.join(',\n')}`
  
  sqlResult.value = result
  message.success('VALUES 语句生成成功')
}

/** 生成临时表 SQL */
const handleFormatTempTable = () => {
  const lines = processInputData()
  if (!lines) return

  // 生成表名：tm_年月日时分秒
  const now = new Date()
  const tableName = `tm_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`

  let createTableSql = ''
  const isPostgreSQL = form.value.dbType === 'postgresql'

  if (isPostgreSQL) {
    // PostgreSQL 语法
    createTableSql = `CREATE TABLE "${tableName}" (
  "id" SERIAL PRIMARY KEY,
  "InsValues" VARCHAR(500)
);`
  } else {
    // MySQL 语法
    createTableSql = `CREATE TABLE \`${tableName}\` (
  \`id\` INT AUTO_INCREMENT PRIMARY KEY,
  \`InsValues\` VARCHAR(500)
);`
  }

  // 生成 VALUES 语句
  const valuesLines = lines.map(line => `('${line}')`)
  const insertSql = isPostgreSQL
    ? `INSERT INTO "${tableName}" ("InsValues") VALUES\n${valuesLines.join(',\n')};`
    : `INSERT INTO \`${tableName}\` (\`InsValues\`) VALUES\n${valuesLines.join(',\n')};`

  sqlResult.value = `${createTableSql}\n\n${insertSql}`
  message.success('临时表 SQL 生成成功')
}

/** 清空 */
const handleClear = () => {
  form.value.inputData = ''
  sqlResult.value = ''
}

/** 复制到剪贴板 */
const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(sqlResult.value)
    message.success('已复制到剪贴板')
  } catch (e) {
    message.error('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.wherein-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* 使用说明样式 */
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

/* 输入卡片样式 */
.input-card {
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.action-buttons {
  width: 100%;
}

/* 结果卡片样式 */
.result-card {
  margin-top: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  animation: fadeIn 0.3s ease-in;
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

.sql-textarea {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.sql-textarea :deep(textarea) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

/* 移动端响应式布局 */
@media (max-width: 768px) {
  .wherein-container {
    padding: 0 8px;
  }

  .usage-guide {
    margin-top: 16px;
  }

  .guide-title {
    font-size: 14px;
  }

  .guide-list {
    font-size: 13px;
    padding-left: 16px;
    line-height: 1.6;
  }

  .input-card {
    margin-bottom: 16px;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }

  .action-buttons :deep(.n-button) {
    width: 100%;
  }

  .sql-textarea {
    font-size: 12px;
  }

  .sql-textarea :deep(textarea) {
    font-size: 12px;
  }
}

/* 平板端响应式布局 */
@media (min-width: 769px) and (max-width: 1024px) {
  .wherein-container {
    padding: 0 16px;
  }

  .guide-list {
    font-size: 14px;
  }
}

/* 大屏幕优化 */
@media (min-width: 1440px) {
  .wherein-container {
    max-width: 1400px;
  }
}
</style>
