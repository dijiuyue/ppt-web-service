<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ElButton,
  ElTag,
  ElTabs,
  ElTabPane,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
  ElMessageBox,
  ElMessage,
  ElIcon,
  ElLoading,
  ElTooltip
} from 'element-plus'
import {
  VideoPlay,
  CircleClose,
  RefreshRight,
  Delete,
  Edit,
  ArrowLeft,
  Document,
  Brush,
  Files,
  Download,
  Link,
  WarningFilled
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import PipelineStatus from '@/components/PipelineStatus.vue'
import SourceUploader from '@/components/SourceUploader.vue'
import type { Project, SourceFile } from '@/types'
import { uploadSources, addUrlSource, deleteSource } from '@/api/sources'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const route = useRoute()
const projectStore = useProjectStore()

const activeTab = ref('overview')

const project = computed(() => projectStore.currentProject)
const pipelineStatus = computed(() => projectStore.pipelineStatus)
const sourceFiles = computed(() => projectStore.sourceFiles)
const designSpec = computed(() => projectStore.designSpec)
const svgPages = computed(() => projectStore.svgPages)
const exports = computed(() => projectStore.exports)
const isLoading = computed(() => projectStore.isLoading)
const isPipelineRunning = computed(() => projectStore.isPipelineRunning)
const isWaitingConfirmation = computed(() => projectStore.isWaitingConfirmation)

onMounted(() => {
  loadProject()
})

onUnmounted(() => {
  projectStore.disconnectWebSocket()
})

watch(() => props.id, () => {
  loadProject()
})

const loadProject = async () => {
  if (!props.id) return
  await projectStore.fetchProject(props.id)
  await projectStore.fetchPipelineStatus(props.id)
  await projectStore.fetchSources(props.id)
  await projectStore.fetchDesignSpec(props.id)
  await projectStore.fetchSVGPages(props.id)
  await projectStore.fetchExports(props.id)
  projectStore.connectWebSocket(props.id)
}

const statusConfig = computed(() => {
  if (!project.value) return { type: 'info' as const, label: '未知' }
  const map: Record<string, { type: 'info' | 'warning' | 'primary' | 'success' | 'danger'; label: string }> = {
    draft: { type: 'info', label: '草稿' },
    confirming: { type: 'warning', label: '待确认' },
    processing: { type: 'primary', label: '进行中' },
    completed: { type: 'success', label: '已完成' },
    failed: { type: 'danger', label: '失败' }
  }
  return map[project.value.status] || { type: 'info', label: '未知' }
})

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleStart = async () => {
  await projectStore.startProjectPipeline(props.id)
}

const handleCancel = async () => {
  try {
    await ElMessageBox.confirm('确定要取消当前 Pipeline 吗？', '取消确认', {
      confirmButtonText: '取消Pipeline',
      cancelButtonText: '返回',
      type: 'warning'
    })
    await projectStore.cancelProjectPipeline(props.id)
  } catch {
    // 用户取消
  }
}

const handleResume = async () => {
  await projectStore.resumeProjectPipeline(props.id)
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要删除此项目吗？', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '返回',
      type: 'danger'
    })
    await projectStore.deleteProjectById(props.id)
    router.push('/projects')
  } catch {
    // 用户取消
  }
}

const goToConfirmations = () => {
  router.push(`/projects/${props.id}/confirm`)
}

const goToPages = () => {
  router.push(`/projects/${props.id}/pages`)
}

const goToExports = () => {
  router.push(`/projects/${props.id}/exports`)
}

const goBack = () => {
  router.push('/projects')
}

// 源文件上传处理
const handleUpload = async (files: File[]) => {
  try {
    await uploadSources(props.id, files)
    ElMessage.success('文件上传成功')
    await projectStore.fetchSources(props.id)
  } catch {
    ElMessage.error('上传失败')
  }
}

const handleAddUrl = async (url: string, title?: string) => {
  try {
    await addUrlSource(props.id, { url, title })
    ElMessage.success('URL 添加成功')
    await projectStore.fetchSources(props.id)
  } catch {
    ElMessage.error('添加失败')
  }
}

const handleDeleteSource = async (sourceId: string) => {
  try {
    await deleteSource(props.id, sourceId)
    ElMessage.success('已删除')
    await projectStore.fetchSources(props.id)
  } catch {
    ElMessage.error('删除失败')
  }
}

const getFileTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    pdf: '#ff4d4f', docx: '#1890ff', xlsx: '#52c41a', pptx: '#faad14',
    url: '#722ed1', md: '#13c2c2', txt: '#8c8c8c', html: '#eb2f96', epub: '#fa8c16'
  }
  return colors[type] || '#666'
}
</script>

