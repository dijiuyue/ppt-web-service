// ==================== 枚举类型 ====================

export type ProjectStatus = 'draft' | 'confirming' | 'processing' | 'completed' | 'failed'

export type PipelineStep =
  | 'init'
  | 'source_processing'
  | 'strategist'
  | 'image_acquisition'
  | 'executor'
  | 'post_processing'
  | 'completed'

export type StepStatus = 'pending' | 'running' | 'completed' | 'failed' | 'waiting_confirmation'

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'waiting_confirmation' | 'cancelled'

export type CanvasFormat = 'ppt169' | 'ppt43' | 'xhs' | 'story'

export type FileType = 'pdf' | 'docx' | 'xlsx' | 'pptx' | 'url' | 'md' | 'txt' | 'html' | 'epub'

export type LLMProvider = 'openai' | 'anthropic' | 'deepseek'

// ==================== 项目相关 ====================

export interface Project {
  id: string
  name: string
  description: string | null
  canvas_format: CanvasFormat
  status: ProjectStatus
  current_step: PipelineStep
  step_status: StepStatus
  llm_provider: LLMProvider
  llm_model: string
  template_path: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  source_files?: SourceFile[]
  design_spec?: DesignSpec
  svg_pages?: SVGPage[]
  pptx_exports?: PPTXExport[]
  pipeline_jobs?: PipelineJob[]
}

export interface CreateProjectRequest {
  name: string
  description?: string
  canvas_format: CanvasFormat
  llm_provider: LLMProvider
  llm_model: string
  template_path?: string
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
  canvas_format?: CanvasFormat
  llm_provider?: LLMProvider
  llm_model?: string
  template_path?: string
}

// ==================== 源文件相关 ====================

export interface SourceFile {
  id: string
  project_id: string
  original_filename: string
  file_type: FileType
  storage_key: string
  storage_backend: string
  file_size: number
  markdown_content: string | null
  markdown_storage_key: string | null
  conversion_status: 'pending' | 'processing' | 'completed' | 'failed'
  conversion_error: string | null
  sort_order: number
  created_at: string
}

export interface UploadSourcesResponse {
  files: SourceFile[]
}

export interface AddUrlSourceRequest {
  url: string
  title?: string
}

// ==================== Design Spec 相关 ====================

export interface ColorScheme {
  primary: string
  secondary: string
  accent: string
  background: string
  text: string
  text_secondary: string
  [key: string]: string
}

export interface Typography {
  title_font: string
  body_font: string
  title_size?: string
  body_size?: string
  fallback_fonts?: string[]
}

export interface DesignSpec {
  id: string
  project_id: string
  confirmation_canvas: string | null
  confirmation_page_count: number | null
  confirmation_audience: string | null
  confirmation_style_mode: string | null
  confirmation_style_descriptor: string | null
  confirmation_color_scheme: ColorScheme | null
  confirmation_icon_approach: string | null
  confirmation_typography: Typography | null
  confirmation_image_approach: string | null
  confirmation_status: 'pending' | 'confirmed'
  confirmed_at: string | null
  spec_content: string | null
  spec_storage_key: string | null
  created_at: string
  updated_at: string
}

export interface EightConfirmationsData {
  confirmation_canvas: string
  confirmation_page_count: number
  confirmation_audience: string
  confirmation_style_mode: 'A' | 'B' | 'C'
  confirmation_style_descriptor: string
  confirmation_color_scheme: ColorScheme
  confirmation_icon_approach: 'A' | 'B' | 'C' | 'D'
  confirmation_typography: Typography
  confirmation_image_approach: 'A' | 'B' | 'C' | 'D' | 'E'
}

// ==================== Pipeline 相关 ====================

