<script setup lang="ts">
import { computed } from 'vue'
import { ElCard, ElTag, ElProgress, ElButton, ElIcon, ElDropdown, ElDropdownMenu, ElDropdownItem } from 'element-plus'
import {
  MoreFilled,
  Delete,
  Edit,
  View,
  VideoPlay,
  DocumentChecked
} from '@element-plus/icons-vue'
import type { Project } from '@/types'

const props = defineProps<{
  project: Project
}>()

const emit = defineEmits<{
  (e: 'click', id: string): void
  (e: 'start', id: string): void
  (e: 'delete', id: string): void
  (e: 'edit', id: string): void
}>()

const statusConfig = computed(() => {
  switch (props.project.status) {
    case 'draft':
      return { type: 'info' as const, label: '草稿', class: 'status-tag--draft' }
    case 'confirming':
      return { type: 'warning' as const, label: '待确认', class: 'status-tag--confirming' }
    case 'processing':
      return { type: 'primary' as const, label: '进行中', class: 'status-tag--processing' }
    case 'completed':
      return { type: 'success' as const, label: '已完成', class: 'status-tag--completed' }
    case 'failed':
      return { type: 'danger' as const, label: '失败', class: 'status-tag--failed' }
    default:
      return { type: 'info' as const, label: '未知', class: '' }
  }
})

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const handleCardClick = () => {
  emit('click', props.project.id)
}

const handleCommand = (command: string) => {
  switch (command) {
    case 'start':
      emit('start', props.project.id)
      break
    case 'edit':
      emit('edit', props.project.id)
      break
    case 'delete':
      emit('delete', props.project.id)
      break
  }
}

const canvasFormatLabel = computed(() => {
  const formats: Record<string, string> = {
    ppt169: '16:9',
    ppt43: '4:3',
    xhs: '小红书',
    story: 'Story'
  }
  return formats[props.project.canvas_format] || props.project.canvas_format
})

const progressPercent = computed(() => {
  const stepMap: Record<string, number> = {
    init: 0,
    source_processing: 15,
    strategist: 30,
    image_acquisition: 50,
    executor: 70,
    post_processing: 90,
    completed: 100
  }
  return stepMap[props.project.current_step] || 0
})
</script>

<template>
  <ElCard
    class="project-card card-hover"
    shadow="hover"
    @click="handleCardClick"
  >
    <div class="card-content">
      <!-- 头部 -->
      <div class="card-header-row">
        <div class="card-title-section">
          <h4 class="project-name">{{ project.name }}</h4>
          <p v-if="project.description" class="project-description">
            {{ project.description }}
          </p>
        </div>
        <div class="card-actions">
          <ElTag :type="statusConfig.type" size="small" effect="light" class="status-badge">
            {{ statusConfig.label }}
          </ElTag>
          <ElDropdown trigger="click" @command="handleCommand" @click.stop>
            <ElButton link type="info" size="small">
              <ElIcon><MoreFilled /></ElIcon>
            </ElButton>
            <template #dropdown>
              <ElDropdownMenu>
                <ElDropdownItem command="start" :disabled="project.status === 'processing'">
                  <ElIcon><VideoPlay /></ElIcon> 启动 Pipeline
                </ElDropdownItem>
                <ElDropdownItem command="edit">
                  <ElIcon><Edit /></ElIcon> 编辑
                </ElDropdownItem>
                <ElDropdownItem command="delete" divided>
                  <ElIcon><Delete /></ElIcon> 删除
                </ElDropdownItem>
              </ElDropdownMenu>
            </template>
          </ElDropdown>
        </div>
      </div>

      <!-- 元信息 -->
      <div class="card-meta">
        <span class="meta-item">
          <ElIcon><DocumentChecked /></ElIcon>
          {{ canvasFormatLabel }}
        </span>
        <span class="meta-item">{{ project.llm_model }}</span>
        <span class="meta-item">{{ formatDate(project.created_at) }}</span>
      </div>

      <!-- 进度条 -->
      <div v-if="project.status !== 'draft'" class="card-progress">
        <ElProgress
          :percentage="progressPercent"
          :status="project.status === 'failed' ? 'exception' : undefined"
          :stroke-width="6"
          :show-text="true"
        />
      </div>

      <!-- 底部操作 -->
      <div class="card-footer">
        <ElButton
          v-if="project.status === 'draft'"
          type="primary"
          size="small"
          @click.stop="emit('start', project.id)"
        >
          <ElIcon><VideoPlay /></ElIcon>
          启动
        </ElButton>
        <ElButton
          v-if="project.status === 'confirming'"
          type="warning"
          size="small"
          @click.stop="handleCardClick"
        >
          <ElIcon><DocumentChecked /></ElIcon>
          去确认
        </ElButton>
        <ElButton v-else type="info" size="small" link @click.stop="handleCardClick">
          <ElIcon><View /></ElIcon>
          查看详情
        </ElButton>
      </div>
    </div>
  </ElCard>
</template>

<style scoped>
.project-card {
  cursor: pointer;
  transition: all var(--transition-base);
}

.project-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg) !important;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.card-title-section {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 4px 0 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.status-badge {
  font-size: 11px;
  font-weight: 500;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-progress {
  margin-top: 4px;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}
</style>
