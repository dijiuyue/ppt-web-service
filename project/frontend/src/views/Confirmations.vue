<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElButton, ElCard, ElIcon, ElLoading, ElEmpty, ElMessage, ElSteps, ElStep } from 'element-plus'
import {
  ArrowLeft,
  Check,
  Brush,
  Monitor,
  Files,
  User,
  Palette,
  CollectionTag,
  FontSize,
  Picture
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import EightConfirmationsForm from '@/components/EightConfirmationsForm.vue'
import type { EightConfirmationsData } from '@/types'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const projectStore = useProjectStore()

const isSubmitting = ref(false)

const project = projectStore.currentProject
const designSpec = projectStore.designSpec
const isLoading = projectStore.isLoading

onMounted(() => {
  if (!projectStore.currentProject || projectStore.currentProject.id !== props.id) {
    projectStore.fetchProject(props.id)
  }
  if (!projectStore.designSpec) {
    projectStore.fetchConfirmations(props.id)
  }
})

const initialData = ref<Partial<EightConfirmationsData>>({})

onMounted(() => {
  if (designSpec) {
    initialData.value = {
      confirmation_canvas: designSpec.confirmation_canvas || undefined,
      confirmation_page_count: designSpec.confirmation_page_count || undefined,
      confirmation_audience: designSpec.confirmation_audience || undefined,
      confirmation_style_mode: (designSpec.confirmation_style_mode as 'A' | 'B' | 'C') || undefined,
      confirmation_style_descriptor: designSpec.confirmation_style_descriptor || undefined,
      confirmation_color_scheme: designSpec.confirmation_color_scheme || undefined,
      confirmation_icon_approach: (designSpec.confirmation_icon_approach as 'A' | 'B' | 'C' | 'D') || undefined,
      confirmation_typography: designSpec.confirmation_typography || undefined,
      confirmation_image_approach: (designSpec.confirmation_image_approach as 'A' | 'B' | 'C' | 'D' | 'E') || undefined
    }
  }
})

const handleSubmit = async (data: EightConfirmationsData) => {
  isSubmitting.value = true
  try {
    await projectStore.submitConfirmations(props.id, data)
    ElMessage.success('确认已提交，Pipeline 继续执行')
    router.push(`/projects/${props.id}`)
  } catch {
    // 错误由拦截器处理
  } finally {
    isSubmitting.value = false
  }
}

const goBack = () => {
  router.push(`/projects/${props.id}`)
}
</script>

<template>
  <div class="page-container confirmations-page">
    <!-- 返回栏 -->
    <div class="back-bar">
      <ElButton link @click="goBack">
        <ElIcon><ArrowLeft /></ElIcon>
        返回项目详情
      </ElButton>
    </div>

    <div class="page-header">
      <div>
        <h1 class="page-title">Eight Confirmations</h1>
        <p class="page-subtitle">
          请仔细确认以下 8 项设计规范，这些将影响最终的PPT生成效果
        </p>
      </div>
    </div>

    <!-- 提示信息 -->
    <ElCard class="hint-card" type="info">
      <div class="hint-content">
        <ElIcon :size="18"><Brush /></ElIcon>
        <span>
          AI 已根据您的源文件生成了设计方案推荐。您可以调整以下配置以满足您的需求。
          确认后将进入页面生成阶段。
        </span>
      </div>
    </ElCard>

    <!-- 加载状态 -->
    <div v-if="isLoading && !designSpec" v-loading="true" class="loading-container" />

    <!-- 确认表单 -->
    <template v-else>
      <EightConfirmationsForm
        :initial-data="initialData"
        :loading="isSubmitting"
        @submit="handleSubmit"
      />
    </template>
  </div>
</template>

<style scoped>
.confirmations-page {
  max-width: 900px;
}

.back-bar {
  margin-bottom: 16px;
}

.hint-card {
  margin-bottom: 24px;
  background: #e6f7ff;
  border-color: #91d5ff;
}

.hint-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.hint-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 14px;
  color: #0958d9;
  line-height: 1.6;
}

.loading-container {
  height: 400px;
}
</style>
