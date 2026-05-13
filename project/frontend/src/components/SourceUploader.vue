<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  ElUpload,
  ElButton,
  ElIcon,
  ElDialog,
  ElInput,
  ElTag,
  ElMessage,
  ElProgress
} from 'element-plus'
import {
  UploadFilled,
  Document,
  Delete,
  Link,
  Plus,
  DocumentCopy,
  Picture,
  Files
} from '@element-plus/icons-vue'
import type { SourceFile, FileType } from '@/types'

const props = defineProps<{
  projectId: string
  sources: SourceFile[]
}>()

const emit = defineEmits<{
  (e: 'upload', files: File[]): void
  (e: 'addUrl', url: string, title?: string): void
  (e: 'delete', sourceId: string): void
}>()

const urlDialogVisible = ref(false)
const urlInput = ref('')
const urlTitle = ref('')
const isDragOver = ref(false)
const uploadInput = ref<HTMLInputElement | null>(null)

const fileTypeIcons: Record<string, any> = {
  pdf: Document,
  docx: DocumentCopy,
  xlsx: Files,
  pptx: Picture,
  url: Link,
  md: Document,
  txt: Document,
  html: Document,
  epub: DocumentCopy
}

const fileTypeColors: Record<FileType, string> = {
  pdf: '#ff4d4f',
  docx: '#1890ff',
  xlsx: '#52c41a',
  pptx: '#faad14',
  url: '#722ed1',
  md: '#13c2c2',
  txt: '#8c8c8c',
  html: '#eb2f96',
  epub: '#fa8c16'
}

const getFileIcon = (type: string) => {
  return fileTypeIcons[type] || Document
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const handleDragOver = (e: DragEvent) => {
  e.preventDefault()
  isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    const fileArray = Array.from(files)
    emit('upload', fileArray)
  }
}

const handleFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files && input.files.length > 0) {
    const fileArray = Array.from(input.files)
    emit('upload', fileArray)
    input.value = ''
  }
}

const handleUploadClick = () => {
  uploadInput.value?.click()
}

const handleAddUrl = () => {
  if (!urlInput.value.trim()) {
    ElMessage.warning('请输入URL')
    return
  }
  emit('addUrl', urlInput.value.trim(), urlTitle.value.trim() || undefined)
  urlDialogVisible.value = false
  urlInput.value = ''
  urlTitle.value = ''
}

const handleDelete = (sourceId: string) => {
  emit('delete', sourceId)
}

const acceptedTypes = '.pdf,.docx,.xlsx,.pptx,.md,.txt,.html,.epub'
</script>

<template>
  <div class="source-uploader">
    <!-- 上传区域 -->
    <div
      class="upload-zone"
      :class="{ 'is-dragover': isDragOver }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="handleUploadClick"
    >
      <input
        ref="uploadInput"
        type="file"
        :accept="acceptedTypes"
        multiple
        class="upload-input-hidden"
        @change="handleFileChange"
      />
      <div class="upload-content">
        <ElIcon :size="48" color="var(--primary-color)">
          <UploadFilled />
        </ElIcon>
        <div class="upload-text">
          <p class="upload-title">拖拽文件到此处，或点击上传</p>
          <p class="upload-hint">
            支持 PDF, DOCX, XLSX, PPTX, MD, TXT, HTML, EPUB
          </p>
        </div>
        <ElButton type="primary" size="small" @click.stop="urlDialogVisible = true">
          <ElIcon><Link /></ElIcon>
          添加 URL
        </ElButton>
      </div>
    </div>

    <!-- 文件列表 -->
    <div v-if="sources.length > 0" class="source-list">
      <div class="source-list-header">
        <span class="source-count">已上传 {{ sources.length }} 个文件</span>
      </div>
      <div class="source-items">
        <div
          v-for="source in sources"
          :key="source.id"
          class="source-item"
        >
          <div class="source-info">
            <div class="source-icon" :style="{ color: fileTypeColors[source.file_type as FileType] || '#666' }">
              <ElIcon :size="24">
                <component :is="getFileIcon(source.file_type)" />
              </ElIcon>
            </div>
            <div class="source-details">
              <span class="source-name" :title="source.original_filename">
                {{ source.original_filename }}
              </span>
              <div class="source-meta">
                <ElTag :type="source.conversion_status === 'completed' ? 'success' : 'info'" size="small">
                  {{ source.conversion_status === 'completed' ? '已转换' : '处理中' }}
                </ElTag>
                <span class="source-size">{{ formatFileSize(source.file_size) }}</span>
              </div>
            </div>
          </div>
          <ElButton
            link
            type="danger"
            size="small"
            @click="handleDelete(source.id)"
          >
            <ElIcon><Delete /></ElIcon>
          </ElButton>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="source-empty">
      <p>暂无源文件，请上传或添加 URL</p>
    </div>

    <!-- URL 对话框 -->
    <ElDialog
      v-model="urlDialogVisible"
      title="添加 URL 源"
      width="500px"
      destroy-on-close
    >
      <div class="url-form">
        <ElInput
          v-model="urlInput"
          placeholder="https://example.com/article"
          size="large"
        >
          <template #prefix>
            <ElIcon><Link /></ElIcon>
          </template>
        </ElInput>
        <ElInput
          v-model="urlTitle"
          placeholder="标题 (可选)"
          size="large"
          class="url-title-input"
        />
      </div>
      <template #footer>
        <ElButton @click="urlDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="handleAddUrl">添加</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.source-uploader {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius-lg);
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
  background: var(--bg-secondary);
}

.upload-zone:hover,
.upload-zone.is-dragover {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

.upload-input-hidden {
  display: none;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-title {
  font-size: 15px;
  color: var(--text-primary);
  margin: 0;
  font-weight: 500;
}

.upload-hint {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.source-list {
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius-md);
  background: var(--bg-primary);
}

.source-list-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  border-radius: var(--border-radius-md) var(--border-radius-md) 0 0;
}

.source-count {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.source-items {
  max-height: 360px;
  overflow-y: auto;
}

.source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  transition: background var(--transition-fast);
}

.source-item:last-child {
  border-bottom: none;
}

.source-item:hover {
  background: var(--bg-secondary);
}

.source-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.source-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.source-details {
  flex: 1;
  min-width: 0;
}

.source-name {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.source-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.source-size {
  font-size: 12px;
  color: var(--text-muted);
}

.source-empty {
  text-align: center;
  padding: 40px 0;
  color: var(--text-muted);
  font-size: 14px;
}

.url-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.url-title-input {
  margin-top: 8px;
}
</style>
