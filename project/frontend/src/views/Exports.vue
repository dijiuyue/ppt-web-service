<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElButton,
  ElIcon,
  ElLoading,
  ElEmpty,
  ElMessage,
  ElCard,
  ElTag,
  ElDialog,
  ElDescriptions,
  ElDescriptionsItem,
  ElTooltip
} from 'element-plus'
import {
  ArrowLeft,
  Download,
  Refresh,
  Document,
  Calendar,
  FolderOpened
} from '@element-plus/icons-vue'
import { useProjectStore } from '@/stores/project'
import { getExports, downloadExport, createExport } from '@/api/exports'
import type { PPTXExport } from '@/types'

const props = defineProps<{
  id: string
}>()

const router = useRouter()
const projectStore = useProjectStore()

const exports = ref<PPTXExport[]>([])
const isLoading = ref(false)
const isExporting = ref(false)
const isDownloading = ref<string | null>(null)
const showPreview = ref(false)
const previewExport = ref<PPTXExport | null>(null)

const project = computed(() => projectStore.currentProject)

onMounted(() => {
  loadExports()
})

const loadExports = async () => {
  isLoading.value = true
  try {
    await projectStore.fetchProject(props.id)
    const list = await getExports(props.id)
    exports.value = list
  } catch {
    // 错误由拦截器处理
  } finally {
    isLoading.value = false
  }
}

const handleDownload = async (exp: PPTXExport) => {
  isDownloading.value = exp.id
  try {
    const blob = await downloadExport(props.id, exp.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = exp.filename
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch {
    ElMessage.error('下载失败')
  } finally {
    isDownloading.value = null
  }
}

const handleReExport = async () => {
  isExporting.value = true
  try {
    await createExport(props.id)
    ElMessage.success('重新导出已启动')
    await loadExports()
  } catch {
    ElMessage.error('导出失败')
  } finally {
    isExporting.value = false
  }
}

const handlePreview = (exp: PPTXExport) => {
  previewExport.value = exp
  showPreview.value = true
}

const formatDate = (dateStr: string): string => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatFileSize = (bytes: number | null): string => {
  if (!bytes) return '-'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const goBack = () => {
  router.push(`/projects/${props.id}`)
}
</script>

<template>
  <div class="page-container exports-page">
    <!-- 返回栏 -->
    <div class="back-bar">
      <ElButton link @click="goBack">
        <ElIcon><ArrowLeft /></ElIcon>
        返回项目详情
      </ElButton>
    </div>

    <div class="page-header">
      <div>
        <h1 class="page-title">导出管理</h1>
        <p class="page-subtitle" v-if="project">
          {{ project.name }} - 下载和管理 PPT 导出文件
        </p>
      </div>
      <ElButton
        type="primary"
        :loading="isExporting"
        @click="handleReExport"
        :disabled="project?.status !== 'completed'"
      >
        <ElIcon><Refresh /></ElIcon>
        重新导出
      </ElButton>
    </div>

    <!-- 导出列表 -->
    <div v-if="isLoading" v-loading="true" class="loading-container" />

    <div v-else-if="exports.length > 0" class="exports-list">
      <ElCard
        v-for="exp in exports"
        :key="exp.id"
        class="export-card card-hover"
        shadow="hover"
      >
        <div class="export-card-content">
          <div class="export-icon">
            <ElIcon :size="36" color="var(--primary-color)">
              <Document />
            </ElIcon>
          </div>
          <div class="export-info">
            <h4 class="export-filename">{{ exp.filename }}</h4>
            <div class="export-meta">
              <span class="meta-item">
                <ElIcon><Calendar /></ElIcon>
                {{ formatDate(exp.created_at) }}
              </span>
              <span class="meta-item">
                <ElIcon><FolderOpened /></ElIcon>
                {{ formatFileSize(exp.file_size) }}
              </span>
              <ElTag type="info" size="small">{{ exp.export_type }}</ElTag>
            </div>
          </div>
          <div class="export-actions">
            <ElTooltip content="下载 PPT">
              <ElButton
                type="primary"
                :loading="isDownloading === exp.id"
                @click="handleDownload(exp)"
              >
                <ElIcon><Download /></ElIcon>
                下载
              </ElButton>
            </ElTooltip>
            <ElButton link @click="handlePreview(exp)">查看详情</ElButton>
          </div>
        </div>
      </ElCard>
    </div>

    <ElEmpty v-else description="暂无导出文件">
      <template #extra>
        <ElButton
          type="primary"
          :loading="isExporting"
          @click="handleReExport"
          :disabled="project?.status !== 'completed'"
        >
          <ElIcon><Refresh /></ElIcon>
          立即导出
        </ElButton>
      </template>
    </ElEmpty>

    <!-- 预览对话框 -->
    <ElDialog
      v-model="showPreview"
      title="导出详情"
      width="500px"
      destroy-on-close
    >
      <ElDescriptions v-if="previewExport" :column="1" border>
        <ElDescriptionsItem label="文件名">{{ previewExport.filename }}</ElDescriptionsItem>
        <ElDescriptionsItem label="导出类型">{{ previewExport.export_type }}</ElDescriptionsItem>
        <ElDescriptionsItem label="文件大小">{{ formatFileSize(previewExport.file_size) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="转场效果">{{ previewExport.transition_effect || '默认' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="动画效果">{{ previewExport.animation_effect || '默认' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="创建时间">{{ formatDate(previewExport.created_at) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="存储路径">{{ previewExport.storage_key }}</ElDescriptionsItem>
      </ElDescriptions>
      <template #footer>
        <ElButton @click="showPreview = false">关闭</ElButton>
        <ElButton
          v-if="previewExport"
          type="primary"
          :loading="isDownloading === previewExport.id"
          @click="handleDownload(previewExport)"
        >
          <ElIcon><Download /></ElIcon>
          下载
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.exports-page {
  max-width: 1000px;
}

.back-bar {
  margin-bottom: 16px;
}

.loading-container {
  height: 300px;
}

.exports-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.export-card {
  border-radius: var(--border-radius-md);
}

.export-card-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.export-icon {
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
}

.export-info {
  flex: 1;
  min-width: 0;
}

.export-filename {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  word-break: break-all;
}

.export-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.export-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .export-card-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .export-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
