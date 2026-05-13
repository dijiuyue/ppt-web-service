# PPT Master Web Service - 架构说明文档

> 本文档详细描述 PPT Master Web Service 的系统架构、技术选型、数据流和核心组件设计。

---

## 目录

- [系统架构总览](#系统架构总览)
- [数据流图](#数据流图)
- [技术选型理由](#技术选型理由)
- [数据库设计说明](#数据库设计说明)
- [Pipeline工作流说明](#pipeline工作流说明)
- [LangChain StateGraph设计](#langchain-stategraph设计)
- [文件存储策略](#文件存储策略)

---

## 系统架构总览

### 整体架构

PPT Master Web Service 采用经典的**前后端分离 + 微服务化**架构，通过 Docker Compose 统一部署。系统分为五个核心层次：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           接入层 (Access Layer)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Nginx Reverse Proxy                              │   │
│  │  • 静态资源服务 (Vue前端)  • API反向代理  • WebSocket代理           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           前端层 (Presentation Layer)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │  Vue 3 + TS │  │ Element Plus│  │    Pinia    │  │   Vue Router    │   │
│  │             │  │             │  │             │  │                 │   │
│  │ • 响应式UI  │  │ • UI组件库  │  │ • 状态管理  │  │ • SPA路由       │   │
│  │ • 组合式API │  │ • 主题定制  │  │ • 跨组件通信│  │ • 路由守卫      │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      WebSocket Client                               │   │
│  │  • 实时状态更新  • Pipeline进度推送  • 确认通知                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ HTTP / WebSocket
┌─────────────────────────────────────────────────────────────────────────────┐
│                           业务逻辑层 (Business Logic Layer)                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI (ASGI Server)                          │   │
│  │                                                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │   │
│  │  │   REST API   │  │  WebSocket   │  │  Background Tasks    │     │   │
│  │  │  (CRUD接口)  │  │  (实时推送)  │  │  (轻量后台任务)      │     │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘     │   │
│  │                                                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │   │
│  │  │  SQLAlchemy  │  │   Pydantic   │  │   LangChain Core     │     │   │
│  │  │  (ORM/数据库) │  │  (数据验证)  │  │   (Pipeline编排)     │     │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘     │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    服务层 (Services)                         │   │   │
│  │  │  ProjectService │ PipelineService │ StorageService │ LLM     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    核心模块 (Core)                           │   │   │
│  │  │  Pipeline Graph │ Storage Backend │ Script Runner           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ Celery Task / DB / Cache / Storage
┌─────────────────────────────────────────────────────────────────────────────┐
│                           任务执行层 (Task Execution Layer)                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Celery Worker Pool                              │   │
│  │                                                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │   │
│  │  │  Pipeline    │  │   Source     │  │    Image Tasks       │     │   │
│  │  │  Executor    │  │  Processor   │  │  (Generate/Search)   │     │   │
│  │  │  • LLM调用   │  │  • PDF转MD   │  │  • AI图片生成        │     │   │
│  │  │  • Design    │  │  • DOCX解析  │  │  • Web图片搜索       │     │   │
│  │  │    Spec生成  │  │  • XLSX转换  │  │  • 图片处理          │     │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘     │   │
│  │                                                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │   │
│  │  │    SVG       │  │    PPT       │  │    Script Wrapper    │     │   │
│  │  │  Generator   │  │   Exporter   │  │  (ppt-master skill)  │     │   │
│  │  │  • 逐页生成  │  │  • SVG转PPT  │  │  • 质量检查          │     │   │
│  │  │  • 质量检查  │  │  • 动画配置  │  │  • 后处理            │     │   │
│  │  │  • 备注生成  │  │  • 打包下载  │  │  • 格式转换          │     │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据持久层 (Data Persistence Layer)                │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐    │
│  │   PostgreSQL   │  │     Redis      │  │  MinIO (S3-Compatible)     │    │
│  │                │  │                │  │                            │    │
│  │ • 项目数据     │  │ • 缓存         │  │ • 源文件存储               │    │
│  │ • 文件元数据   │  │ • 会话状态     │  │ • 转换后Markdown           │    │
│  │ • Pipeline状态 │  │ • Celery队列   │  │ • 图片资源                 │    │
│  │ • Design Spec  │  │ • 限流计数     │  │ • SVG页面文件              │    │
│  │ • Job记录      │  │ • 临时数据     │  │ • PPT导出文件              │    │
│  └────────────────┘  └────────────────┘  └────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 | 技术 |
|------|------|------|
| Nginx | 反向代理、负载均衡、静态资源服务 | Nginx |
| Vue Frontend | 用户界面、状态管理、API调用 | Vue 3 + TypeScript |
| FastAPI Backend | RESTful API、WebSocket、业务逻辑 | FastAPI + SQLAlchemy |
| Celery Worker | 异步任务执行、LLM调用 | Celery + Redis |
| PostgreSQL | 结构化数据持久化 | PostgreSQL 15+ |
| Redis | 缓存、消息队列、会话存储 | Redis 7 |
| MinIO | 对象存储（文件存储） | MinIO |

---

## 数据流图

### 1. 项目创建与源文件上传

```
用户 ──→ 前端 ──→ POST /api/projects ──→ FastAPI
                                          │
                                          ▼
                                    ┌───────────┐
                                    │ Project   │
                                    │ Service   │
                                    └─────┬─────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
                    ▼                     ▼                     ▼
               ┌─────────┐        ┌───────────┐        ┌───────────┐
               │PostgreSQL│        │   MinIO   │        │  Response  │
               │ projects │        │ (文件存储) │        │  201 Created│
               │  table   │        │           │        │  + project  │
               └─────────┘        └───────────┘        └─────┬─────┘
                                                             │
                    用户 ←── 前端 ←── 项目创建成功 ←──────────┘

用户 ──→ 上传文件 ──→ POST /api/projects/{id}/sources/upload
                        │
                        ▼
                   ┌───────────┐
                   │  Storage  │ ──→ MinIO: projects/{id}/sources/{sid}/{file}
                   │  Service  │
                   └─────┬─────┘
                         │
                         ▼
                   ┌───────────┐     ┌───────────┐
                   │ Celery    │ ──→ │ Source    │ ──→ 文件转换为Markdown
                   │ Task      │     │ Processor │
                   │ (async)   │     │ (pdf_to_md)│
                   └───────────┘     └─────┬─────┘
                                           │
                                           ▼
                                    MinIO: projects/{id}/sources/{sid}/converted.md
                                    PostgreSQL: source_files.conversion_status = "completed"
                                    WebSocket: 通知前端转换完成
```

### 2. Pipeline执行流程

```
用户 ──→ 点击「启动Pipeline」 ──→ POST /api/projects/{id}/start
                                      │
                                      ▼
                                ┌───────────────┐
                                │ Pipeline      │ ──→ Celery: run_pipeline_step
                                │ Service       │     project_id, step="source_processing"
                                └───────┬───────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
        ┌──────────┐           ┌──────────────┐         ┌──────────────┐
        │ LangChain │           │ Celery Worker │         │ WebSocket    │
        │ StateGraph│◄─────────│ (Task执行)    │────────►│ (状态推送)   │
        │ (编排)   │           │              │         │              │
        └────┬─────┘           └──────────────┘         └──────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    Pipeline Steps Flow                          │
    │                                                                 │
    │   [init] ──→ [source_processing] ──→ [strategist]            │
    │                                             │                   │
    │                                             ▼                   │
    │                                    [WAITING_CONFIRMATION]      │
    │                                             │                   │
    │                         用户确认Eight Confirmations             │
    │                                             │                   │
    │                                             ▼                   │
    │                                    [image_acquisition]         │
    │                                             │                   │
    │                                             ▼                   │
    │                                    [executor] ──→ 逐页SVG生成  │
    │                                             │                   │
    │                                             ▼                   │
    │                                    [post_processing]           │
    │                                             │                   │
    │                                             ▼                   │
    │                                    [COMPLETED] ──→ PPT导出     │
    └─────────────────────────────────────────────────────────────────┘
```

### 3. Eight Confirmations 数据流

```
Celery Worker (Strategist Task)
    │
    ├── 1. 读取所有source_files的markdown_content
    │
    ├── 2. 构建Prompt (包含strategist.md内容 + 源内容)
    │
    ├── 3. 调用LLM生成Eight Confirmations
    │       • confirmation_canvas: "ppt169"
    │       • confirmation_page_count: 15
    │       • confirmation_audience: "高管团队"
    │       • confirmation_style_mode: "A"
    │       • confirmation_color_scheme: {primary: "#1a1a2e", ...}
    │       • confirmation_icon_approach: "B"
    │       • confirmation_typography: {title_font: "Noto Sans SC", ...}
    │       • confirmation_image_approach: "C"
    │
    ├── 4. 生成完整 design_spec.md
    │
    ├── 5. 存入数据库
    │       PostgreSQL: design_specs 表
    │       MinIO: projects/{id}/design_spec.md
    │
    ├── 6. 设置状态
    │       PostgreSQL: projects.status = "CONFIRMING"
    │       PostgreSQL: projects.step_status = "WAITING_CONFIRMATION"
    │
    └── 7. WebSocket推送
            {"type": "confirmation_needed", "data": {confirmations...}}
            前端自动跳转确认页面

用户 ──→ 查看/修改Confirmations ──→ 点击确认
    │
    └── POST /api/projects/{id}/design-spec/confirm
            │
            ▼
        FastAPI ──→ 更新 design_specs.confirmation_status = "confirmed"
                ──→ 更新 projects.status = "PROCESSING"
                ──→ 触发Pipeline继续: Celery Task (image_acquisition)
                ──→ WebSocket: {"type": "step_change", "data": {"step": "image_acquisition"}}
```

### 4. SVG页面生成数据流

```
Celery Worker (Executor Task)
    │
    ├── 1. 读取 spec_lock (机器可读设计规范)
    │       PostgreSQL: spec_locks 表
    │       MinIO: projects/{id}/spec_lock.md
    │
    ├── 2. 读取 design_spec
    │       MinIO: projects/{id}/design_spec.md
    │
    ├── 3. 逐页生成SVG (Sequential, one at a time)
    │       FOR page_number IN 1..N:
    │           • 构建页面Prompt (页面类型 + 内容 + 设计规范)
    │           • 调用LLM生成SVG代码
    │           • SVG质量检查
    │           • 保存到DB和MinIO
    │           • WebSocket推送进度
    │
    ├── 4. 生成Speaker Notes
    │       FOR each svg_page:
    │           • 基于SVG内容生成演讲备注
    │           • 保存到 speaker_notes 表
    │
    ├── 5. SVG后处理
    │       • 调用 finalize_svg.py
    │       • 字体嵌入、路径优化
    │       • 保存到 svg_final/
    │
    └── 6. PPT导出
            • 调用 svg_to_pptx.py
            • 生成 .pptx 文件
            • 保存到 MinIO: projects/{id}/exports/{eid}/{filename}
            • WebSocket: {"type": "status_update", "data": {"status": "completed"}}
```

---

## 技术选型理由

### 后端框架：FastAPI

| 考量因素 | FastAPI优势 | 其他框架对比 |
|----------|-------------|-------------|
| **异步支持** | 原生ASGI，内置async/await | Django需额外配置channels |
| **自动文档** | 自动生成Swagger UI和ReDoc | Flask需集成flasgger |
| **类型安全** | Pydantic数据验证，类型提示 | Flask无原生验证 |
| **性能** | 基于Starlette，性能接近Go/Node | Django较重，Flask需优化 |
| **WebSocket** | 原生支持 | Django需channels层 |
| **生态** | SQLAlchemy、Celery成熟集成 | - |

### ORM：SQLAlchemy 2.0 + asyncpg

- **SQLAlchemy 2.0** 引入了全新的声明式API和异步查询支持
- **asyncpg** 是PostgreSQL的高性能异步驱动，比psycopg2快数倍
- 支持复杂查询、关系映射和迁移工具（Alembic）

### 任务队列：Celery + Redis

| 方案 | 优点 | 缺点 | 选择理由 |
|------|------|------|----------|
| Celery + Redis | 成熟稳定，生态丰富 | 配置较复杂 | 社区支持最好，Python生态成熟 |
| RQ | 简单轻量 | 功能较少 | 不适合复杂Pipeline |
| Dramatiq | 性能好 | 社区较小 | - |
| APScheduler | 内置简单 | 无分布式支持 | 不适合生产环境 |

### AI框架：LangChain

- **StateGraph** 提供了清晰的状态机编排能力，非常适合Pipeline工作流
- 内置多种LLM提供商集成（OpenAI、Anthropic等）
- 支持Prompt模板、Chain组合、Memory管理等
- 与FastAPI/Celery可以无缝集成

### 前端框架：Vue 3 + TypeScript

| 考量因素 | Vue 3优势 |
|----------|-----------|
| **组合式API** | `<script setup>` 语法简洁，逻辑复用方便 |
| **TypeScript** | 完整类型支持，开发体验好 |
| **性能** | Proxy-based响应式，性能优于Vue 2 |
| **生态** | Element Plus、Pinia、Vue Router成熟 |
| **学习曲线** | 比React平缓，文档友好 |

### 数据库：PostgreSQL 15+

- **JSON支持** - 原生JSONB字段，方便存储灵活的spec数据
- **全文搜索** - 源文件内容搜索
- **并发控制** - MVCC机制，高并发场景稳定
- **扩展性** - 支持分区、并行查询等
- **Docker友好** - 官方镜像稳定可靠

### 对象存储：MinIO

- **S3兼容** - 完全兼容AWS S3 API，便于迁移
- **轻量** - 单二进制文件，Docker镜像小巧
- **高性能** - 读写性能优异
- **Web管理** - 内置管理控制台
- **本地开发** - 无需云账号即可本地开发

---

## 数据库设计说明

### 设计原则

1. **规范化设计** - 减少数据冗余，确保数据一致性
2. **JSON字段灵活存储** - spec_lock等结构化不确定的数据使用JSONB
3. **状态机驱动** - Pipeline相关状态使用枚举类型严格约束
4. **软删除考虑** - 关键业务数据支持审计追溯
5. **索引优化** - 外键、常用查询字段添加索引

### ER关系图

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────┐
│  projects   │◄─────►│  design_specs    │       │  spec_locks  │
│             │  1:1  │                  │       │              │
│ • id (PK)   │       │ • id (PK)        │       │ • id (PK)    │
│ • name      │       │ • project_id(FK) │       │ • project_id │
│ • status    │       │ • confirmation_* │       │ • colors     │
│ • current_  │       │ • spec_content   │       │ • typography │
│   step      │       │ • confirmation_  │       │ • icons      │
│ • llm_*     │       │   status         │       │ • images     │
└──────┬──────┘       └──────────────────┘       └──────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│ source_files │      │ image_resources  │      │  svg_pages   │
│              │      │                  │      │              │
│ • id (PK)    │      │ • id (PK)        │      │ • id (PK)    │
│ • project_id │      │ • project_id(FK) │      │ • project_id │
│ • file_type  │      │ • acquire_via    │      │ • page_number│
│ • storage_key│      │ • status         │      │ • svg_content│
│ • markdown_  │      │ • storage_key    │      │ • quality_*  │
│   content    │      │ • generation_    │      │              │
└──────────────┘      │   prompt         │      └──────┬───────┘
                      └──────────────────┘             │
┌──────────────┐      ┌──────────────────┐             │ 1:1
│ pipeline_jobs│      │ pptx_exports     │             ▼
│              │      │                  │      ┌──────────────┐
│ • id (PK)    │      │ • id (PK)        │      │ speaker_notes│
│ • project_id │      │ • project_id(FK) │      │              │
│ • step       │      │ • storage_key    │      │ • id (PK)    │
│ • status     │      │ • file_size      │      │ • svg_page_id│
│ • celery_    │      │ • transition_    │      │ • note_content│
│   task_id    │      │   effect         │      └──────────────┘
│ • error_*    │      └──────────────────┘
└──────────────┘
```

### 表设计说明

#### projects（项目主表）

核心项目信息表，记录项目基本信息和Pipeline执行状态。

```sql
-- 关键字段索引
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_current_step ON projects(current_step);
CREATE INDEX idx_projects_step_status ON projects(step_status);
CREATE INDEX idx_projects_created_at ON projects(created_at);
```

状态转换规则：
- `DRAFT` → `CONFIRMING`（Strategist完成后）
- `CONFIRMING` → `PROCESSING`（用户确认后）
- `PROCESSING` → `COMPLETED` / `FAILED`（Pipeline结束）

#### source_files（源文件表）

存储源文件元数据和转换后的Markdown内容。转换过程是异步的，通过 `conversion_status` 跟踪状态。

```sql
CREATE INDEX idx_source_files_project_id ON source_files(project_id);
CREATE INDEX idx_source_files_conversion ON source_files(conversion_status);
```

#### design_specs（设计规范表）

存储AI生成的Eight Confirmations和完整Design Spec。

**Eight Confirmations字段说明：**

| 字段 | 说明 | 示例值 |
|------|------|--------|
| `confirmation_canvas` | 画布格式 | `ppt169`, `ppt43`, `xhs`, `story` |
| `confirmation_page_count` | 建议页数 | `15` |
| `confirmation_audience` | 目标受众 | `高管团队`、`技术工程师` |
| `confirmation_style_mode` | 风格模式 | `A` (简洁专业) / `B` (视觉冲击力) / `C` (数据驱动) |
| `confirmation_color_scheme` | 配色方案 | JSON `{primary, secondary, accent, ...}` |
| `confirmation_icon_approach` | 图标策略 | `A` / `B` / `C` / `D` |
| `confirmation_typography` | 字体方案 | JSON `{title_font, body_font, title_size, body_size}` |
| `confirmation_image_approach` | 图片策略 | `A`(AI生成) / `B`(Web搜索) / `C`(用户上传) / `D`(混合) / `E`(无图片) |

#### spec_locks（执行锁表）

将Design Spec解析为机器可读的JSON结构，供后续Pipeline步骤使用。每个JSON字段都有明确的结构定义。

**colors结构示例：**

```json
{
  "bg": "#ffffff",
  "primary": "#1a1a2e",
  "accent": "#e94560",
  "secondary_accent": "#533483",
  "text": "#16213e",
  "text_secondary": "#666666",
  "border": "#e0e0e0"
}
```

**page_rhythm结构示例：**

```json
{
  "P01": "anchor",
  "P02": "dense",
  "P03": "breathing",
  "P04": "dense"
}
```

#### svg_pages（SVG页面表）

存储生成的SVG页面，包含SVG内容和质量检查结果。

```sql
CREATE INDEX idx_svg_pages_project_id ON svg_pages(project_id);
CREATE INDEX idx_svg_pages_page_number ON svg_pages(page_number);
CREATE INDEX idx_svg_pages_quality ON svg_pages(quality_check_status);
```

#### pipeline_jobs（流水线作业表）

记录每个Pipeline步骤的执行历史，用于状态追踪和故障排查。

```sql
CREATE INDEX idx_pipeline_jobs_project_id ON pipeline_jobs(project_id);
CREATE INDEX idx_pipeline_jobs_step ON pipeline_jobs(step);
CREATE INDEX idx_pipeline_jobs_status ON pipeline_jobs(status);
CREATE INDEX idx_pipeline_jobs_celery ON pipeline_jobs(celery_task_id);
```

### 枚举类型定义

```sql
-- PostgreSQL枚举类型（通过SQLAlchemy Enum定义）
CREATE TYPE projectstatus AS ENUM ('draft', 'confirming', 'processing', 'completed', 'failed');
CREATE TYPE pipelinestep AS ENUM ('init', 'source_processing', 'strategist', 'image_acquisition', 'executor', 'post_processing', 'completed');
CREATE TYPE stepstatus AS ENUM ('pending', 'running', 'completed', 'failed', 'waiting_confirmation');
CREATE TYPE jobstatus AS ENUM ('pending', 'running', 'completed', 'failed', 'waiting_confirmation', 'cancelled');
```

---

## Pipeline工作流说明

### Pipeline概述

Pipeline是PPT生成的核心工作流，共包含7个步骤，通过LangChain StateGraph编排，Celery异步执行。

```
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 1 │───►│  Source Content  │───►│  源文件处理    │───►│ 文件转换为Markdown   │
│         │    │  Processing      │    │               │    │ 文本提取/结构化      │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
                                              │
                                              ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 2 │───►│  Project Init    │───►│ 项目初始化    │───►│ 创建项目目录结构     │
│         │    │                  │    │               │    │ 初始化配置参数       │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
                                              │
                                              ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 3 │───►│  Template Option │───►│ 模板选项      │───►│ 选择画布格式         │
│         │    │                  │    │               │    │ (Web界面配置)        │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
                                              │
                                              ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 4 │───►│  Strategist Phase│───►│ 策略制定      │───►│ AI分析内容           │
│         │    │  (BLOCKING)      │    │               │    │ 生成Eight Confirms   │
│         │    │                  │    │ 等待用户确认   │    │ 生成Design Spec      │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
                                              │ ◄── 用户确认
                                              ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 5 │───►│  Image           │───►│ 图片获取      │───►│ AI生成图片           │
│         │    │  Acquisition     │    │               │    │ Web搜索图片          │
│         │    │                  │    │               │    │ 用户上传图片         │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
                                              │
                                              ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 6 │───►│  Executor Phase  │───►│ 页面执行      │───►│ 逐页生成SVG          │
│         │    │                  │    │               │    │ SVG质量检查          │
│         │    │                  │    │               │    │ 生成Speaker Notes    │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
                                              │
                                              ▼
┌─────────┐    ┌──────────────────┐    ┌───────────────┐    ┌──────────────────────┐
│  Step 7 │───►│  Post-processing │───►│ 后处理导出    │───►│ SVG后处理/优化       │
│         │    │  & Export        │    │               │    │ 导出PPTX文件         │
│         │    │                  │    │               │    │ 质量最终检查         │
└─────────┘    └──────────────────┘    └───────────────┘    └──────────────────────┘
```

### 各步骤详细说明

#### Step 1: Source Content Processing（源文件处理）

**职责**: 将用户上传的各种格式文件转换为统一的Markdown文本。

**输入**: 源文件（PDF/DOCX/XLSX/PPTX/URL/MD/TXT/HTML/EPUB）
**输出**: Markdown文本 + 结构化元数据

**处理流程**:
```python
async def process_source_files(project_id: str):
    for source_file in project.source_files:
        # 根据文件类型选择转换器
        if source_file.file_type == "pdf":
            markdown = await run_pdf_to_md(source_file.storage_key)
        elif source_file.file_type == "docx":
            markdown = await run_docx_to_md(source_file.storage_key)
        elif source_file.file_type == "xlsx":
            markdown = await run_xlsx_to_md(source_file.storage_key)
        # ... 其他格式
        
        # 保存转换结果
        source_file.markdown_content = markdown
        source_file.conversion_status = "completed"
```

#### Step 2: Project Initialization（项目初始化）

**职责**: 初始化项目配置和目录结构。

**输入**: 项目基本信息（名称、描述、画布格式）
**输出**: 初始化后的项目配置

#### Step 3: Template Option（模板选项）

**职责**: 确定画布格式和基础设计参数。

**说明**: 此步骤在项目创建时通过Web界面配置，不需要独立的Pipeline步骤执行。

画布格式对应viewBox:
| 格式 | viewBox | 尺寸 |
|------|---------|------|
| ppt169 | `0 0 1280 720` | 16:9 |
| ppt43 | `0 0 1024 768` | 4:3 |
| xhs | `0 0 900 1200` | 3:4 |
| story | `0 0 1080 1920` | 9:16 |

#### Step 4: Strategist Phase（策略制定）- **BLOCKING**

**职责**: AI分析源内容，生成Eight Confirmations和完整Design Spec。

**输入**: 所有source_files的markdown_content
**输出**: Eight Confirmations + design_spec.md

**关键特征**: 
- 此步骤会暂停Pipeline，等待用户确认
- 用户确认后才能继续执行

#### Step 5: Image Acquisition（图片获取）

**职责**: 根据确认的图片策略获取所需图片资源。

**策略选项**:
- **A - AI生成**: 使用DALL-E/Midjourney等生成图片
- **B - Web搜索**: 使用搜索引擎查找免版权图片
- **C - 用户上传**: 用户手动上传所需图片
- **D - 混合模式**: 结合以上多种方式
- **E - 无图片**: 纯文字排版

#### Step 6: Executor Phase（页面执行）

**职责**: 根据spec_lock逐页生成SVG页面。

**特点**:
- 逐页顺序生成（sequential）
- 每页独立调用LLM
- 每页包含SVG代码 + Speaker Note
- 生成后进行SVG质量检查

#### Step 7: Post-processing & Export（后处理导出）

**职责**: SVG后处理、质量检查和PPTX导出。

**流程**:
1. SVG后处理（字体嵌入、路径优化）
2. 最终质量检查
3. PPTX导出
4. 资源清理

---

## LangChain StateGraph设计

### StateGraph架构

Pipeline使用LangChain的StateGraph实现状态机编排，每个步骤对应一个Graph节点。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        StateGraph (PPTMasterPipeline)                    │
│                                                                          │
│   ┌─────────┐    ┌─────────────┐    ┌─────────────────┐               │
│   │  Entry  │───►│   source_   │───►│    strategist   │               │
│   │  Point  │    │ processing  │    │                 │               │
│   └─────────┘    └─────────────┘    └────────┬────────┘               │
│                                              │                          │
│                                              ▼                          │
│                                     ┌─────────────────┐                │
│                                     │ wait_           │◄─────────────┐│
│                                     │ confirmation    │              ││
│                                     │                 │              ││
│                                     │ 等待用户确认    │              ││
│                                     └────────┬────────┘              ││
│                                              │                       ││
│                               ┌──────────────┼──────────────┐        ││
│                               │              │              │        ││
│                               ▼              │              ▼        ││
│                        ┌─────────────┐       │       ┌────────────┐  ││
│                        │    END      │       │       │ image_     │  ││
│                        │  (继续等待)  │       │       │ acquisition│  ││
│                        └─────────────┘       │       └─────┬──────┘  ││
│                                              │             │         ││
│                                              │  用户确认   │         ││
│                                              │             ▼         ││
│                                              │      ┌─────────────┐  ││
│                                              │      │  executor   │  ││
│                                              │      └──────┬──────┘  ││
│                                              │             │         ││
│                                              │             ▼         ││
│                                              │      ┌─────────────┐  ││
│                                              │      │ post_       │  ││
│                                              │      │ processing  │──┘│
│                                              │      └──────┬──────┘   │
│                                              │             │          │
│                                              │             ▼          │
│                                              │      ┌─────────────┐   │
│                                              └─────►│     END     │   │
│                                                     │  (Pipeline   │   │
│                                                     │   完成)      │   │
│                                                     └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 状态定义

```python
from typing import TypedDict, Optional

class PPTPipelineState(TypedDict):
    """Pipeline状态定义"""
    project_id: str                    # 项目ID
    current_step: str                  # 当前步骤
    step_status: str                   # 步骤状态
    design_spec: Optional[str]         # Design Spec内容
    spec_lock: Optional[str]          # Spec Lock内容
    confirmations: Optional[dict]     # Eight Confirmations
    confirmation_status: str           # 确认状态
    errors: list[str]                  # 错误列表
```

### 节点实现

```python
class PPTMasterPipeline:
    """LangChain驱动的PPT生成Pipeline"""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """构建StateGraph工作流"""
        builder = StateGraph(PPTPipelineState)
        
        # === 添加节点 ===
        builder.add_node("source_processing", self._source_processing_node)
        builder.add_node("strategist", self._strategist_node)
        builder.add_node("wait_confirmation", self._wait_confirmation_node)
        builder.add_node("image_acquisition", self._image_acquisition_node)
        builder.add_node("executor", self._executor_node)
        builder.add_node("post_processing", self._post_processing_node)
        
        # === 添加边 ===
        # 入口 -> 源文件处理
        builder.set_entry_point("source_processing")
        
        # 源文件处理 -> 策略制定
        builder.add_edge("source_processing", "strategist")
        
        # 策略制定 -> 等待确认
        builder.add_edge("strategist", "wait_confirmation")
        
        # 等待确认 -> 条件分支
        builder.add_conditional_edges(
            "wait_confirmation",
            self._check_confirmation,
            {
                "confirmed": "image_acquisition",   # 已确认 -> 图片获取
                "waiting": END                       # 未确认 -> 结束等待
            }
        )
        
        # 图片获取 -> 条件分支
        builder.add_conditional_edges(
            "image_acquisition",
            self._check_images,
            {
                "needed": "executor",   # 需要图片 -> 页面执行
                "skip": "executor"      # 跳过图片 -> 页面执行
            }
        )
        
        # 页面执行 -> 后处理
        builder.add_edge("executor", "post_processing")
        
        # 后处理 -> 结束
        builder.add_edge("post_processing", END)
        
        return builder.compile()
    
    async def _strategist_node(self, state: PPTPipelineState) -> PPTPipelineState:
        """Strategist步骤: 生成Eight Confirmations和Design Spec"""
        # 1. 读取source files的markdown内容
        sources = await self._get_source_markdown(state["project_id"])
        
        # 2. 构建prompt
        prompt = self._build_strategist_prompt(sources)
        
        # 3. 调用LLM生成Eight Confirmations
        response = await self.llm.ainvoke(prompt)
        
        # 4. 解析LLM输出
        confirmations = self._parse_confirmations(response.content)
        design_spec = self._parse_design_spec(response.content)
        
        # 5. 保存到数据库
        await self._save_design_spec(state["project_id"], confirmations, design_spec)
        
        # 6. 设置等待确认状态
        await self._set_waiting_confirmation(state["project_id"])
        
        # 7. 通过WebSocket通知前端
        await self._notify_confirmation_needed(state["project_id"], confirmations)
        
        return {
            **state,
            "current_step": "strategist",
            "step_status": "waiting_confirmation",
            "confirmations": confirmations,
            "design_spec": design_spec,
            "confirmation_status": "pending"
        }
    
    async def _executor_node(self, state: PPTPipelineState) -> PPTPipelineState:
        """Executor步骤: 逐页生成SVG"""
        project_id = state["project_id"]
        
        # 1. 读取spec_lock和design_spec
        spec_lock = await self._get_spec_lock(project_id)
        design_spec = await self._get_design_spec(project_id)
        
        # 2. 获取页面规划
        page_plan = spec_lock["page_rhythm"]  # {"P01": "anchor", "P02": "dense", ...}
        
        # 3. 逐页生成SVG
        for page_key, page_rhythm in page_plan.items():
            page_number = int(page_key.replace("P", ""))
            
            # 构建页面prompt
            page_prompt = self._build_page_prompt(
                page_number=page_number,
                page_rhythm=page_rhythm,
                spec_lock=spec_lock,
                design_spec=design_spec
            )
            
            # 调用LLM生成SVG
            svg_response = await self.llm.ainvoke(page_prompt)
            svg_content = self._extract_svg(svg_response.content)
            
            # SVG质量检查
            quality_result = await self._check_svg_quality(svg_content)
            
            # 生成Speaker Note
            note_prompt = self._build_note_prompt(svg_content, page_number)
            note_response = await self.llm.ainvoke(note_prompt)
            
            # 保存到数据库和MinIO
            await self._save_svg_page(project_id, page_number, svg_content, quality_result)
            await self._save_speaker_note(project_id, page_number, note_response.content)
            
            # WebSocket推送进度
            await self._notify_page_progress(project_id, page_number, len(page_plan))
        
        return {
            **state,
            "current_step": "executor",
            "step_status": "completed"
        }
    
    def _check_confirmation(self, state: PPTPipelineState) -> str:
        """检查用户是否已确认"""
        if state["confirmation_status"] == "confirmed":
            return "confirmed"
        return "waiting"
    
    def _check_images(self, state: PPTPipelineState) -> str:
        """检查是否需要图片获取步骤"""
        confirmation = state.get("confirmations", {})
        image_approach = confirmation.get("confirmation_image_approach", "E")
        if image_approach == "E":  # 无图片
            return "skip"
        return "needed"
```

### Celery任务集成

```python
# tasks/pipeline.py

from celery import shared_task
from app.core.pipeline.graph import PPTMasterPipeline

@shared_task(bind=True, max_retries=3)
def run_pipeline_step(self, project_id: str, step: str, input_data: dict = None):
    """执行Pipeline单个步骤"""
    try:
        pipeline = PPTMasterPipeline()
        result = pipeline.run_step(project_id, step, input_data)
        return result
    except Exception as exc:
        # 重试逻辑
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        # 记录错误，更新项目状态
        update_project_status(project_id, status="failed")
        raise

@shared_task
def process_source_file(source_id: str):
    """转换源文件为markdown"""
    from app.core.scripts.runner import ScriptRunner
    
    runner = ScriptRunner()
    source_file = get_source_file(source_id)
    
    # 下载文件到临时目录
    with ProjectWorkspace(source_file.project_id) as workspace:
        file_path = workspace.get_file(source_file.storage_key)
        
        # 根据文件类型转换
        if source_file.file_type == "pdf":
            markdown = runner.run_pdf_to_md(file_path)
        elif source_file.file_type == "docx":
            markdown = runner.run_docx_to_md(file_path)
        # ...
        
        # 保存转换结果
        source_file.markdown_content = markdown
        source_file.conversion_status = "completed"
        save_source_file(source_file)

@shared_task
def generate_images(project_id: str, image_ids: list[str]):
    """批量生成图片"""
    for image_id in image_ids:
        image_resource = get_image_resource(image_id)
        
        if image_resource.acquire_via == "ai":
            # AI生成图片
            image_data = generate_image_with_ai(image_resource.generation_prompt)
        elif image_resource.acquire_via == "web":
            # Web搜索图片
            image_data = search_image_on_web(image_resource.search_query)
        
        # 保存图片
        storage_key = save_to_minio(image_data, f"projects/{project_id}/images/{image_id}")
        image_resource.storage_key = storage_key
        image_resource.status = "generated"
        save_image_resource(image_resource)

@shared_task
def run_svg_quality_check(project_id: str):
    """SVG质量检查"""
    from app.core.scripts.runner import ScriptRunner
    
    runner = ScriptRunner()
    svg_pages = get_svg_pages(project_id)
    
    with ProjectWorkspace(project_id) as workspace:
        for svg_page in svg_pages:
            result = runner.run_svg_quality_checker(workspace.path)
            svg_page.quality_check_status = result["status"]
            svg_page.quality_check_errors = result.get("errors", [])
            svg_page.quality_check_warnings = result.get("warnings", [])
            save_svg_page(svg_page)

@shared_task
def export_pptx(project_id: str, export_options: dict = None):
    """导出PPT"""
    from app.core.scripts.runner import ScriptRunner
    
    runner = ScriptRunner()
    
    with ProjectWorkspace(project_id) as workspace:
        # 执行SVG后处理
        runner.run_finalize_svg(workspace.path)
        
        # 导出PPTX
        pptx_files = runner.run_svg_to_pptx(workspace.path, export_options or {})
        
        # 保存导出记录
        for pptx_file in pptx_files:
            storage_key = save_to_minio(
                pptx_file["data"],
                f"projects/{project_id}/exports/{pptx_file['filename']}"
            )
            create_pptx_export(project_id, storage_key, pptx_file["filename"])
```

---

## 文件存储策略

### 存储抽象层设计

系统采用抽象层设计，支持多种存储后端：

```python
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    """存储后端抽象接口"""
    
    @abstractmethod
    async def put(self, key: str, data: bytes | str, 
                  content_type: str = "application/octet-stream") -> str:
        """上传文件，返回存储key"""
        ...
    
    @abstractmethod
    async def get(self, key: str) -> bytes:
        """下载文件"""
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除文件"""
        ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        ...
    
    @abstractmethod
    def get_url(self, key: str, expires: int = 3600) -> str:
        """获取预签名URL（临时访问）"""
        ...
    
    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """获取公开URL（如配置为公开访问）"""
        ...
```

### 存储路径规范

```
projects/{project_id}/                          # 项目根目录
├── sources/{source_id}/
│   ├── {original_filename}                     # 原始上传文件
│   └── converted.md                            # 转换后的Markdown
├── images/{image_id}/
│   ├── {filename}                              # 最终使用的图片
│   └── original_{filename}                     # 用户上传的原始图片
├── design_spec.md                              # Design Spec文档
├── spec_lock.md                                # Spec Lock文档
├── svg_output/
│   ├── 01_cover.svg                            # 原始生成的SVG
│   ├── 02_toc.svg
│   ├── 03_content_1.svg
│   └── ...
├── svg_final/                                  # 后处理后的SVG
│   ├── 01_cover.svg
│   ├── 02_toc.svg
│   └── ...
├── notes/
│   ├── total.md                                # 所有备注汇总
│   ├── 01_cover.md                             # 单页备注
│   └── ...
├── exports/{export_id}/
│   └── {project_name}_{timestamp}.pptx         # 导出的PPT文件
└── templates/                                  # 自定义模板文件
```

### MinIOStorage实现

```python
import boto3
from botocore.config import Config

class MinioStorage(StorageBackend):
    """MinIO/S3存储后端"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, 
                 bucket: str, secure: bool = False):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )
    
    async def put(self, key: str, data: bytes | str, 
                  content_type: str = "application/octet-stream") -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        return key
    
    async def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()
    
    async def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
    
    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False
    
    def get_url(self, key: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires
        )
    
    def get_public_url(self, key: str) -> str:
        endpoint = self.client.meta.endpoint_url
        return f"{endpoint}/{self.bucket}/{key}"
```

### LocalStorage实现

```python
import os
import aiofiles
from pathlib import Path

class LocalStorage(StorageBackend):
    """本地文件系统存储后端（开发环境）"""
    
    def __init__(self, base_path: str = "./data/storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def put(self, key: str, data: bytes | str, 
                  content_type: str = "application/octet-stream") -> str:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "w" if isinstance(data, str) else "wb"
        encoding = "utf-8" if isinstance(data, str) else None
        
        async with aiofiles.open(file_path, mode, encoding=encoding) as f:
            await f.write(data)
        
        return key
    
    async def get(self, key: str) -> bytes:
        file_path = self.base_path / key
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()
    
    async def delete(self, key: str) -> None:
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()
    
    async def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()
    
    def get_url(self, key: str, expires: int = 3600) -> str:
        return f"/storage/{key}"
    
    def get_public_url(self, key: str) -> str:
        return f"/storage/{key}"
```

### StorageManager工厂

```python
class StorageManager:
    """存储后端管理器 - 根据配置自动选择backend"""
    
    _instance: StorageBackend = None
    
    @classmethod
    def get_backend(cls) -> StorageBackend:
        if cls._instance is None:
            storage_type = os.getenv("STORAGE_BACKEND", "minio")
            
            if storage_type == "minio":
                cls._instance = MinioStorage(
                    endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
                    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    bucket=os.getenv("MINIO_BUCKET", "pptmaster"),
                    secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
                )
            elif storage_type == "local":
                cls._instance = LocalStorage(
                    base_path=os.getenv("STORAGE_LOCAL_PATH", "./data/storage")
                )
            else:
                raise ValueError(f"Unknown storage backend: {storage_type}")
        
        return cls._instance
```

### 临时工作目录管理

```python
import tempfile
import shutil
from contextlib import asynccontextmanager

class ProjectWorkspace:
    """管理项目的临时工作目录"""
    
    def __init__(self, project_id: str, storage: StorageBackend = None):
        self.project_id = project_id
        self.storage = storage or StorageManager.get_backend()
        self.temp_dir = None
    
    async def __aenter__(self):
        """创建临时目录，从存储同步文件"""
        self.temp_dir = tempfile.mkdtemp(prefix=f"ppt_{self.project_id}_")
        await self._sync_from_storage()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """同步结果到存储，清理临时目录"""
        if exc_type is None:
            await self._sync_to_storage()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def _sync_from_storage(self):
        """从MinIO同步项目文件到临时目录"""
        prefix = f"projects/{self.project_id}/"
        # 列出所有文件并下载
        # ...
    
    async def _sync_to_storage(self):
        """从临时目录同步结果到MinIO"""
        for file_path in Path(self.temp_dir).rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.temp_dir)
                key = f"projects/{self.project_id}/{relative_path}"
                data = file_path.read_bytes()
                await self.storage.put(key, data)
    
    @property
    def path(self) -> str:
        return self.temp_dir
    
    def get_file(self, relative_path: str) -> str:
        """获取临时目录中的文件绝对路径"""
        return str(Path(self.temp_dir) / relative_path)
```

---

*本文档由 PPT Master Web Service 团队维护，如有疑问请联系开发团队。*