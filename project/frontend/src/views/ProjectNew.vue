<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
  ElButton,
  ElCard,
  ElSteps,
  ElStep,
  ElMessage,
  ElIcon,
  ElRadioGroup,
  ElRadioButton,
  ElUpload
} from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  UploadFilled,
  Document,
  Setting,
  Check,
  Monitor
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { uploadSources } from '@/api/sources'
import type { CreateProjectRequest, CanvasFormat, LLMProvider } from '@/types'

const router = useRouter()
const projectStore = useProjectStore()

const activeStep = ref(0)
const formRef = ref<InstanceType<typeof ElForm>>()
const isSubmitting = ref(false)

const form = reactive<CreateProjectRequest>({
  name: '',
  description: '',
  canvas_format: 'ppt169',
  llm_provider: 'openai',
  llm_model: 'gpt-4o',
  template_path: undefined
})

const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  canvas_format: [{ required: true, message: '请选择画布格式', trigger: 'change' }],
  llm_provider: [{ required: true, message: '请选择LLM提供商', trigger: 'change' }],
  llm_model: [{ required: true, message: '请选择模型', trigger: 'change' }]
}

const canvasFormats = [
  { value: 'ppt169' as CanvasFormat, label: 'PPT 16:9', desc: '标准演示文稿 (1280x720)', icon: Monitor },
  { value: 'ppt43' as CanvasFormat, label: 'PPT 4:3', desc: '传统格式 (1024x768)', icon: Monitor },
  { value: 'xhs' as CanvasFormat, label: '小红书', desc: '社交媒体卡片 (720x960)', icon: Document },
  { value: 'story' as CanvasFormat, label: 'Story', desc: '竖屏故事 (540x960)', icon: Document }
]

const llmProviders: { value: LLMProvider; label: string }[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'deepseek', label: 'DeepSeek' }
]

