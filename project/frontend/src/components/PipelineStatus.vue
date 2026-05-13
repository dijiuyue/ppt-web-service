<script setup lang="ts">
import { computed } from 'vue'
import { ElSteps, ElStep, ElTag, ElProgress, ElEmpty, ElIcon } from 'element-plus'
import {
  SetUp,
  Document,
  Brain,
  Picture,
  MagicStick,
  Tools,
  CircleCheck,
  Loading,
  WarningFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import type { PipelineStatus, StepStatus } from '@/types'

const props = defineProps<{
  status: PipelineStatus | null
}>()

const stepIcons: Record<string, any> = {
  SetUp,
  Document,
  Brain,
  Picture,
  MagicStick,
  Tools,
  CircleCheck
}

const stepList = [
  { key: 'init', title: '初始化', description: '准备项目环境', icon: 'SetUp' },
  { key: 'source_processing', title: '源文件处理', description: '解析和转换文档', icon: 'Document' },
  { key: 'strategist', title: '策略分析', description: 'AI生成设计方案', icon: 'Brain' },
  { key: 'image_acquisition', title: '图片获取', description: '搜索和生成图片', icon: 'Picture' },
  { key: 'executor', title: '页面生成', description: '生成SVG页面', icon: 'MagicStick' },
  { key: 'post_processing', title: '后处理', description: '优化和导出', icon: 'Tools' },
  { key: 'completed', title: '完成', description: '项目已完成', icon: 'CircleCheck' }
]

const activeStep = computed(() => {
  if (!props.status) return -1
  return stepList.findIndex((s) => s.key === props.status?.current_step)
})

const currentStepStatus = computed((): StepStatus => {
  if (!props.status) return 'pending'
  return props.status.step_status
})

const stepStatusMap = computed(() => {
  const map: Record<number, '' | 'wait' | 'process' | 'finish' | 'error'> = {}
  const active = activeStep.value
  const curStatus = currentStepStatus.value

  stepList.forEach((_, index) => {
    if (index < active) {
      map[index] = 'finish'
    } else if (index === active) {
      if (curStatus === 'running') {
        map[index] = 'process'
      } else if (curStatus === 'completed') {
        map[index] = 'finish'
      } else if (curStatus === 'failed') {
        map[index] = 'error'
      } else if (curStatus === 'waiting_confirmation') {
        map[index] = 'process'
      } else {
        map[index] = 'wait'
      }
    } else {
      map[index] = 'wait'
    }
  })

  return map
})

const getStatusIcon = (status: StepStatus) => {
  switch (status) {
    case 'running':
      return Loading
    case 'completed':
      return CircleCheck
    case 'failed':
      return CircleCloseFilled
    case 'waiting_confirmation':
      return WarningFilled
    default:
      return undefined
  }
}

const getStatusText = (status: StepStatus): string => {
  switch (status) {
    case 'pending':
      return '等待中'
    case 'running':
      return '进行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    case 'waiting_confirmation':
      return '等待确认'
    default:
      return '未知'
  }
}

const getStatusType = (status: StepStatus) => {
  switch (status) {
    case 'pending':
      return 'info'
    case 'running':
      return 'primary'
    case 'completed':
      return 'success'
    case 'failed':
      return 'danger'
    case 'waiting_confirmation':
      return 'warning'
    default:
      return 'info'
  }
}
</script>

<template>
  <div class="pipeline-status">
    <div v-if="!status" class="pipeline-empty">
      <ElEmpty description="暂无Pipeline状态" />
    </div>

    <div v-else class="pipeline-content">
      <!-- 当前状态概览 -->
      <div class="pipeline-overview">
        <div class="pipeline-overview-left">
          <h4 class="pipeline-step-name">
            {{ stepList[activeStep]?.title || '初始化' }}
          </h4>
          <p class="pipeline-step-desc">
            {{ stepList[activeStep]?.description || '' }}
          </p>
        </div>
        <div class="pipeline-overview-right">
          <ElTag
            :type="getStatusType(currentStepStatus)"
            effect="dark"
            size="large"
            class="status-tag-large"
          >
            <ElIcon v-if="currentStepStatus === 'running'" class="is-loading">
              <Loading />
            </ElIcon>
            <ElIcon v-else-if="getStatusIcon(currentStepStatus)">
              <component :is="getStatusIcon(currentStepStatus)" />
            </ElIcon>
            {{ getStatusText(currentStepStatus) }}
          </ElTag>
        </div>
      </div>

      <!-- 总体进度 -->
      <div class="pipeline-progress">
        <div class="progress-label">
          <span>总体进度</span>
          <span class="progress-value">{{ status.overall_progress }}%</span>
        </div>
        <ElProgress
          :percentage="status.overall_progress"
          :status="currentStepStatus === 'failed' ? 'exception' : undefined"
          :stroke-width="12"
          class="overall-progress-bar"
        />
      </div>

      <!-- 当前Job信息 -->
      <div v-if="status.current_job" class="current-job-info">
        <div class="job-detail">
          <span class="job-label">当前任务:</span>
          <span class="job-value">{{ status.current_job.step }}</span>
        </div>
        <div v-if="status.current_job.error_message" class="job-error">
          <ElIcon><WarningFilled /></ElIcon>
          {{ status.current_job.error_message }}
        </div>
      </div>

      <!-- 步骤条 -->
      <div class="pipeline-steps-container">
        <ElSteps
          :active="activeStep"
          finish-status="success"
          align-center
          class="pipeline-steps"
        >
          <ElStep
            v-for="(step, index) in stepList"
            :key="step.key"
            :status="stepStatusMap[index]"
          >
            <template #title>
              <span class="step-title">{{ step.title }}</span>
            </template>
            <template #icon>
              <div class="step-icon-wrapper">
                <ElIcon :size="20">
                  <component :is="stepIcons[step.icon]" />
                </ElIcon>
              </div>
            </template>
          </ElStep>
        </ElSteps>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pipeline-status {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}

.pipeline-overview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.pipeline-overview-left {
  flex: 1;
}

.pipeline-step-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.pipeline-step-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.status-tag-large {
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 500;
}

.is-loading {
  animation: rotate 1s linear infinite;
  margin-right: 4px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.pipeline-progress {
  margin-bottom: 20px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.progress-value {
  font-weight: 600;
  color: var(--primary-color);
}

.overall-progress-bar {
  border-radius: 6px;
}

.current-job-info {
  background: var(--bg-secondary);
  border-radius: var(--border-radius-sm);
  padding: 12px 16px;
  margin-bottom: 20px;
}

.job-detail {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.job-label {
  color: var(--text-secondary);
}

.job-value {
  color: var(--text-primary);
  font-weight: 500;
}

.job-error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px;
  background: #fff1f0;
  border-radius: 6px;
  color: var(--danger-color);
  font-size: 12px;
}

.pipeline-steps-container {
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  overflow-x: auto;
}

.pipeline-steps :deep(.el-step__title) {
  font-size: 12px;
  font-weight: 500;
}

.pipeline-steps :deep(.el-step__icon) {
  width: 36px;
  height: 36px;
}

.step-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.pipeline-empty {
  padding: 40px 0;
}

@media (max-width: 768px) {
  .pipeline-status {
    padding: 16px;
  }

  .pipeline-overview {
    flex-direction: column;
    align-items: flex-start;
  }

  .pipeline-steps :deep(.el-step__title) {
    font-size: 11px;
  }
}
</style>