export interface PipelineJob {
  id: string
  project_id: string
  step: PipelineStep
  status: JobStatus
  celery_task_id: string | null
  input_data: Record<string, unknown> | null
  output_data: Record<string, unknown> | null
  error_message: string | null
  error_traceback: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface PipelineStatus {
  project_id: string
  current_step: PipelineStep
  step_status: StepStatus
  overall_progress: number
  current_job: PipelineJob | null
  recent_jobs: PipelineJob[]
  can_resume: boolean
  can_cancel: boolean
  can_start: boolean
}

// ==================== SVG 页面相关 ====================

export interface SVGPage {
  id: string
  project_id: string
  page_number: number
  page_name: string
  filename: string
  svg_content: string | null
  svg_storage_key: string | null
  page_rhythm: string | null
  page_layout: string | null
  page_chart: string | null
  quality_check_status: 'pending' | 'passed' | 'failed'
  quality_check_errors: string[] | null
  quality_check_warnings: string[] | null
  speaker_note?: SpeakerNote
  created_at: string
  updated_at: string
}

export interface UpdateSVGPageRequest {
  svg_content?: string
  page_name?: string
  page_rhythm?: string
  page_layout?: string
}

export interface SpeakerNote {
  id: string
  project_id: string
  svg_page_id: string
  page_number: number
  page_name: string
  note_content: string | null
  split_storage_key: string | null
}

// ==================== 导出相关 ====================

export interface PPTXExport {
  id: string
  project_id: string
  export_type: 'native' | 'svg_preview'
  filename: string
  storage_key: string
  storage_backend: string
  file_size: number | null
  transition_effect: string | null
  animation_effect: string | null
  created_at: string
}

export interface CreateExportRequest {
  export_type?: 'native' | 'svg_preview'
  transition_effect?: string
  animation_effect?: string
}

// ==================== 图片资源相关 ====================

export interface ImageResource {
  id: string
  project_id: string
  filename: string
  dimensions: string | null
  ratio: number | null
  purpose: string | null
  image_type: string | null
  acquire_via: 'ai' | 'web' | 'user' | 'placeholder'
  status: 'pending' | 'generated' | 'sourced' | 'existing' | 'needs_manual' | 'placeholder'
  generation_prompt: string | null
  generation_backend: string | null
  search_query: string | null
  source_url: string | null
  attribution_text: string | null
  license_tier: string | null
  storage_key: string | null
  storage_backend: string
  original_storage_key: string | null
  created_at: string
  updated_at: string
}

export interface UpdateImageRequest {
  purpose?: string
  image_type?: string
  acquire_via?: 'ai' | 'web' | 'user' | 'placeholder'
  generation_prompt?: string
  search_query?: string
}

// ==================== WebSocket 消息 ====================

export type WebSocketMessageType =
  | 'status_update'
  | 'job_update'
  | 'step_change'
  | 'error'
  | 'confirmation_needed'
  | 'connected'
  | 'heartbeat'

export interface WebSocketMessage {
  type: WebSocketMessageType
  data: Record<string, unknown>
  timestamp: string
}

// ==================== API 响应类型 ====================

export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface ApiError {
  detail: string
  status_code: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// ==================== 设置相关 ====================

export interface AppSettings {
  llm_api_key: string
  llm_provider: LLMProvider
  llm_model: string
  llm_base_url: string
  default_canvas_format: CanvasFormat
  theme: 'light' | 'dark' | 'auto'
}

// ==================== Pipeline 步骤定义 ====================

export interface PipelineStepDef {
  key: PipelineStep
  title: string
  description: string
  icon: string
}

export const PIPELINE_STEPS: PipelineStepDef[] = [
  { key: 'init', title: '初始化', description: '准备项目环境', icon: 'SetUp' },
  { key: 'source_processing', title: '源文件处理', description: '解析和转换上传的文档', icon: 'Document' },
  { key: 'strategist', title: '策略分析', description: 'AI分析内容并生成设计方案', icon: 'Brain' },
  { key: 'image_acquisition', title: '图片获取', description: '搜索和生成所需图片资源', icon: 'Picture' },
  { key: 'executor', title: '页面生成', description: '生成SVG页面内容', icon: 'MagicStick' },
  { key: 'post_processing', title: '后处理', description: 'SVG优化和PPT导出', icon: 'Tools' },
  { key: 'completed', title: '完成', description: '项目已完成', icon: 'CircleCheck' }
]

// ==================== 模板选项 ====================

export interface TemplateOption {
  id: string
  name: string
  description: string
  preview_image?: string
  path: string
}

export const CANVAS_FORMAT_OPTIONS: { value: CanvasFormat; label: string; description: string; ratio: string }[] = [
  { value: 'ppt169', label: 'PPT 16:9', description: '标准演示文稿格式', ratio: '16:9' },
  { value: 'ppt43', label: 'PPT 4:3', description: '传统演示文稿格式', ratio: '4:3' },
  { value: 'xhs', label: '小红书', description: '社交媒体卡片格式', ratio: '3:4' },
  { value: 'story', label: 'Story', description: '竖屏故事格式', ratio: '9:16' }
]

export const LLM_MODEL_OPTIONS: Record<LLMProvider, { value: string; label: string }[]> = {
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4', label: 'GPT-4' }
  ],
  anthropic: [
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
    { value: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
    { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' }
  ],
  deepseek: [
    { value: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro (推荐)' },
    { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner' },
    { value: 'deepseek-chat', label: 'DeepSeek Chat' }
  ]
}

export const STYLE_MODE_OPTIONS = [
  { value: 'A', label: 'A - 极简商务', description: '简洁、专业、大量留白' },
  { value: 'B', label: 'B - 视觉冲击力', description: '大胆用色、强烈对比' },
  { value: 'C', label: 'C - 温暖人文', description: '柔和色调、亲和力强' }
]

export const ICON_APPROACH_OPTIONS = [
  { value: 'A', label: 'A - 线性图标', description: '简洁线条风格' },
  { value: 'B', label: 'B - 面性图标', description: '填充色块风格' },
  { value: 'C', label: 'C - 双色图标', description: '双色渐变风格' },
  { value: 'D', label: 'D - 插画风格', description: '手绘插画风格' }
]

export const IMAGE_APPROACH_OPTIONS = [
  { value: 'A', label: 'A - AI生成', description: '使用AI生成所有图片' },
  { value: 'B', label: 'B - 网络搜索', description: '从网络搜索图片' },
  { value: 'C', label: 'C - 混合模式', description: 'AI生成+网络搜索' },
  { value: 'D', label: 'D - 用户上传', description: '使用用户上传的图片' },
  { value: 'E', label: 'E - 纯图标', description: '仅使用图标，无图片' }
]
