# PPT Master Web Service - 开发文档

> 面向开发者的技术文档，包含开发环境搭建、代码结构说明、功能扩展指南和调试技巧。

---

## 目录

- [开发环境搭建](#开发环境搭建)
- [代码结构](#代码结构)
- [添加新功能](#添加新功能)
- [测试指南](#测试指南)
- [调试技巧](#调试技巧)

---

## 开发环境搭建

### 方式一：Docker Compose 开发模式（推荐）

使用Docker Compose启动所有依赖服务，在本地运行前后端代码。

#### 1. 启动依赖服务

```bash
# 仅启动数据库、Redis、MinIO（不启动应用本身）
docker-compose -f docker-compose.dev.yml up -d db redis minio

# 或使用完整compose但停止backend和frontend
docker-compose up -d
docker-compose stop backend celery_worker frontend
```

#### 2. 后端开发环境

```bash
# 进入后端目录
cd backend

# 创建Python虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或: venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 设置环境变量
export DATABASE_URL="postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster"
export REDIS_URL="redis://localhost:6379/0"
export MINIO_ENDPOINT="localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
export OPENAI_API_KEY="sk-your-key"

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. 前端开发环境

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 前端将运行在 http://localhost:5173
# API请求会自动代理到 http://localhost:8000
```

#### 4. 启动Celery Worker

```bash
# 在新终端中
cd backend
source venv/bin/activate

celery -A app.celery_app worker --loglevel=info --concurrency=2

# 如果需要监控任务（可选）
# 启动Flower监控界面
celery -A app.celery_app flower --port=5555
```

### 方式二：全本地开发

#### 系统要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- MinIO (可选，可用本地存储代替)

#### 安装PostgreSQL

**macOS:**

```bash
brew install postgresql@15
brew services start postgresql@15

# 创建数据库和用户
psql postgres -c "CREATE USER pptmaster WITH PASSWORD 'pptmaster';"
psql postgres -c "CREATE DATABASE pptmaster OWNER pptmaster;"
```

**Ubuntu:**

```bash
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-contrib
sudo service postgresql start

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER pptmaster WITH PASSWORD 'pptmaster';"
sudo -u postgres psql -c "CREATE DATABASE pptmaster OWNER pptmaster;"
```

#### 安装Redis

**macOS:**

```bash
brew install redis
brew services start redis
```

**Ubuntu:**

```bash
sudo apt-get install redis-server
sudo service redis-server start
```

#### 安装MinIO（可选）

```bash
# macOS
brew install minio
mkdir -p ~/minio/data
minio server ~/minio/data --console-address :9001

# Linux
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
mkdir -p ~/minio/data
./minio server ~/minio/data --console-address :9001
```

### 方式三：VS Code Dev Container

项目支持VS Code Dev Container，一键启动完整的开发环境。

#### 前置要求

- [VS Code](https://code.visualstudio.com/)
- [Dev Containers扩展](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- Docker Desktop

#### 使用方法

1. 在VS Code中打开项目
2. 按 `F1` → 输入 `Dev Containers: Reopen in Container`
3. 等待容器构建完成
4. 开发环境已准备就绪！

### 环境变量配置（开发）

创建 `backend/.env` 文件：

```env
# === Database ===
DATABASE_URL=postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === MinIO (可选，开发环境可用local) ===
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./data/storage
# 或 MinIO:
# STORAGE_BACKEND=minio
# MINIO_ENDPOINT=localhost:9000
# MINIO_ACCESS_KEY=minioadmin
# MINIO_SECRET_KEY=minioadmin
# MINIO_BUCKET=pptmaster
# MINIO_SECURE=false

# === LLM ===
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o

# === PPT Master Skill ===
PPT_MASTER_SKILL_DIR=./ppt-master/skills/ppt-master

# === App ===
DEBUG=true
LOG_LEVEL=debug
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 验证开发环境

```bash
# 1. 检查后端
curl http://localhost:8000/api/health
# 预期: {"status": "ok"}

# 2. 检查API文档
curl http://localhost:8000/api/openapi.json | head -20

# 3. 检查前端
curl http://localhost:5173 | head -20

# 4. 检查Celery
celery -A app.celery_app inspect ping

# 5. 检查数据库
docker-compose exec db psql -U pptmaster -d pptmaster -c "SELECT COUNT(*) FROM projects;"

# 6. 检查Redis
docker-compose exec redis redis-cli ping
# 预期: PONG
```

---

## 代码结构

### 后端目录详解

```
backend/
├── alembic/                        # 数据库迁移
│   ├── versions/                   # 迁移脚本目录
│   │   ├── 001_initial_migration.py
│   │   ├── 002_add_speaker_notes.py
│   │   └── 003_add_pipeline_jobs.py
│   ├── env.py                      # Alembic环境配置
│   └── script.py.mako              # 迁移脚本模板
│
├── app/                            # 主应用目录
│   ├── __init__.py
│   ├── main.py                     # FastAPI入口文件
│   │                               # - 创建FastAPI实例
│   │                               # - 注册中间件
│   │                               # - 挂载路由
│   │                               # - 启动/关闭事件
│   │
│   ├── config.py                   # 配置管理
│   │                               # - Pydantic Settings模型
│   │                               # - 环境变量读取
│   │                               # - 配置验证
│   │
│   ├── database.py                 # 数据库连接管理
│   │                               # - AsyncSession工厂
│   │                               # - 引擎配置
│   │                               # - 依赖注入函数
│   │
│   ├── models/                     # SQLAlchemy ORM模型
│   │   ├── __init__.py             # 模型导出和基类
│   │   ├── project.py              # 项目模型
│   │   ├── source_file.py          # 源文件模型
│   │   ├── design_spec.py          # 设计规范模型
│   │   ├── spec_lock.py            # 执行锁模型
│   │   ├── image_resource.py       # 图片资源模型
│   │   ├── svg_page.py             # SVG页面模型
│   │   ├── speaker_note.py         # 演讲备注模型
│   │   ├── pptx_export.py          # PPT导出模型
│   │   ├── pipeline_job.py         # Pipeline作业模型
│   │   └── enums.py                # 枚举类型定义
│   │
│   ├── schemas/                    # Pydantic数据模型
│   │   ├── __init__.py
│   │   ├── project.py              # 项目相关Schema
│   │   ├── source_file.py          # 源文件Schema
│   │   ├── design_spec.py          # Design Spec Schema
│   │   ├── pipeline.py             # Pipeline状态Schema
│   │   ├── svg_page.py             # SVG页面Schema
│   │   ├── export.py               # 导出Schema
│   │   └── common.py               # 通用Schema（分页、响应包装等）
│   │
│   ├── api/                        # API路由层
│   │   ├── __init__.py
│   │   ├── deps.py                 # 依赖注入
│   │   │                           # - get_db_session
│   │   │                           # - get_storage
│   │   │                           # - get_current_project
│   │   │
│   │   └── v1/                     # API版本v1
│   │       ├── __init__.py         # 路由聚合
│   │       ├── projects.py         # 项目CRUD + Pipeline控制
│   │       ├── sources.py          # 源文件上传/管理
│   │       ├── design_spec.py      # Design Spec / Eight Confirmations
│   │       ├── pipeline.py         # Pipeline状态/历史/恢复
│   │       ├── pages.py            # SVG页面查询/编辑
│   │       ├── exports.py          # PPT导出/下载
│   │       ├── images.py           # 图片资源管理
│   │       └── websocket.py        # WebSocket连接处理
│   │
│   ├── services/                   # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── project_service.py      # 项目业务逻辑
│   │   │                           # - CRUD操作
│   │   │                           # - 状态管理
│   │   │
│   │   ├── pipeline_service.py     # Pipeline业务逻辑
│   │   │                           # - 启动/取消/恢复
│   │   │                           # - 状态查询
│   │   │                           # - 与Celery交互
│   │   │
│   │   ├── storage_service.py      # 存储服务
│   │   │                           # - 文件上传/下载
│   │   │                           # - URL签名
│   │   │
│   │   └── llm_service.py          # LLM服务
│   │                               # - Prompt构建
│   │                               # - API调用封装
│   │                               # - 响应解析
│   │
│   ├── core/                       # 核心模块
│   │   ├── __init__.py
│   │   ├── pipeline/               # LangChain Pipeline
│   │   │   ├── __init__.py
│   │   │   ├── graph.py            # StateGraph定义和编译
│   │   │   ├── state.py            # Pipeline状态TypedDict
│   │   │   ├── nodes.py            # Pipeline节点函数
│   │   │   │                       # - source_processing_node
│   │   │   │                       # - strategist_node
│   │   │   │                       # - image_acquisition_node
│   │   │   │                       # - executor_node
│   │   │   │                       # - post_processing_node
│   │   │   │
│   │   │   └── prompts/            # Prompt模板
│   │   │       ├── strategist.md   # Strategist步骤Prompt
│   │   │       ├── executor.md     # Executor步骤Prompt
│   │   │       └── speaker_note.md # Speaker Note Prompt
│   │   │
│   │   ├── storage/                # 存储抽象层
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # StorageBackend抽象类
│   │   │   ├── minio.py            # MinIO实现
│   │   │   ├── local.py            # 本地文件系统实现
│   │   │   └── manager.py          # StorageManager工厂
│   │   │
│   │   └── scripts/                # 原skill脚本包装器
│   │       ├── __init__.py
│   │       ├── runner.py           # ScriptRunner类
│   │       │                       # - run_pdf_to_md
│   │       │                       # - run_svg_quality_checker
│   │       │                       # - run_finalize_svg
│   │       │                       # - run_svg_to_pptx
│   │       │
│   │       └── workspace.py        # ProjectWorkspace上下文管理器
│   │
│   ├── celery_app.py               # Celery应用配置
│   ├── tasks/                      # Celery任务
│   │   ├── __init__.py
│   │   ├── pipeline.py             # Pipeline主任务
│   │   ├── source_processing.py    # 源文件处理任务
│   │   ├── image_tasks.py          # 图片获取/生成任务
│   │   └── export.py               # PPT导出任务
│   │
│   └── utils/                      # 工具函数
│       ├── __init__.py
│       ├── validators.py           # 数据验证工具
│       └── exceptions.py           # 自定义异常
│
├── tests/                          # 测试目录
│   ├── __init__.py
│   ├── conftest.py                 # Pytest配置和fixtures
│   ├── test_api/                   # API集成测试
│   │   ├── test_projects.py
│   │   ├── test_sources.py
│   │   └── test_pipeline.py
│   ├── test_services/              # 服务层单元测试
│   │   ├── test_project_service.py
│   │   └── test_pipeline_service.py
│   └── test_core/                  # 核心模块测试
│       ├── test_pipeline_graph.py
│       └── test_storage.py
│
├── pyproject.toml                  # Python项目配置和依赖
├── alembic.ini                     # Alembic配置
├── Dockerfile                      # 生产镜像
├── Dockerfile.dev                  # 开发镜像
└── .env.example                    # 环境变量模板
```

### 前端目录详解

```
frontend/
├── src/
│   ├── components/                 # Vue组件
│   │   ├── common/                 # 通用组件
│   │   │   ├── AppHeader.vue       # 顶部导航栏
│   │   │   ├── AppSidebar.vue      # 侧边栏
│   │   │   ├── LoadingSpinner.vue  # 加载动画
│   │   │   └── ErrorMessage.vue    # 错误提示
│   │   │
│   │   ├── pipeline/               # Pipeline相关组件
│   │   │   ├── PipelineStatus.vue  # Pipeline状态条
│   │   │   ├── StepIndicator.vue   # 步骤指示器
│   │   │   └── LogViewer.vue       # 日志查看器
│   │   │
│   │   ├── project/                # 项目相关组件
│   │   │   ├── ProjectCard.vue     # 项目卡片
│   │   │   ├── ProjectForm.vue     # 项目表单
│   │   │   └── ProjectList.vue     # 项目列表
│   │   │
│   │   ├── source/                 # 源文件相关组件
│   │   │   ├── SourceUploader.vue  # 源文件上传组件
│   │   │   ├── SourceList.vue      # 源文件列表
│   │   │   └── SourcePreview.vue   # 源文件预览
│   │   │
│   │   ├── confirmation/           # Eight Confirmations组件
│   │   │   ├── EightConfirmations.vue      # 主组件
│   │   │   ├── ConfirmationCanvas.vue      # 画布确认
│   │   │   ├── ConfirmationPageCount.vue   # 页数确认
│   │   │   ├── ConfirmationAudience.vue    # 受众确认
│   │   │   ├── ConfirmationStyle.vue       # 风格确认
│   │   │   ├── ConfirmationColor.vue       # 配色确认
│   │   │   ├── ConfirmationIcon.vue        # 图标确认
│   │   │   ├── ConfirmationTypography.vue  # 字体确认
│   │   │   └── ConfirmationImage.vue       # 图片策略确认
│   │   │
│   │   ├── svg/                    # SVG相关组件
│   │   │   ├── SVGPreview.vue      # SVG预览组件
│   │   │   ├── SVGEditor.vue       # SVG编辑器
│   │   │   ├── SVGThumbnail.vue    # SVG缩略图
│   │   │   └── SVGQualityBadge.vue # SVG质量徽章
│   │   │
│   │   ├── image/                  # 图片相关组件
│   │   │   ├── ImageManager.vue    # 图片管理器
│   │   │   ├── ImageUploader.vue   # 图片上传
│   │   │   └── ImagePreview.vue    # 图片预览
│   │   │
│   │   └── export/                 # 导出相关组件
│   │       ├── ExportList.vue      # 导出列表
│   │       └── DownloadButton.vue  # 下载按钮
│   │
│   ├── views/                      # 页面视图
│   │   ├── HomeView.vue            # 首页/仪表盘
│   │   ├── ProjectListView.vue     # 项目列表页
│   │   ├── ProjectCreateView.vue   # 创建项目页
│   │   ├── ProjectDetailView.vue   # 项目详情页
│   │   ├── ConfirmationView.vue    # Eight Confirmations页
│   │   ├── SVGEditorView.vue       # SVG编辑器页
│   │   ├── PPTPreviewView.vue      # PPT预览页
│   │   ├── ExportView.vue          # 导出管理页
│   │   └── SettingsView.vue        # 系统设置页
│   │
│   ├── stores/                     # Pinia状态管理
│   │   ├── index.ts                # Store导出
│   │   ├── project.ts              # 项目Store
│   │   ├── pipeline.ts             # Pipeline Store
│   │   └── app.ts                  # 应用级Store
│   │
│   ├── api/                        # API客户端
│   │   ├── client.ts               # Axios实例配置
│   │   ├── projects.ts             # 项目API
│   │   ├── sources.ts              # 源文件API
│   │   ├── designSpec.ts           # Design Spec API
│   │   ├── pipeline.ts             # Pipeline API
│   │   ├── pages.ts                # SVG页面API
│   │   ├── exports.ts              # PPT导出API
│   │   └── images.ts               # 图片API
│   │
│   ├── composables/                # 组合式函数
│   │   ├── useWebSocket.ts         # WebSocket封装
│   │   ├── usePipeline.ts          # Pipeline状态管理
│   │   ├── useProject.ts           # 项目操作
│   │   └── useFileUpload.ts        # 文件上传
│   │
│   ├── router/                     # Vue Router
│   │   └── index.ts
│   │
│   ├── types/                      # TypeScript类型
│   │   └── index.ts
│   │
│   ├── utils/                      # 工具函数
│   │   ├── formatters.ts           # 格式化函数
│   │   └── validators.ts           # 验证函数
│   │
│   ├── App.vue
│   └── main.ts
│
├── public/                         # 静态资源
├── index.html
├── package.json
├── vite.config.ts                  # Vite配置
├── tsconfig.json                   # TypeScript配置
├── tsconfig.app.json
├── tsconfig.node.json
├── tailwind.config.js              # Tailwind CSS配置（可选）
└── Dockerfile
```

---

## 添加新功能

### 添加新的API端点

以添加「项目克隆」功能为例：

#### 1. 定义Schema

```python
# app/schemas/project.py

class ProjectCloneRequest(BaseModel):
    """项目克隆请求"""
    name: str = Field(..., min_length=2, max_length=100, description="新项目名称")
    description: Optional[str] = Field(None, max_length=500)

class ProjectCloneResponse(BaseModel):
    """项目克隆响应"""
    original_id: UUID
    new_id: UUID
    name: str
    message: str
```

#### 2. 实现业务逻辑

```python
# app/services/project_service.py

async def clone_project(
    db: AsyncSession,
    storage: StorageBackend,
    original_id: UUID,
    clone_data: ProjectCloneRequest
) -> Project:
    """克隆项目"""
    # 1. 获取原项目
    original = await get_project(db, original_id)
    if not original:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 2. 创建新项目
    new_project = Project(
        name=clone_data.name,
        description=clone_data.description or original.description,
        canvas_format=original.canvas_format,
        llm_provider=original.llm_provider,
        llm_model=original.llm_model,
        status=ProjectStatus.DRAFT,
        current_step=PipelineStep.INIT,
        step_status=StepStatus.PENDING,
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    
    # 3. 复制源文件
    for source in original.source_files:
        new_source = SourceFile(
            project_id=new_project.id,
            original_filename=source.original_filename,
            file_type=source.file_type,
            storage_key=source.storage_key,  # 共享存储
            file_size=source.file_size,
            markdown_content=source.markdown_content,
            conversion_status=source.conversion_status,
        )
        db.add(new_source)
    
    await db.commit()
    
    # 4. 复制存储文件
    await _copy_storage_files(storage, original_id, new_project.id)
    
    return new_project

async def _copy_storage_files(
    storage: StorageBackend,
    original_id: UUID,
    new_id: UUID
):
    """复制MinIO中的项目文件"""
    # 复制模板、设计规范等
    old_prefix = f"projects/{original_id}/"
    new_prefix = f"projects/{new_id}/"
    # ... 实现文件复制逻辑
```

#### 3. 添加路由

```python
# app/api/v1/projects.py

from app.schemas.project import ProjectCloneRequest, ProjectCloneResponse
from app.services.project_service import clone_project

@router.post("/{project_id}/clone", response_model=ProjectCloneResponse)
async def clone_project_endpoint(
    project_id: UUID,
    request: ProjectCloneRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    """克隆项目
    
    创建项目的副本，包含所有源文件和设计配置。
    不包含已生成的SVG页面和PPT导出。
    """
    new_project = await clone_project(db, storage, project_id, request)
    
    return ProjectCloneResponse(
        original_id=project_id,
        new_id=new_project.id,
        name=new_project.name,
        message=f"Project '{request.name}' cloned successfully"
    )
```

#### 4. 添加测试

```python
# tests/test_api/test_projects.py

async def test_clone_project(client: AsyncClient, db: AsyncSession):
    """测试项目克隆"""
    # 1. 创建原项目
    response = await client.post("/api/projects", json={
        "name": "Original Project",
        "description": "Test project"
    })
    original_id = response.json()["data"]["id"]
    
    # 2. 克隆项目
    response = await client.post(f"/api/projects/{original_id}/clone", json={
        "name": "Cloned Project",
        "description": "Cloned from original"
    })
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Cloned Project"
    assert data["original_id"] == original_id
    assert data["new_id"] != original_id
```

### 添加新的Pipeline步骤

以在Executor后添加「手动审核」步骤为例：

#### 1. 修改StateGraph

```python
# app/core/pipeline/graph.py

def _build_workflow(self) -> StateGraph:
    builder = StateGraph(PPTPipelineState)
    
    # ... 现有节点 ...
    
    # 添加新的审核节点
    builder.add_node("manual_review", self._manual_review_node)
    
    # 修改executor后的边
    builder.add_edge("executor", "manual_review")
    
    # 添加条件分支
    builder.add_conditional_edges(
        "manual_review",
        self._check_review,
        {
            "approved": "post_processing",
            "rejected": END  # 或回到executor
        }
    )
    
    # ... 其余代码 ...
    return builder.compile()

async def _manual_review_node(self, state: PPTPipelineState) -> PPTPipelineState:
    """人工审核步骤"""
    await self._set_waiting_review(state["project_id"])
    await self._notify_review_needed(state["project_id"])
    
    return {
        **state,
        "current_step": "manual_review",
        "step_status": "waiting_confirmation",
    }

def _check_review(self, state: PPTPipelineState) -> str:
    """检查审核状态"""
    if state.get("review_status") == "approved":
        return "approved"
    return "waiting"
```

#### 2. 添加审核API

```python
# app/api/v1/pipeline.py

@router.post("/{project_id}/pipeline/review")
async def review_pipeline(
    project_id: UUID,
    review: ReviewRequest,  # {status: "approved" | "rejected", comment: "..."}
    db: AsyncSession = Depends(get_db),
):
    """审核Pipeline执行结果"""
    project = await get_project(db, project_id)
    
    if project.current_step != "manual_review":
        raise HTTPException(400, "Project is not in review stage")
    
    if review.status == "approved":
        # 更新Pipeline状态，继续执行
        await update_pipeline_state(project_id, review_status="approved")
        # 触发后续步骤
        await resume_pipeline(project_id)
    else:
        # 标记为拒绝，可能需要重新执行
        await update_pipeline_state(project_id, review_status="rejected")
    
    return {"message": f"Review {review.status}"}
```

### 添加新的存储后端

以添加阿里云OSS支持为例：

```python
# app/core/storage/oss.py

import oss2
from .base import StorageBackend

class AliyunOSSStorage(StorageBackend):
    """阿里云OSS存储后端"""
    
    def __init__(self, access_key: str, secret_key: str, 
                 endpoint: str, bucket: str):
        auth = oss2.Auth(access_key, secret_key)
        self.bucket = oss2.Bucket(auth, endpoint, bucket)
    
    async def put(self, key: str, data: bytes | str, 
                  content_type: str = "application/octet-stream") -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.bucket.put_object(key, data, headers={"Content-Type": content_type})
        return key
    
    async def get(self, key: str) -> bytes:
        return self.bucket.get_object(key).read()
    
    async def delete(self, key: str) -> None:
        self.bucket.delete_object(key)
    
    async def exists(self, key: str) -> bool:
        return self.bucket.object_exists(key)
    
    def get_url(self, key: str, expires: int = 3600) -> str:
        return self.bucket.sign_url("GET", key, expires)
    
    def get_public_url(self, key: str) -> str:
        return f"https://{self.bucket.bucket_name}.{self.endpoint}/{key}"
```

然后更新StorageManager：

```python
# app/core/storage/manager.py

elif storage_type == "oss":
    from .oss import AliyunOSSStorage
    cls._instance = AliyunOSSStorage(
        access_key=os.getenv("OSS_ACCESS_KEY"),
        secret_key=os.getenv("OSS_SECRET_KEY"),
        endpoint=os.getenv("OSS_ENDPOINT"),
        bucket=os.getenv("OSS_BUCKET"),
    )
```

---

## 测试指南

### 测试结构

```
tests/
├── conftest.py              # 共享fixtures
├── __init__.py
├── test_api/                # API集成测试
│   ├── test_projects.py
│   ├── test_sources.py
│   ├── test_design_spec.py
│   ├── test_pipeline.py
│   ├── test_pages.py
│   └── test_exports.py
├── test_services/           # 服务层单元测试
│   ├── test_project_service.py
│   ├── test_pipeline_service.py
│   └── test_storage_service.py
├── test_core/               # 核心模块测试
│   ├── test_pipeline_graph.py
│   ├── test_storage.py
│   └── test_script_runner.py
└── fixtures/                # 测试数据
    ├── sample.pdf
    ├── sample.docx
    └── sample.md
```

### 共享Fixtures

```python
# tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base

# 测试数据库
TEST_DATABASE_URL = "postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncSession:
    """提供测试数据库会话"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    """提供HTTP测试客户端"""
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_project_data():
    """示例项目数据"""
    return {
        "name": "Test Project",
        "description": "A test project",
        "canvas_format": "ppt169",
        "llm_provider": "openai",
        "llm_model": "gpt-4o"
    }

@pytest_asyncio.fixture
async def sample_project(client: AsyncClient, sample_project_data):
    """创建示例项目"""
    response = await client.post("/api/projects", json=sample_project_data)
    return response.json()["data"]
```

### API集成测试示例

```python
# tests/test_api/test_projects.py

import pytest

class TestProjectAPI:
    """项目API测试"""
    
    async def test_create_project(self, client, sample_project_data):
        """测试创建项目"""
        response = await client.post("/api/projects", json=sample_project_data)
        
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == sample_project_data["name"]
        assert data["status"] == "draft"
        assert data["current_step"] == "init"
    
    async def test_create_project_without_name(self, client):
        """测试缺少名称时创建失败"""
        response = await client.post("/api/projects", json={})
        
        assert response.status_code == 422
        assert "name" in str(response.json())
    
    async def test_get_project_list(self, client, sample_project):
        """测试获取项目列表"""
        response = await client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] >= 1
        assert any(p["id"] == sample_project["id"] for p in data["items"])
    
    async def test_get_project_detail(self, client, sample_project):
        """测试获取项目详情"""
        response = await client.get(f"/api/projects/{sample_project['id']}")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == sample_project["id"]
        assert data["name"] == sample_project["name"]
    
    async def test_get_nonexistent_project(self, client):
        """测试获取不存在的项目"""
        response = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
    
    async def test_update_project(self, client, sample_project):
        """测试更新项目"""
        response = await client.put(
            f"/api/projects/{sample_project['id']}",
            json={"name": "Updated Name"}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Updated Name"
    
    async def test_delete_project(self, client, sample_project):
        """测试删除项目"""
        response = await client.delete(f"/api/projects/{sample_project['id']}")
        
        assert response.status_code == 200
        
        # 确认已删除
        response = await client.get(f"/api/projects/{sample_project['id']}")
        assert response.status_code == 404
    
    async def test_start_pipeline(self, client, sample_project):
        """测试启动Pipeline"""
        response = await client.post(f"/api/projects/{sample_project['id']}/start")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["current_step"] in ["source_processing", "init"]
```

### 服务层单元测试

```python
# tests/test_services/test_project_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.project_service import create_project, get_project, clone_project
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectCloneRequest

class TestProjectService:
    """项目服务测试"""
    
    @pytest.mark.asyncio
    async def test_create_project(self, db):
        """测试创建项目"""
        project_data = ProjectCreate(
            name="Test Project",
            description="Test",
            canvas_format="ppt169"
        )
        
        project = await create_project(db, project_data)
        
        assert project.name == "Test Project"
        assert project.status == "draft"
        assert project.canvas_format == "ppt169"
    
    @pytest.mark.asyncio
    async def test_clone_project(self, db, sample_project):
        """测试克隆项目"""
        mock_storage = AsyncMock()
        mock_storage.put.return_value = "test-key"
        
        clone_data = ProjectCloneRequest(
            name="Cloned Project",
            description="Cloned"
        )
        
        new_project = await clone_project(db, mock_storage, sample_project.id, clone_data)
        
        assert new_project.name == "Cloned Project"
        assert new_project.id != sample_project.id
        assert new_project.status == "draft"
        mock_storage.put.assert_called()
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api/test_projects.py

# 运行特定测试类
pytest tests/test_api/test_projects.py::TestProjectAPI

# 运行特定测试方法
pytest tests/test_api/test_projects.py::TestProjectAPI::test_create_project

# 显示详细输出
pytest -v

# 显示打印输出
pytest -s

# 生成覆盖率报告
pytest --cov=app --cov-report=html --cov-report=term

# 覆盖率报告将生成在 htmlcov/index.html

# 并行运行测试（需安装pytest-xdist）
pytest -n auto

# 调试模式（遇到错误停止）
pytest --pdb

# 只运行失败的测试
pytest --lf

# 先运行失败的测试，再运行其他
pytest --ff
```

### 测试配置

```toml
# pyproject.toml

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["app"]
omit = ["app/main.py", "app/celery_app.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

---

## 调试技巧

### 后端调试

#### 使用IPython嵌入调试

```python
# 在代码中插入断点
from IPython import embed; embed()

# 或使用更轻量的方式
import pdb; pdb.set_trace()
```

#### 使用VS Code调试

`.vscode/launch.json` 配置：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Server",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "console": "integratedTerminal"
    },
    {
      "name": "Celery Worker",
      "type": "python",
      "request": "launch",
      "module": "celery",
      "args": ["-A", "app.celery_app", "worker", "--loglevel=debug"],
      "cwd": "${workspaceFolder}/backend",
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v", "-s"],
      "cwd": "${workspaceFolder}/backend",
      "console": "integratedTerminal"
    }
  ]
}
```

#### 数据库查询调试

```python
# 在代码中打印SQL
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    print(f"\n\n{'='*50}")
    print(f"SQL: {statement}")
    print(f"Params: {parameters}")
    print(f"{'='*50}\n")
```

#### Celery任务调试

```bash
# 以同步方式运行任务（调试时）
python -c "
from app.celery_app import app
task = app.tasks['app.tasks.pipeline.run_pipeline_step']
result = task.run('project-id', 'source_processing', {})
print(result)
"

# 查看任务队列状态
celery -A app.celery_app inspect active
celery -A app.celery_app inspect scheduled
celery -A app.celery_app inspect reserved
celery -A app.celery_app inspect revoked

# 清除所有任务
celery -A app.celery_app purge

# 监控实时任务执行
celery -A app.celery_app events --dump
```

### 前端调试

#### Vue DevTools

1. 安装 [Vue DevTools浏览器扩展](https://devtools.vuejs.org/)
2. 打开浏览器开发者工具 → Vue面板
3. 可查看：
   - 组件树
   - Pinia状态
   - 路由信息
   - 事件监听

#### VS Code调试配置

`.vscode/launch.json`：

```json
{
  "configurations": [
    {
      "name": "Chrome Debug",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

#### 网络请求调试

```typescript
// 在api/client.ts中添加请求/响应拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error('[API Response Error]', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
```

### WebSocket调试

```bash
# 使用wscat测试WebSocket
npm install -g wscat

# 连接WebSocket
wscat -c ws://localhost:8000/ws/projects/{project_id}

# 发送消息
> {"type": "ping"}

# 查看实时推送的消息
```

### Docker调试

```bash
# 进入容器内部调试
docker-compose exec backend /bin/sh

# 在容器内运行Python
docker-compose exec backend python

# 检查容器环境变量
docker-compose exec backend env | grep OPENAI

# 检查数据库连接
docker-compose exec backend python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine('postgresql+asyncpg://pptmaster:pptmaster@db:5432/pptmaster')
async def test():
    async with engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print(result.fetchone())
asyncio.run(test())
"

# 实时查看所有容器日志
docker-compose logs -f --tail=100

# 仅查看特定服务的日志
docker-compose logs -f backend
docker-compose logs -f celery_worker
```

### 性能分析

#### 后端性能分析

```python
# 使用cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... 执行要分析的代码 ...

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 打印前20个
```

#### 数据库查询优化

```python
# 启用SQLAlchemy查询计时
import time
from sqlalchemy import event

@event.listens_for(Engine, "before_cursor_execute")
def before_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info["query_start_time"].pop(-1)
    if total > 0.1:  # 记录慢查询 (>100ms)
        print(f"\n[SLOW QUERY] {total:.3f}s: {statement[:200]}")
```

### 常见问题排查

#### 问题1: 数据库迁移失败

```bash
# 查看迁移历史
alembic history --verbose

# 标记某个迁移为已执行（跳过）
alembic stamp <revision_id>

# 手动回滚
alembic downgrade -1

# 生成空迁移脚本手动修复
alembic revision -m "manual fix"
```

#### 问题2: Celery任务不执行

```bash
# 检查Worker是否在线
celery -A app.celery_app inspect ping

# 检查队列是否有任务
docker-compose exec redis redis-cli -n 0 LLEN celery

# 清除所有挂起的任务
celery -A app.celery_app purge

# 重启Worker
docker-compose restart celery_worker
```

#### 问题3: 前端API请求失败

```bash
# 检查CORS配置
curl -I -X OPTIONS http://localhost:8000/api/projects \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"

# 检查后端是否运行
curl http://localhost:8000/api/health

# 检查Vite代理配置（vite.config.ts）
```

---

*本文档由 PPT Master Web Service 团队维护，如有疑问请联系开发团队。*