<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import {
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
  ElButton,
  ElCard,
  ElMessage,
  ElIcon,
  ElRadioGroup,
  ElRadioButton,
  ElDivider,
  ElTag
} from 'element-plus'
import {
  Setting,
  Key,
  Monitor,
  Brush,
  Save,
  Check,
  RefreshLeft,
  InfoFilled
} from '@element-plus/icons-vue'
import type { LLMProvider, AppSettings } from '@/types'

const isSaving = ref(false)
const settingsSaved = ref(false)

const settings = reactive<AppSettings>({
  llm_api_key: '',
  llm_provider: 'openai',
  llm_model: 'gpt-4o',
  default_canvas_format: 'ppt169',
  theme: 'light'
})

const modelOptions = computed(() => {
  if (settings.llm_provider === 'openai') {
    return [
      { value: 'gpt-4o', label: 'GPT-4o (推荐)' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'gpt-4', label: 'GPT-4' }
    ]
  }
  return [
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
    { value: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
    { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' }
  ]
})

import { computed, watch } from 'vue'

watch(() => settings.llm_provider, () => {
  if (settings.llm_provider === 'openai') {
    settings.llm_model = 'gpt-4o'
  } else {
    settings.llm_model = 'claude-sonnet-4-20250514'
  }
})

onMounted(() => {
  const saved = localStorage.getItem('app_settings')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      Object.assign(settings, parsed)
    } catch {
      // 忽略解析错误
    }
  }
})

const handleSave = async () => {
  isSaving.value = true
  try {
    // 模拟保存延迟
    await new Promise((resolve) => setTimeout(resolve, 500))
    localStorage.setItem('app_settings', JSON.stringify(settings))
    settingsSaved.value = true
    ElMessage.success('设置已保存')
    setTimeout(() => {
      settingsSaved.value = false
    }, 3000)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    isSaving.value = false
  }
}

const handleReset = () => {
  settings.llm_api_key = ''
  settings.llm_provider = 'openai'
  settings.llm_model = 'gpt-4o'
  settings.default_canvas_format = 'ppt169'
  settings.theme = 'light'
  ElMessage.info('已重置为默认设置')
}

const providers: { value: LLMProvider; label: string }[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' }
]

const canvasFormats = [
  { value: 'ppt169' as const, label: 'PPT 16:9' },
  { value: 'ppt43' as const, label: 'PPT 4:3' },
  { value: 'xhs' as const, label: '小红书' },
  { value: 'story' as const, label: 'Story' }
]
</script>

<template>
  <div class="page-container settings-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">
          <ElIcon><Setting /></ElIcon>
          系统设置
        </h1>
        <p class="page-subtitle">配置您的 AI 模型和默认选项</p>
      </div>
    </div>

    <div class="settings-grid">
      <!-- LLM 配置 -->
      <ElCard class="settings-card">
        <template #header>
          <div class="card-header">
            <ElIcon :size="18"><Key /></ElIcon>
            <span>LLM 配置</span>
          </div>
        </template>

        <ElForm label-position="top" class="settings-form">
          <ElFormItem label="API Key">
            <ElInput
              v-model="settings.llm_api_key"
              type="password"
              placeholder="sk-..."
              show-password
              size="large"
            >
              <template #prefix>
                <ElIcon><Key /></ElIcon>
              </template>
            </ElInput>
            <div class="form-hint">
              <ElIcon><InfoFilled /></ElIcon>
              <span>您的 API Key 仅存储在本地浏览器中，不会上传到服务器</span>
            </div>
          </ElFormItem>

          <ElFormItem label="默认 LLM 提供商">
            <ElRadioGroup v-model="settings.llm_provider" size="large">
              <ElRadioButton
                v-for="provider in providers"
                :key="provider.value"
                :label="provider.value"
              >
                {{ provider.label }}
              </ElRadioButton>
            </ElRadioGroup>
          </ElFormItem>

          <ElFormItem label="默认模型">
            <ElSelect v-model="settings.llm_model" class="full-width" size="large">
              <ElOption
                v-for="model in modelOptions"
                :key="model.value"
                :label="model.label"
                :value="model.value"
              />
            </ElSelect>
          </ElFormItem>
        </ElForm>
      </ElCard>

      <!-- 默认项目设置 -->
      <ElCard class="settings-card">
        <template #header>
          <div class="card-header">
            <ElIcon :size="18"><Monitor /></ElIcon>
            <span>默认项目设置</span>
          </div>
        </template>

        <ElForm label-position="top" class="settings-form">
          <ElFormItem label="默认画布格式">
            <div class="format-options">
              <div
                v-for="fmt in canvasFormats"
                :key="fmt.value"
                class="format-option-btn"
                :class="{ active: settings.default_canvas_format === fmt.value }"
                @click="settings.default_canvas_format = fmt.value"
              >
                <Monitor v-if="fmt.value.includes('ppt')" :size="20" />
                <Brush v-else :size="20" />
                <span>{{ fmt.label }}</span>
              </div>
            </div>
          </ElFormItem>
        </ElForm>
      </ElCard>

      <!-- 关于 -->
      <ElCard class="settings-card about-card">
        <template #header>
          <div class="card-header">
            <ElIcon :size="18"><InfoFilled /></ElIcon>
            <span>关于</span>
          </div>
        </template>
        <div class="about-content">
          <h3>PPT Master</h3>
          <p>AI 驱动的专业演示文稿生成服务</p>
          <p class="version">版本 1.0.0</p>
          <ElTag type="info" size="small">Vue 3 + TypeScript</ElTag>
          <ElTag type="info" size="small">Element Plus</ElTag>
          <ElTag type="info" size="small">FastAPI</ElTag>
        </div>
      </ElCard>
    </div>

    <!-- 保存按钮 -->
    <div class="settings-actions">
      <ElButton size="large" @click="handleReset">
        <ElIcon><RefreshLeft /></ElIcon>
        重置
      </ElButton>
      <ElButton
        type="primary"
        size="large"
        :loading="isSaving"
        @click="handleSave"
      >
        <ElIcon v-if="settingsSaved"><Check /></ElIcon>
        <ElIcon v-else><Save /></ElIcon>
        {{ settingsSaved ? '已保存' : '保存设置' }}
      </ElButton>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  max-width: 800px;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 24px;
}

.settings-card {
  border-radius: var(--border-radius-md);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.settings-form {
  max-width: 600px;
}

.full-width {
  width: 100%;
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.format-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.format-option-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: 14px;
  color: var(--text-primary);
}

.format-option-btn:hover {
  border-color: var(--primary-light);
}

.format-option-btn.active {
  border-color: var(--primary-color);
  background: var(--primary-light);
  color: var(--primary-color);
  font-weight: 500;
}

.about-card .about-content {
  text-align: center;
  padding: 16px 0;
}

.about-content h3 {
  font-size: 20px;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.about-content p {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.version {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 12px !important;
}

.about-content .el-tag {
  margin: 0 4px;
}

.settings-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  position: sticky;
  bottom: 0;
  background: var(--bg-secondary);
  padding: 16px;
  margin: 0 -24px -24px -24px;
}

@media (max-width: 768px) {
  .settings-actions {
    margin: 0 -16px -16px -16px;
  }
}
</style>