const modelOptions = computed(() => {
  if (form.llm_provider === 'openai') {
    return [
      { value: 'gpt-4o', label: 'GPT-4o (推荐)' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini (快速)' },
      { value: 'gpt-4', label: 'GPT-4' },
      { value: '__custom__', label: '自定义模型...' }
    ]
  }
  if (form.llm_provider === 'deepseek') {
    return [
      { value: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro (推荐)' },
      { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner' },
      { value: 'deepseek-chat', label: 'DeepSeek Chat' },
      { value: '__custom__', label: '自定义模型...' }
    ]
  }
  return [
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
    { value: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
    { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
    { value: '__custom__', label: '自定义模型...' }
  ]
})

const showCustomModel = ref(false)
const customModel = ref('')

watch(() => form.llm_provider, () => {
  showCustomModel.value = false
  customModel.value = ''
  if (form.llm_provider === 'openai') {
    form.llm_model = 'gpt-4o'
  } else if (form.llm_provider === 'deepseek') {
    form.llm_model = 'deepseek-v4-pro'
  } else {
    form.llm_model = 'claude-sonnet-4-20250514'
  }
})

watch(() => form.llm_model, (newVal) => {
  if (newVal === '__custom__') {
    showCustomModel.value = true
    form.llm_model = customModel.value || ''
  }
})

watch(customModel, (newVal) => {
  if (showCustomModel.value) {
    form.llm_model = newVal
  }
})

const uploadedFiles = ref<File[]>([])
const uploadProjectId = ref<string>('') // 创建项目后填充

const handleFileChange = (file: any) => {
  uploadedFiles.value.push(file.raw)
}

const handleRemove = (file: any) => {
  uploadedFiles.value = uploadedFiles.value.filter(f => f.name !== file.name)
}

const goNext = async () => {
  if (activeStep.value === 0) {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return
  }
  if (activeStep.value < 2) activeStep.value++
}

const goPrev = () => {
  if (activeStep.value > 0) activeStep.value--
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  isSubmitting.value = true
  try {
    const project = await projectStore.createNewProject(form)

    // 如果有上传的文件，先上传源文件
    if (project && uploadedFiles.value.length > 0) {
      await uploadSources(project.id, uploadedFiles.value)
    }

    ElMessage.success('项目创建成功')
    router.push(`/projects/${project.id}`)
  } catch {
    // 错误由拦截器处理
  } finally {
    isSubmitting.value = false
  }
}

const goBack = () => {
  router.push('/projects')
}
</script>

<template>
  <div class="page-container project-new-page">
    <!-- 返回按钮 -->
    <div class="back-bar">
      <ElButton link @click="goBack">
        <ElIcon><ArrowLeft /></ElIcon>
        返回项目列表
      </ElButton>
    </div>

    <div class="page-header">
      <div>
        <h1 class="page-title">创建新项目</h1>
        <p class="page-subtitle">填写项目信息并上传源文件</p>
      </div>
    </div>

    <!-- 步骤条 -->
    <ElSteps :active="activeStep" finish-status="success" align-center class="form-steps">
      <ElStep title="基本信息" description="填写项目配置" />
      <ElStep title="LLM 配置" description="选择AI模型" />
      <ElStep title="源文件" description="上传文档(可选)" />
    </ElSteps>

    <!-- 表单 -->
    <ElForm
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      class="project-form"
      @submit.prevent
    >
      <!-- 步骤 1: 基本信息 -->
      <div v-show="activeStep === 0" class="form-step-content">
        <ElCard>
          <ElFormItem label="项目名称" prop="name">
            <ElInput
              v-model="form.name"
              placeholder="输入项目名称，例如：Q3产品发布会"
              size="large"
              maxlength="100"
              show-word-limit
            />
          </ElFormItem>

          <ElFormItem label="项目描述">
            <ElInput
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="简要描述项目的主题和目标..."
            />
          </ElFormItem>

          <ElFormItem label="画布格式" prop="canvas_format">
            <div class="format-options">
              <div
                v-for="fmt in canvasFormats"
                :key="fmt.value"
                class="format-option"
                :class="{ active: form.canvas_format === fmt.value }"
                @click="form.canvas_format = fmt.value"
              >
                <ElIcon :size="28">
                  <component :is="fmt.icon" />
                </ElIcon>
                <div class="format-option-info">
                  <span class="format-option-label">{{ fmt.label }}</span>
                  <span class="format-option-desc">{{ fmt.desc }}</span>
                </div>
              </div>
            </div>
          </ElFormItem>
        </ElCard>
      </div>

      <!-- 步骤 2: LLM 配置 -->
      <div v-show="activeStep === 1" class="form-step-content">
        <ElCard>
          <ElFormItem label="LLM 提供商" prop="llm_provider">
            <ElRadioGroup v-model="form.llm_provider" size="large">
              <ElRadioButton
                v-for="provider in llmProviders"
                :key="provider.value"
                :label="provider.value"
              >
                {{ provider.label }}
              </ElRadioButton>
            </ElRadioGroup>
          </ElFormItem>

          <ElFormItem label="模型选择" prop="llm_model">
            <ElSelect v-if="!showCustomModel" v-model="form.llm_model" class="full-width" size="large">
              <ElOption
                v-for="model in modelOptions"
                :key="model.value"
                :label="model.label"
                :value="model.value"
              />
            </ElSelect>
            <ElInput
              v-else
              v-model="customModel"
              placeholder="输入模型名称，如 deepseek-v4-pro"
              size="large"
            />
          </ElFormItem>

          <div class="llm-hint">
            <ElIcon><Setting /></ElIcon>
            <span>
              您可以在<strong>系统设置</strong>中配置API密钥和Base URL
            </span>
          </div>
        </ElCard>
      </div>

      <!-- 步骤 3: 源文件 -->
      <div v-show="activeStep === 2" class="form-step-content">
        <ElCard>
          <div class="upload-section">
            <ElUpload
              drag
              multiple
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleRemove"
              accept=".pdf,.docx,.xlsx,.pptx,.md,.txt,.html,.epub"
              class="upload-area"
            >
              <ElIcon class="el-icon--upload"><UploadFilled /></ElIcon>
              <div class="el-upload__text">
                拖拽文件到此处或 <em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持 PDF, DOCX, XLSX, PPTX, MD, TXT, HTML, EPUB
                </div>
              </template>
            </ElUpload>
          </div>
        </ElCard>
      </div>
    </ElForm>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <ElButton v-if="activeStep > 0" @click="goPrev" size="large">
        <ElIcon><ArrowLeft /></ElIcon>
        上一步
      </ElButton>
      <ElButton
        v-if="activeStep < 2"
        type="primary"
        size="large"
        @click="goNext"
      >
        下一步
        <ElIcon><ArrowRight /></ElIcon>
      </ElButton>
      <ElButton
        v-if="activeStep === 2"
        type="primary"
        size="large"
        :loading="isSubmitting"
        @click="handleSubmit"
      >
        <ElIcon><Check /></ElIcon>
        创建项目
      </ElButton>
    </div>
  </div>
</template>

<style scoped>
.project-new-page {
  max-width: 800px;
}

.back-bar {
  margin-bottom: 16px;
}

.form-steps {
  margin-bottom: 32px;
}

.project-form {
  margin-bottom: 24px;
}

.form-step-content {
  animation: fadeIn 0.3s ease;
}

.full-width {
  width: 100%;
}

.format-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.format-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--bg-primary);
}

.format-option:hover {
  border-color: var(--primary-light);
  background: var(--bg-secondary);
}

.format-option.active {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

.format-option-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.format-option-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.format-option-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.llm-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: var(--border-radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
}

.upload-section {
  padding: 20px 0;
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  padding: 40px 20px;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .format-options {
    grid-template-columns: 1fr;
  }
}
</style>
