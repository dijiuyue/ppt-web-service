<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  ElButton,
  ElIcon,
  ElSlider,
  ElTooltip,
  ElEmpty,
  ElInput
} from 'element-plus'
import {
  ZoomIn,
  ZoomOut,
  FullScreen,
  Download,
  Edit,
  Check,
  Close,
  RefreshLeft
} from '@element-plus/icons-vue'
import type { SVGPage } from '@/types'

const props = defineProps<{
  page: SVGPage | null
  svgContent: string
  editable?: boolean
}>()

const emit = defineEmits<{
  (e: 'save', content: string): void
  (e: 'download'): void
}>()

const scale = ref(1)
const isFullscreen = ref(false)
const isEditing = ref(false)
const editedContent = ref('')
const viewerContainer = ref<HTMLElement | null>(null)

const scalePercent = computed(() => Math.round(scale.value * 100))

watch(() => props.svgContent, (newVal) => {
  if (!isEditing.value) {
    editedContent.value = newVal
  }
}, { immediate: true })

const handleZoomIn = () => {
  if (scale.value < 3) scale.value = Math.min(3, scale.value + 0.1)
}

const handleZoomOut = () => {
  if (scale.value > 0.2) scale.value = Math.max(0.2, scale.value - 0.1)
}

const handleZoomChange = (val: number) => {
  scale.value = val / 100
}

const handleResetZoom = () => {
  scale.value = 1
}

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    viewerContainer.value?.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

const handleEdit = () => {
  isEditing.value = true
  editedContent.value = props.svgContent
}

const handleSave = () => {
  emit('save', editedContent.value)
  isEditing.value = false
}

const handleCancel = () => {
  editedContent.value = props.svgContent
  isEditing.value = false
}

const handleDownload = () => {
  emit('download')
}

const hasContent = computed(() => {
  return props.svgContent && props.svgContent.length > 0
})

// 清理 SVG 内容，确保可以安全地内联显示
const sanitizedSvg = computed(() => {
  if (!props.svgContent) return ''
  // 如果内容已经是完整的 SVG，直接返回
  if (props.svgContent.trim().startsWith('<svg')) {
    return props.svgContent
  }
  // 否则包装在 svg 标签中
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">${props.svgContent}</svg>`
})
</script>

<template>
  <div ref="viewerContainer" class="svg-viewer" :class="{ 'is-fullscreen': isFullscreen }">
    <!-- 工具栏 -->
    <div class="viewer-toolbar">
      <div class="toolbar-left">
        <span v-if="page" class="page-info">
          P{{ String(page.page_number).padStart(2, '0') }} - {{ page.page_name }}
        </span>
      </div>
      <div class="toolbar-right">
        <!-- 编辑模式 -->
        <template v-if="editable && isEditing">
          <ElButton type="success" size="small" @click="handleSave">
            <ElIcon><Check /></ElIcon> 保存
          </ElButton>
          <ElButton size="small" @click="handleCancel">
            <ElIcon><Close /></ElIcon> 取消
          </ElButton>
        </template>
        <template v-else-if="editable">
          <ElTooltip content="编辑 SVG">
            <ElButton link size="small" @click="handleEdit">
              <ElIcon><Edit /></ElIcon>
            </ElButton>
          </ElTooltip>
        </template>

        <!-- 缩放控制 -->
        <div class="zoom-controls">
          <ElTooltip content="缩小">
            <ElButton link size="small" @click="handleZoomOut">
              <ElIcon><ZoomOut /></ElIcon>
            </ElButton>
          </ElTooltip>
          <ElSlider
            v-model="scalePercent"
            :min="20"
            :max="300"
            :step="10"
            size="small"
            class="zoom-slider"
            @change="handleZoomChange"
          />
          <ElTooltip content="放大">
            <ElButton link size="small" @click="handleZoomIn">
              <ElIcon><ZoomIn /></ElIcon>
            </ElButton>
          </ElTooltip>
          <span class="zoom-value">{{ scalePercent }}%</span>
          <ElTooltip content="重置">
            <ElButton link size="small" @click="handleResetZoom">
              <ElIcon><RefreshLeft /></ElIcon>
            </ElButton>
          </ElTooltip>
        </div>

        <!-- 全屏 -->
        <ElTooltip content="全屏">
          <ElButton link size="small" @click="toggleFullscreen">
            <ElIcon><FullScreen /></ElIcon>
          </ElButton>
        </ElTooltip>

        <!-- 下载 -->
        <ElTooltip content="下载 SVG">
          <ElButton link size="small" @click="handleDownload">
            <ElIcon><Download /></ElIcon>
          </ElButton>
        </ElTooltip>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="viewer-content">
      <!-- 编辑模式 -->
      <div v-if="isEditing" class="edit-mode">
        <ElInput
          v-model="editedContent"
          type="textarea"
          :rows="24"
          class="svg-editor"
          placeholder="在此编辑 SVG 代码..."
        />
      </div>

      <!-- 预览模式 -->
      <div v-else-if="hasContent" class="preview-mode">
        <div
          class="svg-container"
          :style="{ transform: `scale(${scale.value})`, transformOrigin: 'center center' }"
        >
          <div v-html="sanitizedSvg" class="svg-render" />
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-mode">
        <ElEmpty description="暂无 SVG 内容" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.svg-viewer {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border-radius: var(--border-radius-md);
  border: 1px solid var(--border-color);
  overflow: hidden;
  height: 100%;
}

.svg-viewer.is-fullscreen {
  width: 100vw;
  height: 100vh;
  border-radius: 0;
}

.viewer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 8px;
}

.page-info {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  border-left: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
  margin: 0 4px;
}

.zoom-slider {
  width: 100px;
}

.zoom-value {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 40px;
  text-align: center;
}

.viewer-content {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.preview-mode {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #f0f0f0;
  overflow: auto;
}

.svg-container {
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform var(--transition-fast);
}

.svg-render :deep(svg) {
  display: block;
  max-width: 100%;
  max-height: 100%;
}

.edit-mode {
  flex: 1;
  padding: 16px;
}

.svg-editor :deep(textarea) {
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.empty-mode {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
