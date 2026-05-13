import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Project,
  PipelineStatus,
  PipelineJob,
  DesignSpec,
  EightConfirmationsData,
  CreateProjectRequest,
  UpdateProjectRequest,
  WebSocketMessage,
  SourceFile,
  SVGPage,
  PPTXExport
} from '@/types'
import {
  getProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  startPipeline,
  cancelPipeline
} from '@/api/projects'
import {
  getDesignSpec,
  getConfirmations,
  confirmEightConfirmations
} from '@/api/designSpec'
import { getPipelineStatus, getPipelineJobs, resumePipeline } from '@/api/pipeline'
import { getSources } from '@/api/sources'
import { getSVGPages } from '@/api/svgPages'
import { getExports } from '@/api/exports'
import { ElMessage } from 'element-plus'

export const useProjectStore = defineStore('project', () => {
  // ==================== State ====================
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const pipelineStatus = ref<PipelineStatus | null>(null)
  const pipelineJobs = ref<PipelineJob[]>([])
  const designSpec = ref<DesignSpec | null>(null)
  const sourceFiles = ref<SourceFile[]>([])
  const svgPages = ref<SVGPage[]>([])
  const exports = ref<PPTXExport[]>([])
  const wsConnection = ref<WebSocket | null>(null)
  const isLoading = ref(false)
  const isConnecting = ref(false)
  const connectionError = ref<string | null>(null)

  // ==================== Getters ====================
  const projectById = computed(() => {
    return (id: string) => projects.value.find((p) => p.id === id) || null
  })

  const currentStepIndex = computed(() => {
    if (!pipelineStatus.value) return -1
    const steps = ['init', 'source_processing', 'strategist', 'image_acquisition', 'executor', 'post_processing', 'completed']
    return steps.indexOf(pipelineStatus.value.current_step)
  })

  const isPipelineRunning = computed(() => {
    return pipelineStatus.value?.step_status === 'running'
  })

  const isWaitingConfirmation = computed(() => {
    return pipelineStatus.value?.step_status === 'waiting_confirmation'
  })

  const canStartPipeline = computed(() => {
    return currentProject.value?.status === 'draft' && !isPipelineRunning.value
  })

  const hasConfirmations = computed(() => {
    return designSpec.value?.confirmation_status === 'confirmed'
  })

  // ==================== Actions: Projects ====================

  async function fetchProjects(page = 1, pageSize = 20) {
    isLoading.value = true
    try {
      const response = await getProjects(page, pageSize)
      projects.value = response.items || []
      return response
    } finally {
      isLoading.value = false
    }
  }

  async function fetchProject(id: string) {
    isLoading.value = true
    try {
      const project = await getProject(id)
      currentProject.value = project
      // 同时获取相关数据
      if (project.source_files) sourceFiles.value = project.source_files
      if (project.design_spec) designSpec.value = project.design_spec
      if (project.svg_pages) svgPages.value = project.svg_pages
      if (project.pptx_exports) exports.value = project.pptx_exports
      return project
    } finally {
      isLoading.value = false
    }
  }

  async function createNewProject(data: CreateProjectRequest) {
    isLoading.value = true
    try {
      const project = await createProject(data)
      projects.value.unshift(project)
      currentProject.value = project
      ElMessage.success('项目创建成功')
      return project
    } finally {
      isLoading.value = false
    }
  }

  async function updateProjectById(id: string, data: UpdateProjectRequest) {
    isLoading.value = true
    try {
      const project = await updateProject(id, data)
      const index = projects.value.findIndex((p) => p.id === id)
      if (index !== -1) projects.value[index] = project
      if (currentProject.value?.id === id) currentProject.value = project
      ElMessage.success('项目更新成功')
      return project
    } finally {
      isLoading.value = false
    }
  }

  async function deleteProjectById(id: string) {
    isLoading.value = true
    try {
      await deleteProject(id)
      projects.value = projects.value.filter((p) => p.id !== id)
      if (currentProject.value?.id === id) currentProject.value = null
      ElMessage.success('项目已删除')
    } finally {
      isLoading.value = false
    }
  }

  // ==================== Actions: Pipeline ====================

  async function fetchPipelineStatus(projectId: string) {
    try {
      const status = await getPipelineStatus(projectId)
      pipelineStatus.value = status
      return status
    } catch {
      // 忽略错误，由拦截器处理
      return null
    }
  }

  async function fetchPipelineJobs(projectId: string) {
    try {
      const jobs = await getPipelineJobs(projectId)
      pipelineJobs.value = jobs
      return jobs
    } catch {
      return []
    }
  }

  async function startProjectPipeline(projectId: string) {
    isLoading.value = true
    try {
      const result = await startPipeline(projectId)
      ElMessage.success('Pipeline 已启动')
      await fetchPipelineStatus(projectId)
      return result
    } finally {
      isLoading.value = false
    }
  }

  async function cancelProjectPipeline(projectId: string) {
    isLoading.value = true
    try {
      await cancelPipeline(projectId)
      ElMessage.info('Pipeline 已取消')
      await fetchPipelineStatus(projectId)
    } finally {
      isLoading.value = false
    }
  }

  async function resumeProjectPipeline(projectId: string) {
    isLoading.value = true
    try {
      await resumePipeline(projectId)
      ElMessage.success('Pipeline 已恢复')
      await fetchPipelineStatus(projectId)
    } finally {
      isLoading.value = false
    }
  }

  // ==================== Actions: Design Spec ====================

  async function fetchDesignSpec(projectId: string) {
    try {
      const spec = await getDesignSpec(projectId)
      designSpec.value = spec
      return spec
    } catch {
      return null
    }
  }

  async function fetchConfirmations(projectId: string) {
    try {
      const spec = await getConfirmations(projectId)
      designSpec.value = spec
      return spec
    } catch {
      return null
    }
  }

  async function submitConfirmations(projectId: string, data: EightConfirmationsData) {
    isLoading.value = true
    try {
      const spec = await confirmEightConfirmations(projectId, data)
      designSpec.value = spec
      if (currentProject.value) {
        currentProject.value.status = 'processing'
      }
      ElMessage.success('确认已提交，Pipeline 继续执行')
      return spec
    } finally {
      isLoading.value = false
    }
  }

  // ==================== Actions: Sources ====================

  async function fetchSources(projectId: string) {
    try {
      const files = await getSources(projectId)
      sourceFiles.value = files
      return files
    } catch {
      return []
    }
  }

  // ==================== Actions: SVG Pages ====================

  async function fetchSVGPages(projectId: string) {
    try {
      const pages = await getSVGPages(projectId)
      svgPages.value = pages
      return pages
    } catch {
      return []
    }
  }

  // ==================== Actions: Exports ====================

  async function fetchExports(projectId: string) {
    try {
      const list = await getExports(projectId)
      exports.value = list
      return list
    } catch {
      return []
    }
  }

  // ==================== Actions: WebSocket ====================

  function connectWebSocket(projectId: string) {
    if (wsConnection.value?.readyState === WebSocket.OPEN) {
      if (wsConnection.value.url.includes(projectId)) return
      wsConnection.value.close()
    }

    isConnecting.value = true
    connectionError.value = null

    const wsUrl = `ws://${window.location.host}/ws/projects/${projectId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      isConnecting.value = false
      connectionError.value = null
      console.log('WebSocket 已连接:', projectId)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage
        handleWebSocketMessage(message)
      } catch (err) {
        console.error('WebSocket 消息解析失败:', err)
      }
    }

    ws.onerror = () => {
      isConnecting.value = false
      connectionError.value = 'WebSocket 连接失败'
    }

    ws.onclose = () => {
      isConnecting.value = false
      wsConnection.value = null
    }

    wsConnection.value = ws
  }

  function disconnectWebSocket() {
    if (wsConnection.value) {
      wsConnection.value.close()
      wsConnection.value = null
    }
  }

  function handleWebSocketMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'status_update':
        if (message.data) {
          pipelineStatus.value = message.data as unknown as PipelineStatus
        }
        break
      case 'job_update':
        if (message.data) {
          const job = message.data as unknown as PipelineJob
          const index = pipelineJobs.value.findIndex((j) => j.id === job.id)
          if (index !== -1) {
            pipelineJobs.value[index] = job
          } else {
            pipelineJobs.value.unshift(job)
          }
        }
        break
      case 'step_change':
        if (message.data && pipelineStatus.value) {
          pipelineStatus.value.current_step = (message.data as { step: string }).step as PipelineStatus['current_step']
          pipelineStatus.value.step_status = (message.data as { status: string }).status as PipelineStatus['step_status']
        }
        break
      case 'error':
        ElMessage.error((message.data as { message: string }).message || 'Pipeline 发生错误')
        break
      case 'confirmation_needed':
        if (currentProject.value) {
          currentProject.value.status = 'confirming'
        }
        ElMessage.info('需要确认 Eight Confirmations')
        break
    }
  }

  // ==================== Cleanup ====================

  function resetState() {
    currentProject.value = null
    pipelineStatus.value = null
    pipelineJobs.value = []
    designSpec.value = null
    sourceFiles.value = []
    svgPages.value = []
    exports.value = []
    disconnectWebSocket()
  }

  return {
    // State
    projects,
    currentProject,
    pipelineStatus,
    pipelineJobs,
    designSpec,
    sourceFiles,
    svgPages,
    exports,
    wsConnection,
    isLoading,
    isConnecting,
    connectionError,
    // Getters
    projectById,
    currentStepIndex,
    isPipelineRunning,
    isWaitingConfirmation,
    canStartPipeline,
    hasConfirmations,
    // Actions: Projects
    fetchProjects,
    fetchProject,
    createNewProject,
    updateProjectById,
    deleteProjectById,
    // Actions: Pipeline
    fetchPipelineStatus,
    fetchPipelineJobs,
    startProjectPipeline,
    cancelProjectPipeline,
    resumeProjectPipeline,
    // Actions: Design Spec
    fetchDesignSpec,
    fetchConfirmations,
    submitConfirmations,
    // Actions: Sources
    fetchSources,
    // Actions: SVG Pages
    fetchSVGPages,
    // Actions: Exports
    fetchExports,
    // Actions: WebSocket
    connectWebSocket,
    disconnectWebSocket,
    // Cleanup
    resetState
  }
})
