# PPT Master Web Service - SPEC.md

## 1. 项目概述

将 ppt-master skill (https://github.com/hugohe3/ppt-master) 改造为前后端分离的Web服务，用户可通过Web界面完成PPT生成全流程。

### 1.1 技术栈
- **前端**: Vue 3 + TypeScript + Element Plus + Pinia
- **后端**: FastAPI + SQLAlchemy + Alembic + Celery + Redis
- **数据库**: PostgreSQL 15+
- **对象存储**: MinIO (兼容S3)
- **LLM**: OpenAI API / Anthropic Claude API (服务端配置)
- **容器化**: Docker + Docker Compose

### 1.2 核心Pipeline (与原Skill对应)
```
Step 1: Source Content Processing  →  /api/projects/{id}/upload-sources
Step 2: Project Initialization    →  POST /api/projects
Step 3: Template Option           →  项目配置中的template字段
Step 4: Strategist Phase          →  Celery Task: strategist_phase (BLOCKING - 需用户确认)
Step 5: Image Acquisition         →  Celery Task: image_acquisition
Step 6: Executor Phase            →  Celery Task: executor_phase
Step 7: Post-processing & Export  →  Celery Task: post_processing
```

## 2. 数据库模型 (SQLAlchemy)

### 2.1 projects - 项目主表
```python
class Project(Base):
    __tablename__ = "projects"
    
    id: UUID (PK, default=uuid4)
    name: str (not null)
    description: str (nullable)
    canvas_format: str (default="ppt169", enum: ppt169/ppt43/xhs/story)
    status: ProjectStatus (enum, default="draft")
    # Pipeline状态
    current_step: PipelineStep (enum, default="init")
    step_status: StepStatus (enum, default="pending")  # pending/running/completed/failed/waiting_confirmation
    # 配置
    llm_provider: str (default="openai")  # openai/anthropic
    llm_model: str (default="gpt-4o")
    # 模板配置
    template_path: str (nullable)  # 模板目录路径
    # 时间戳
    created_at: datetime
    updated_at: datetime
    completed_at: datetime (nullable)
    
    # 关系
    source_files: list[SourceFile]
    design_spec: DesignSpec (one-to-one)
    spec_lock: SpecLock (one-to-one)
    image_resources: list[ImageResource]
    svg_pages: list[SVGPage]
    speaker_notes: list[SpeakerNote]
    pptx_exports: list[PPTXExport]
    pipeline_jobs: list[PipelineJob]
```

### 2.2 source_files - 源文件表
```python
class SourceFile(Base):
    __tablename__ = "source_files"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id)
    original_filename: str
    file_type: str (enum: pdf/docx/xlsx/pptx/url/md/txt/html/epub)
    storage_key: str  # MinIO/文件系统路径
    storage_backend: str (default="minio")  # minio/local
    file_size: int (bytes)
    # 转换后的markdown内容
    markdown_content: text (nullable, 转换后填充)
    markdown_storage_key: str (nullable)
    # 转换状态
    conversion_status: str (default="pending")  # pending/processing/completed/failed
    conversion_error: str (nullable)
    # 排序
    sort_order: int (default=0)
    created_at: datetime
```

### 2.3 design_specs - 设计规范表
```python
class DesignSpec(Base):
    __tablename__ = "design_specs"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id, unique)
    
    # Eight Confirmations (用户确认的内容)
    confirmation_canvas: str (nullable)
    confirmation_page_count: int (nullable)
    confirmation_audience: str (nullable)
    confirmation_style_mode: str (nullable)  # A/B/C
    confirmation_style_descriptor: str (nullable)
    confirmation_color_scheme: JSON (nullable)  # {primary, secondary, accent, ...}
    confirmation_icon_approach: str (nullable)  # A/B/C/D
    confirmation_typography: JSON (nullable)  # {title_font, body_font, ...}
    confirmation_image_approach: str (nullable)  # A/B/C/D/E
    
    # 确认状态
    confirmation_status: str (default="pending")  # pending/confirmed
    confirmed_at: datetime (nullable)
    
    # 完整design_spec.md内容
    spec_content: text (nullable)  # 完整的markdown文本
    spec_storage_key: str (nullable)
    
    created_at: datetime
    updated_at: datetime
```

### 2.4 spec_locks - 执行锁表
```python
class SpecLock(Base):
    __tablename__ = "spec_locks"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id, unique)
    
    # 解析后的机器可读数据
    canvas_viewbox: str (nullable)  # "0 0 1280 720"
    canvas_format: str (nullable)
    
    # colors (JSON)
    colors: JSON (nullable)  # {bg, primary, accent, secondary_accent, text, text_secondary, border, ...}
    
    # typography (JSON)
    typography: JSON (nullable)  # {font_family, title_family, body_family, body_size, title_size, ...}
    
    # icons (JSON)
    icons: JSON (nullable)  # {library, brand_library, inventory, stroke_width}
    
    # images (JSON)
    images: JSON (nullable)  # [{name, path, no_crop}, ...]
    
    # page_rhythm (JSON)
    page_rhythm: JSON (nullable)  # {"P01": "anchor", "P02": "dense", ...}
    
    # page_layouts (JSON)
    page_layouts: JSON (nullable)  # {"P01": "01_cover", ...}
    
    # page_charts (JSON)
    page_charts: JSON (nullable)  # {"P05": "bar_chart", ...}
    
    # forbidden (JSON)
    forbidden: JSON (nullable)  # ["rule1", "rule2"]
    
    # 原始文件
    lock_content: text (nullable)  # 原始markdown
    lock_storage_key: str (nullable)
    
    created_at: datetime
    updated_at: datetime
```

### 2.5 image_resources - 图片资源表
```python
class ImageResource(Base):
    __tablename__ = "image_resources"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id)
    
    filename: str
    dimensions: str (nullable)  # "1280x720"
    ratio: float (nullable)
    purpose: str (nullable)
    image_type: str (nullable)  # Background/Photography/Illustration/Diagram/Decorative
    
    # 获取方式
    acquire_via: str (enum: ai/web/user/placeholder)
    status: str (default="pending")  # pending/generated/sourced/existing/needs_manual/placeholder
    
    # AI生成相关
    generation_prompt: text (nullable)
    generation_backend: str (nullable)
    
    # Web搜索相关
    search_query: str (nullable)
    source_url: str (nullable)
    attribution_text: str (nullable)
    license_tier: str (nullable)  # no-attribution/attribution-required
    
    # 存储
    storage_key: str (nullable)
    storage_backend: str (default="minio")
    
    # 用户上传
    original_storage_key: str (nullable)
    
    created_at: datetime
    updated_at: datetime
```

### 2.6 svg_pages - SVG页面表
```python
class SVGPage(Base):
    __tablename__ = "svg_pages"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id)
    
    page_number: int  # 1-based
    page_name: str  # e.g., "cover", "content_1"
    filename: str  # "01_cover.svg"
    
    # SVG内容
    svg_content: text (nullable)  # SVG XML文本
    svg_storage_key: str (nullable)
    
    # 页面属性
    page_rhythm: str (nullable)  # anchor/dense/breathing
    page_layout: str (nullable)  # 模板名
    page_chart: str (nullable)  # 图表类型
    
    # 质量检查
    quality_check_status: str (default="pending")  # pending/passed/failed
    quality_check_errors: JSON (nullable)
    quality_check_warnings: JSON (nullable)
    
    # 关联的speaker note
    speaker_note: SpeakerNote (one-to-one)
    
    created_at: datetime
    updated_at: datetime
```

### 2.7 speaker_notes - 演讲者备注表
```python
class SpeakerNote(Base):
    __tablename__ = "speaker_notes"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id)
    svg_page_id: UUID (FK → svg_pages.id, unique)
    
    page_number: int
    page_name: str
    
    # 备注内容
    note_content: text (nullable)
    
    # 拆分后的单个文件
    split_storage_key: str (nullable)
    
    created_at: datetime
```

### 2.8 pptx_exports - PPT导出表
```python
class PPTXExport(Base):
    __tablename__ = "pptx_exports"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id)
    
    export_type: str (default="native")  # native/svg_preview
    filename: str  # "<project_name>_<timestamp>.pptx"
    storage_key: str (not null)
    storage_backend: str (default="minio")
    file_size: int (nullable)
    
    # 动画配置
    transition_effect: str (nullable)
    animation_effect: str (nullable)
    
    created_at: datetime
```

### 2.9 pipeline_jobs - 流水线作业表
```python
class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"
    
    id: UUID (PK)
    project_id: UUID (FK → projects.id)
    
    step: PipelineStep (enum)  # source_processing/project_init/strategist/image_acquisition/executor/post_processing
    status: JobStatus (enum, default="pending")  # pending/running/completed/failed/waiting_confirmation/cancelled
    
    # Celery任务
    celery_task_id: str (nullable)
    
    # 输入/输出
    input_data: JSON (nullable)
    output_data: JSON (nullable)
    
    # 错误信息
    error_message: str (nullable)
    error_traceback: text (nullable)
    
    # 时间
    started_at: datetime (nullable)
    completed_at: datetime (nullable)
    created_at: datetime
```

### 枚举类型
```python
class ProjectStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMING = "confirming"  # 等待Eight Confirmations确认
    PROCESSING = "processing"  # Pipeline执行中
    COMPLETED = "completed"
    FAILED = "failed"

class PipelineStep(str, Enum):
    INIT = "init"
    SOURCE_PROCESSING = "source_processing"
    STRATEGIST = "strategist"
    IMAGE_ACQUISITION = "image_acquisition"
    EXECUTOR = "executor"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_CONFIRMATION = "waiting_confirmation"
    CANCELLED = "cancelled"
```

## 3. API设计 (FastAPI)

### 3.1 项目API (/api/projects)
```
POST   /api/projects              → 创建项目
GET    /api/projects              → 项目列表(分页)
GET    /api/projects/{id}         → 项目详情
PUT    /api/projects/{id}         → 更新项目
DELETE /api/projects/{id}         → 删除项目
POST   /api/projects/{id}/start   → 启动Pipeline
POST   /api/projects/{id}/cancel  → 取消Pipeline
```

### 3.2 源文件API (/api/projects/{id}/sources)
```
POST   /api/projects/{id}/sources/upload    → 上传源文件(支持多文件)
POST   /api/projects/{id}/sources/url       → 添加URL源
GET    /api/projects/{id}/sources           → 源文件列表
DELETE /api/projects/{id}/sources/{sid}     → 删除源文件
```

### 3.3 Design Spec API (/api/projects/{id}/design-spec)
```
GET    /api/projects/{id}/design-spec              → 获取Design Spec
GET    /api/projects/{id}/design-spec/confirmations  → 获取Eight Confirmations
POST   /api/projects/{id}/design-spec/confirm        → 确认Eight Confirmations
PUT    /api/projects/{id}/design-spec               → 更新Design Spec (高级)
```

### 3.4 Pipeline API (/api/projects/{id}/pipeline)
```
GET    /api/projects/{id}/pipeline/status    → Pipeline状态
GET    /api/projects/{id}/pipeline/jobs      → Job历史
POST   /api/projects/{id}/pipeline/resume    → 从当前步骤恢复
```

### 3.5 SVG页面API (/api/projects/{id}/pages)
```
GET    /api/projects/{id}/pages              → SVG页面列表
GET    /api/projects/{id}/pages/{pid}        → 获取SVG内容
GET    /api/projects/{id}/pages/{pid}/svg    → 获取SVG原始内容(raw)
PUT    /api/projects/{id}/pages/{pid}        → 更新SVG (编辑)
```

### 3.6 PPT导出API (/api/projects/{id}/exports)
```
GET    /api/projects/{id}/exports            → 导出列表
GET    /api/projects/{id}/exports/{eid}      → 下载PPT
POST   /api/projects/{id}/exports            → 重新导出
```

### 3.7 图片资源API (/api/projects/{id}/images)
```
GET    /api/projects/{id}/images             → 图片列表
POST   /api/projects/{id}/images/upload      → 上传图片
PUT    /api/projects/{id}/images/{iid}       → 更新图片配置
```

### 3.8 WebSocket (/ws/projects/{id})
```
WebSocket连接用于实时推送Pipeline状态更新
消息格式: {"type": "status_update", "data": {...}}
消息类型: status_update/job_update/step_change/error/confirmation_needed
```

## 4. 存储抽象层

### 4.1 接口定义
```python
class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key: str, data: bytes | str, content_type: str = "application/octet-stream") -> str: ...
    
    @abstractmethod
    async def get(self, key: str) -> bytes: ...
    
    @abstractmethod
    async def delete(self, key: str) -> None: ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool: ...
    
    @abstractmethod
    def get_url(self, key: str, expires: int = 3600) -> str: ...
    
    @abstractmethod
    def get_public_url(self, key: str) -> str: ...
```

### 4.2 实现
- **MinioStorage**: 生产环境，使用MinIO/S3
- **LocalStorage**: 开发环境，使用本地文件系统
- **StorageManager**: 根据配置自动选择backend

### 4.3 存储路径规范
```
projects/{project_id}/
  sources/{source_id}/{filename}
  sources/{source_id}/converted.md
  images/{image_id}/{filename}
  design_spec.md
  spec_lock.md
  svg_output/{NN}_{page_name}.svg
  svg_final/{NN}_{page_name}.svg
  notes/total.md
  notes/{NN}_{page_name}.md
  exports/{export_id}/{filename}
  templates/  (模板文件)
```

## 5. LangChain Pipeline工作流编排

### 5.1 架构设计
使用Celery + LangChain实现异步Pipeline:

```
                   ┌─────────────────────────────────────────┐
                   │         Pipeline Orchestrator           │
                   │     (LangChain State Machine)           │
                   └──────────────┬──────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │  Celery Worker  │ │  Celery Worker  │ │  Celery Worker  │
    │  (LLM Tasks)    │ │  (Script Tasks) │ │  (File Tasks)   │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 5.2 State Machine
```
[init] → [source_processing] → [strategist] → [WAIT_CONFIRMATION] → [image_acquisition] → [executor] → [post_processing] → [completed]
                                                              ↘
                                                               [image_acquisition SKIP] → [executor]
```

### 5.3 LangChain设计
```python
class PPTPipelineState(TypedDict):
    project_id: str
    current_step: str
    step_status: str
    design_spec: str | None
    spec_lock: str | None
    confirmations: dict | None
    confirmation_status: str
    errors: list[str]

class PPTMasterPipeline:
    """LangChain驱动的PPT生成Pipeline"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """构建StateGraph工作流"""
        builder = StateGraph(PPTPipelineState)
        
        # 添加节点
        builder.add_node("source_processing", self._source_processing_node)
        builder.add_node("strategist", self._strategist_node)
        builder.add_node("wait_confirmation", self._wait_confirmation_node)
        builder.add_node("image_acquisition", self._image_acquisition_node)
        builder.add_node("executor", self._executor_node)
        builder.add_node("post_processing", self._post_processing_node)
        
        # 添加边
        builder.set_entry_point("source_processing")
        builder.add_edge("source_processing", "strategist")
        builder.add_edge("strategist", "wait_confirmation")
        builder.add_conditional_edges(
            "wait_confirmation",
            self._check_confirmation,
            {"confirmed": "image_acquisition", "waiting": END}
        )
        builder.add_conditional_edges(
            "image_acquisition",
            self._check_images,
            {"needed": "executor", "skip": "executor"}
        )
        builder.add_edge("executor", "post_processing")
        builder.add_edge("post_processing", END)
        
        return builder.compile()
    
    async def _strategist_node(self, state: PPTPipelineState) -> PPTPipelineState:
        """Strategist步骤: 生成Eight Confirmations和Design Spec"""
        # 1. 读取source files
        # 2. 构建prompt (包含strategist.md的内容)
        # 3. 调用LLM生成Eight Confirmations
        # 4. 保存到DB，设置WAITING_CONFIRMATION状态
        # 5. 通过WebSocket通知前端
        ...
    
    async def _executor_node(self, state: PPTPipelineState) -> PPTPipelineState:
        """Executor步骤: 生成SVG页面"""
        # 1. 读取spec_lock和design_spec
        # 2. 逐页生成SVG (sequential, one at a time)
        # 3. 每页保存到DB
        # 4. 质量检查
        # 5. 生成speaker notes
        ...
```

### 5.4 Celery任务定义
```python
@app.task(bind=True, max_retries=3)
def run_pipeline_step(self, project_id: str, step: str, input_data: dict):
    """执行Pipeline单个步骤"""
    ...

@app.task
def process_source_file(source_id: str):
    """转换源文件为markdown"""
    ...

@app.task
def generate_images(project_id: str, image_ids: list[str]):
    """批量生成图片"""
    ...

@app.task
def run_svg_quality_check(project_id: str):
    """SVG质量检查"""
    ...

@app.task
def export_pptx(project_id: str, export_options: dict):
    """导出PPT"""
    ...
```

## 6. 前端设计

### 6.1 页面路由
```
/                          → 首页/登录
/projects                  → 项目列表
/projects/new              → 创建项目
/projects/:id              → 项目详情/ Pipeline状态
/projects/:id/confirm      → Eight Confirmations确认
/projects/:id/editor       → SVG页面编辑器
/projects/:id/preview      → PPT预览
/projects/:id/exports      → 导出管理
/settings                  → 系统设置
```

### 6.2 核心组件
- **PipelineStatus**: Pipeline状态可视化 (步骤条)
- **EightConfirmations**: 8项确认表单
- **SVGPreview**: SVG页面预览 (内嵌)
- **ProjectCard**: 项目卡片
- **SourceUploader**: 源文件上传组件
- **ImageManager**: 图片资源管理
- **ExportList**: 导出文件列表

### 6.3 状态管理 (Pinia)
```typescript
// stores/project.ts
export const useProjectStore = defineStore('project', {
  state: () => ({
    projects: [],
    currentProject: null,
    pipelineStatus: null,
    wsConnection: null,
  }),
  actions: {
    async fetchProjects() { ... },
    async createProject(data) { ... },
    async startPipeline(projectId) { ... },
    async confirmEightConfirmations(projectId, data) { ... },
    connectWebSocket(projectId) { ... },
  }
})
```

## 7. 与原Skill脚本的集成

### 7.1 脚本包装器
原skill脚本通过subprocess调用，输入输出通过文件系统。Web服务中:
1. 从DB读取内容 → 写入临时文件
2. 调用原脚本 (subprocess)
3. 读取输出文件 → 存入DB和对象存储
4. 清理临时文件

```python
class ScriptRunner:
    """原skill脚本的包装器"""
    
    SKILL_DIR = "/app/ppt-master/skills/ppt-master"
    
    async def run_pdf_to_md(self, pdf_path: str) -> str:
        """PDF转Markdown"""
        cmd = [sys.executable, f"{self.SKILL_DIR}/scripts/source_to_md/pdf_to_md.py", pdf_path]
        result = await asyncio.create_subprocess_exec(*cmd, ...)
        ...
    
    async def run_project_manager_init(self, name: str, format: str) -> str:
        """初始化项目"""
        cmd = [sys.executable, f"{self.SKILL_DIR}/scripts/project_manager.py", "init", name, "--format", format]
        ...
    
    async def run_svg_quality_checker(self, project_path: str) -> dict:
        """SVG质量检查"""
        cmd = [sys.executable, f"{self.SKILL_DIR}/scripts/svg_quality_checker.py", project_path]
        ...
    
    async def run_finalize_svg(self, project_path: str) -> None:
        """SVG后处理"""
        cmd = [sys.executable, f"{self.SKILL_DIR}/scripts/finalize_svg.py", project_path]
        ...
    
    async def run_svg_to_pptx(self, project_path: str, options: dict) -> list[str]:
        """导出PPTX"""
        cmd = [sys.executable, f"{self.SKILL_DIR}/scripts/svg_to_pptx.py", project_path]
        ...
```

### 7.2 临时工作目录管理
```python
class ProjectWorkspace:
    """管理项目的临时工作目录"""
    
    async def __aenter__(self):
        """创建临时目录，从DB/对象存储同步文件"""
        self.temp_dir = tempfile.mkdtemp(prefix=f"ppt_{self.project_id}_")
        await self._sync_from_storage()
        return self.temp_dir
    
    async def __aexit__(self, *args):
        """同步结果到DB/对象存储，清理临时目录"""
        await self._sync_to_storage()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

## 8. Docker配置

### 8.1 docker-compose.yml
```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: pptmaster
      POSTGRES_USER: pptmaster
      POSTGRES_PASSWORD: pptmaster
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://pptmaster:pptmaster@db:5432/pptmaster
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ppt_master_skill:/app/ppt-master:ro

  celery_worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://pptmaster:pptmaster@db:5432/pptmaster
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ppt_master_skill:/app/ppt-master:ro

  frontend:
    build: ./frontend
    ports:
      - "80:80"

volumes:
  postgres_data:
  minio_data:
  ppt_master_skill:
```

## 9. 环境配置

### 9.1 后端环境变量 (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=pptmaster

# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o

# PPT Master Skill Path
PPT_MASTER_SKILL_DIR=/app/ppt-master/skills/ppt-master

# App
DEBUG=true
LOG_LEVEL=info
```

## 10. 开发顺序

1. **Phase 1**: 数据库模型 + 存储抽象层 + 基础API
2. **Phase 2**: LangChain Pipeline框架 + Celery集成
3. **Phase 3**: 与原skill脚本集成
4. **Phase 4**: 前端基础框架 + 项目列表/创建
5. **Phase 5**: 前端Eight Confirmations + Pipeline状态
6. **Phase 6**: 前端SVG预览 + PPT下载
7. **Phase 7**: Docker配置 + 部署