<template>
  <div class="page-container project-detail-page">
    <!-- 返回栏 -->
    <div class="back-bar">
      <ElButton link @click="goBack">
        <ElIcon><ArrowLeft /></ElIcon>
        返回项目列表
      </ElButton>
    </div>

    <div v-if="isLoading && !project" v-loading="true" class="loading-container" />

    <template v-else-if="project">
      <!-- 页面头部 -->
      <div class="page-header detail-header">
        <div class="detail-title-section">
          <h1 class="page-title">{{ project.name }}</h1>
          <div class="detail-meta">
            <ElTag :type="statusConfig.type" effect="light" size="small">
              {{ statusConfig.label }}
            </ElTag>
            <span class="meta-date">创建于 {{ formatDate(project.created_at) }}</span>
          </div>
          <p v-if="project.description" class="detail-description">
            {{ project.description }}
          </p>
        </div>
        <div class="detail-actions">
          <ElButton
            v-if="project.status === 'draft'"
            type="primary"
            @click="handleStart"
            :loading="isLoading"
          >
            <ElIcon><VideoPlay /></ElIcon>
            启动 Pipeline
          </ElButton>
          <ElButton
            v-if="isWaitingConfirmation"
            type="warning"
            @click="goToConfirmations"
          >
            <ElIcon><WarningFilled /></ElIcon>
            确认设计规范
          </ElButton>
          <ElButton
            v-if="isPipelineRunning"
            @click="handleCancel"
          >
            <ElIcon><CircleClose /></ElIcon>
            取消
          </ElButton>
          <ElButton
            v-if="project.status === 'failed'"
            type="primary"
            @click="handleResume"
            :loading="isLoading"
          >
            <ElIcon><RefreshRight /></ElIcon>
            恢复
          </ElButton>
          <ElButton link type="danger" @click="handleDelete">
            <ElIcon><Delete /></ElIcon>
          </ElButton>
        </div>
      </div>

      <!-- Tab 切换 -->
      <ElTabs v-model="activeTab" class="detail-tabs" type="border-card">
        <!-- 概览 Tab -->
        <ElTabPane name="overview">
          <template #label>
            <span class="tab-label">
              <ElIcon><Files /></ElIcon> 概览
            </span>
          </template>

          <!-- Pipeline 状态 -->
          <div class="tab-content">
            <h3 class="section-title">Pipeline 状态</h3>
            <PipelineStatus :status="pipelineStatus" />
          </div>

          <!-- 项目信息 -->
          <div class="tab-content">
            <h3 class="section-title">项目信息</h3>
            <ElCard>
              <ElDescriptions :column="2" border>
                <ElDescriptionsItem label="项目ID">{{ project.id }}</ElDescriptionsItem>
                <ElDescriptionsItem label="画布格式">{{ project.canvas_format }}</ElDescriptionsItem>
                <ElDescriptionsItem label="LLM 提供商">{{ project.llm_provider }}</ElDescriptionsItem>
                <ElDescriptionsItem label="模型">{{ project.llm_model }}</ElDescriptionsItem>
                <ElDescriptionsItem label="当前步骤">{{ project.current_step }}</ElDescriptionsItem>
                <ElDescriptionsItem label="步骤状态">{{ project.step_status }}</ElDescriptionsItem>
                <ElDescriptionsItem label="创建时间">{{ formatDate(project.created_at) }}</ElDescriptionsItem>
                <ElDescriptionsItem label="更新时间">{{ formatDate(project.updated_at) }}</ElDescriptionsItem>
                <ElDescriptionsItem v-if="project.completed_at" label="完成时间">
                  {{ formatDate(project.completed_at) }}
                </ElDescriptionsItem>
              </ElDescriptions>
            </ElCard>
          </div>
        </ElTabPane>

        <!-- 源文件 Tab -->
        <ElTabPane name="sources">
          <template #label>
            <span class="tab-label">
              <ElIcon><Document /></ElIcon> 源文件 ({{ sourceFiles.length }})
            </span>
          </template>
          <div class="tab-content">
            <SourceUploader
              :project-id="project.id"
              :sources="sourceFiles"
              @upload="handleUpload"
              @add-url="handleAddUrl"
              @delete="handleDeleteSource"
            />
          </div>
        </ElTabPane>

        <!-- Design Spec Tab -->
        <ElTabPane name="designspec">
          <template #label>
            <span class="tab-label">
              <ElIcon><Brush /></ElIcon> Design Spec
            </span>
          </template>
          <div class="tab-content">
            <ElCard v-if="designSpec && designSpec.confirmation_status === 'confirmed'">
              <ElDescriptions :column="1" border>
                <ElDescriptionsItem label="画布">{{ designSpec.confirmation_canvas || '-' }}</ElDescriptionsItem>
                <ElDescriptionsItem label="页数">{{ designSpec.confirmation_page_count || '-' }}</ElDescriptionsItem>
                <ElDescriptionsItem label="受众">{{ designSpec.confirmation_audience || '-' }}</ElDescriptionsItem>
                <ElDescriptionsItem label="风格">{{ designSpec.confirmation_style_mode }} - {{ designSpec.confirmation_style_descriptor || '' }}</ElDescriptionsItem>
                <ElDescriptionsItem label="图标方案">{{ designSpec.confirmation_icon_approach || '-' }}</ElDescriptionsItem>
                <ElDescriptionsItem label="图片方案">{{ designSpec.confirmation_image_approach || '-' }}</ElDescriptionsItem>
                <ElDescriptionsItem label="确认状态">
                  <ElTag type="success">已确认</ElTag>
                  <span v-if="designSpec.confirmed_at">于 {{ formatDate(designSpec.confirmed_at) }}</span>
                </ElDescriptionsItem>
              </ElDescriptions>
            </ElCard>
            <ElEmpty v-else description="尚未完成 Eight Confirmations 确认">
              <template #extra>
                <ElButton v-if="isWaitingConfirmation" type="primary" @click="goToConfirmations">
                  前往确认
                </ElButton>
              </template>
            </ElEmpty>
          </div>
        </ElTabPane>

        <!-- 页面 Tab -->
        <ElTabPane name="pages">
          <template #label>
            <span class="tab-label">
              <ElIcon><Files /></ElIcon> 页面 ({{ svgPages.length }})
            </span>
          </template>
          <div class="tab-content">
            <div v-if="svgPages.length > 0" class="pages-grid">
              <div
                v-for="page in svgPages"
                :key="page.id"
                class="page-card"
                @click="goToPages"
              >
                <div class="page-card-header">
                  <span class="page-number">P{{ String(page.page_number).padStart(2, '0') }}</span>
                  <ElTag :type="page.quality_check_status === 'passed' ? 'success' : 'info'" size="small">
                    {{ page.quality_check_status }}
                  </ElTag>
                </div>
                <div class="page-card-body">
                  <div class="page-preview-placeholder">
                    <ElIcon :size="32" color="#d1d5db"><Files /></ElIcon>
                  </div>
                  <p class="page-name">{{ page.page_name }}</p>
                </div>
              </div>
            </div>
            <ElEmpty v-else description="暂无SVG页面">
              <template #extra>
                <ElButton v-if="project.status === 'completed'" type="primary" @click="goToPages">
                  查看页面
                </ElButton>
              </template>
            </ElEmpty>
          </div>
        </ElTabPane>

        <!-- 导出 Tab -->
        <ElTabPane name="exports">
          <template #label>
            <span class="tab-label">
              <ElIcon><Download /></ElIcon> 导出 ({{ exports.length }})
            </span>
          </template>
          <div class="tab-content">
            <div v-if="exports.length > 0">
              <ElCard v-for="exp in exports" :key="exp.id" class="export-item">
                <div class="export-info">
                  <span class="export-name">{{ exp.filename }}</span>
                  <span class="export-date">{{ formatDate(exp.created_at) }}</span>
                </div>
                <ElButton type="primary" size="small" @click="goToExports">
                  <ElIcon><Download /></ElIcon>
                  查看
                </ElButton>
              </ElCard>
            </div>
            <ElEmpty v-else description="暂无导出文件">
              <template #extra>
                <ElButton v-if="project.status === 'completed'" type="primary" @click="goToExports">
                  导出 PPT
                </ElButton>
              </template>
            </ElEmpty>
          </div>
        </ElTabPane>
      </ElTabs>
    </template>

    <ElEmpty v-else description="项目不存在或已被删除">
      <template #extra>
        <ElButton type="primary" @click="goBack">返回项目列表</ElButton>
      </template>
    </ElEmpty>
  </div>
</template>

<style scoped>
.project-detail-page {
  max-width: 1200px;
}

.back-bar {
  margin-bottom: 16px;
}

.loading-container {
  height: 400px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.detail-title-section {
  flex: 1;
}

.page-title {
  margin-bottom: 8px;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.meta-date {
  font-size: 13px;
  color: var(--text-muted);
}

.detail-description {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 8px 0 0 0;
  max-width: 600px;
  line-height: 1.6;
}

.detail-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-tabs {
  background: var(--bg-primary);
  border-radius: var(--border-radius-md);
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tab-content {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-left: 4px;
  border-left: 3px solid var(--primary-color);
}

.pages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.page-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  padding: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.page-card:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-md);
}

.page-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.page-number {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.page-card-body {
  text-align: center;
}

.page-preview-placeholder {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--bg-secondary);
  border-radius: var(--border-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.page-name {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.export-item {
  margin-bottom: 12px;
}

.export-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.export-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.export-date {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
