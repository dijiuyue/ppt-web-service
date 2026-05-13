# PPT Master Web Service

> 基于AI的智能PPT生成Web服务，通过LLM驱动的Pipeline将源内容自动转换为专业演示文稿。

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [详细安装指南](#详细安装指南)
- [使用指南](#使用指南)
- [开发指南](#开发指南)
- [API文档](#api文档)
- [环境变量参考](#环境变量参考)
- [常见问题FAQ](#常见问题faq)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 项目简介

PPT Master Web Service 是一个基于Web的智能PPT生成平台，它将[ppt-master](https://github.com/hugohe3/ppt-master) skill改造为前后端分离的Web服务。用户可以通过直观的Web界面完成从内容上传到PPT下载的全流程，无需任何命令行操作。

核心工作流程：用户上传源文件（PDF、Word、Excel等）或提供URL，系统通过LLM（OpenAI/Anthropic）自动分析内容、设计排版、生成图片、制作SVG页面，最终导出为PPTX格式。

### 核心概念

| 概念 | 说明 |
|------|------|
| **Pipeline** | 7步PPT生成流水线：源文件处理 → 策略制定 → 图片获取 → 页面执行 → 后处理导出 |
| **Eight Confirmations** | 8项设计确认（画布、页数、受众、风格、配色、图标、字体、图片策略），由用户在AI生成后确认 |
| **Design Spec** | AI生成的完整设计规范文档（Markdown格式） |
| **Spec Lock** | 机器可读的设计规范锁定文件，指导后续页面生成 |

---

## 功能特性

### 核心功能

- **智能内容分析** - 支持PDF、Word、Excel、PPT、URL、Markdown等多种源文件格式，自动转换为结构化内容
- **AI驱动设计** - 基于LLM自动生成Design Spec，包含完整的设计规范
- **八大确认机制** - Eight Confirmations确保AI生成的设计决策符合用户期望
- **自动图片获取** - 支持AI生成、Web搜索、用户上传三种图片获取方式
- **SVG页面生成** - 逐页生成高质量SVG，支持实时预览和编辑
- **PPT导出** - 支持原生PPTX导出，包含动画和过渡效果

### 技术特性

- **前后端分离** - Vue 3 + FastAPI，现代化技术栈
- **异步任务队列** - Celery + Redis处理耗时的LLM调用和文件处理
- **实时状态推送** - WebSocket实时推送Pipeline执行状态
- **对象存储抽象** - 支持MinIO（S3兼容）和本地文件系统
- **数据库迁移** - Alembic管理数据库schema变更
- **容器化部署** - Docker Compose一键启动所有服务

### 支持的文件格式

| 格式 | 上传 | 说明 |
|------|------|------|
| PDF | ✅ | 自动提取文本内容 |
| DOCX | ✅ | Word文档 |
| XLSX | ✅ | Excel表格 |
| PPTX | ✅ | PowerPoint文件 |
| URL | ✅ | 网页内容抓取 |
| MD | ✅ | Markdown文件 |
| TXT | ✅ | 纯文本文件 |
| HTML | ✅ | 网页文件 |
| EPUB | ✅ | 电子书格式 |

### 支持的画布格式

| 格式 | 尺寸 | 适用场景 |
|------|------|----------|
| PPT 16:9 | 1280x720 | 标准演示文稿 |
| PPT 4:3 | 1024x768 | 传统投影 |
| 小红书 | 900x1200 | 社交媒体 |
| 故事板 | 1080x1920 | 竖屏展示 |

---

## 技术架构

### 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              前端层 (Frontend)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  Vue 3 + TS │  │ Element Plus│  │    Pinia    │  │   Vue Router    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ HTTP / WebSocket
┌─────────────────────────────────────────────────────────────────────────┐
│                              后端层 (Backend)                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI (ASGI)                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   REST API   │  │  WebSocket   │  │   API Router (v1)    │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │  SQLAlchemy  │  │   Storage    │  │  LangChain Pipeline  │   │   │
│  │  │  (ORM)       │  │   Backend    │  │  (StateGraph)        │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                            任务队列层 (Worker)                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Celery + Redis                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   Pipeline   │  │  Source      │  │    Image Generate    │   │   │
│  │  │   Steps      │  │  Processing  │  │    & Search          │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   Quality    │  │    PPT       │  │    Script Runner     │   │   │
│  │  │   Check      │  │   Export     │  │    (ppt-master)      │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                            数据持久层 (Storage)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │      MinIO (S3-Compatible)   │  │
│  │  (主数据库)   │  │  (缓存/队列)  │  │      (对象存储)              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Vue 3 + TypeScript | ^3.4 |
| UI组件库 | Element Plus | ^2.5 |
| 状态管理 | Pinia | ^2.1 |
| 后端框架 | FastAPI | ^0.104 |
| ORM | SQLAlchemy + asyncpg | ^2.0 |
| 迁移工具 | Alembic | ^1.12 |
| 任务队列 | Celery + Redis | ^5.3 |
| AI框架 | LangChain | ^0.1 |
| 数据库 | PostgreSQL | 15+ |
| 对象存储 | MinIO | latest |
| 容器化 | Docker + Docker Compose | - |

---

## 快速开始

### 前提条件

- [Docker](https://docs.docker.com/get-docker/) 24.0+
- [Docker Compose](https://docs.docker.com/compose/install/) v2.0+
- OpenAI API Key 或 Anthropic API Key

### 1. 克隆代码

```bash
git clone https://github.com/your-org/ppt-master-web.git
cd ppt-master-web
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，设置你的LLM API Key
vim .env
```

`.env` 文件示例：

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
```

### 3. Docker Compose 启动

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 4. 访问Web界面

- **Web界面**: http://localhost
- **API文档**: http://localhost/api/docs (Swagger UI)
- **MinIO控制台**: http://localhost:9001 (默认账号: minioadmin / minioadmin)

### 5. 创建第一个项目

1. 打开 http://localhost 进入Web界面
2. 点击「新建项目」，填写项目名称和描述
3. 上传源文件（PDF、Word等）
4. 点击「启动Pipeline」
5. 等待AI生成Eight Confirmations后确认设计选项
6. Pipeline自动继续执行，完成后下载PPT

---

## 详细安装指南

### 系统要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2核 | 4核+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 20GB | 50GB+ SSD |
| 网络 | 可访问LLM API | 稳定的外网连接 |
| 操作系统 | Linux/macOS/Windows WSL2 | Ubuntu 22.04 LTS |

### 安装Docker和Docker Compose

**Ubuntu/Debian:**

```bash
# 更新包索引
sudo apt-get update

# 安装Docker
sudo apt-get install -y docker.io

# 安装Docker Compose Plugin
sudo apt-get install -y docker-compose-plugin

# 将当前用户添加到docker组（需重新登录生效）
sudo usermod -aG docker $USER

# 验证安装
docker --version
docker compose version
```

**macOS:**

```bash
# 使用Homebrew安装
brew install --cask docker

# 验证安装
docker --version
docker compose version
```

### 配置LLM API Key

本项目依赖大语言模型（LLM）进行内容分析和设计决策，支持以下提供商：

**OpenAI:**

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 创建API Key
3. 确保账户有足够余额

**Anthropic Claude:**

1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 创建API Key

### 启动步骤

```bash
# 1. 克隆项目仓库
git clone https://github.com/your-org/ppt-master-web.git
cd ppt-master-web

# 2. 创建环境变量文件
cat > .env << 'EOF'
# LLM API Keys (至少配置一个)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# 可选：自定义端口
# FRONTEND_PORT=8080
# BACKEND_PORT=8000
EOF

# 3. 启动所有服务
docker-compose up -d

# 4. 等待服务就绪（约30秒）
docker-compose logs -f backend | grep "Application startup complete"

# 5. 初始化数据库（首次启动）
docker-compose exec backend alembic upgrade head

# 6. 验证服务
# 访问 http://localhost 查看Web界面
# 访问 http://localhost/api/docs 查看API文档
curl http://localhost/api/health
```

### 服务端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Web界面 | 80 | Nginx代理的Vue前端 |
| API服务 | 8000 | FastAPI后端（内部） |
| PostgreSQL | 5432 | 数据库（内部） |
| Redis | 6379 | 缓存/队列（内部） |
| MinIO API | 9000 | 对象存储API（内部） |
| MinIO Console | 9001 | MinIO管理界面 |

---

## 使用指南

### 创建项目

1. 登录Web界面，点击「新建项目」
2. 填写项目信息：
   - **项目名称**（必填）：如"Q1季度报告"
   - **项目描述**（可选）：简要描述PPT内容
   - **画布格式**：选择 PPT 16:9 / PPT 4:3 / 小红书 / 故事板
3. 点击「创建」

### 上传源文件

1. 进入项目详情页，点击「上传源文件」
2. 支持以下方式：
   - **本地上传**：拖拽或选择文件（支持多文件）
   - **URL添加**：输入网页链接，系统自动抓取内容
3. 系统会自动将文件转换为Markdown格式
4. 上传完成后，确认文件列表无误

### 启动Pipeline

1. 在项目详情页点击「启动Pipeline」
2. 系统开始执行，Pipeline状态实时显示：
   - 步骤条显示当前进度
   - WebSocket实时推送状态更新
   - 日志区域显示详细执行日志

### 确认Eight Confirmations

当Pipeline执行到Strategist步骤后，系统会生成Eight Confirmations：

1. 页面自动跳转到确认界面
2. 逐项查看AI生成的设计建议：
   - **画布确认** - 页面尺寸和比例
   - **页数确认** - 建议的总页数
   - **受众确认** - 目标受众分析
   - **风格模式** - A/B/C三种风格选项
   - **配色方案** - 主色、辅色、强调色
   - **图标方案** - A/B/C/D四种图标策略
   - **字体方案** - 标题字体、正文字体
   - **图片策略** - AI生成/Web搜索/用户上传
3. 可以修改任何选项，或直接使用AI建议
4. 点击「确认」提交

> **提示**: Eight Confirmations是Pipeline中的关键人工介入点，确保最终PPT符合您的期望。建议仔细审查每个选项。

### 查看SVG页面

Pipeline进入Executor步骤后，系统逐页生成SVG：

1. 点击「页面预览」查看实时生成的SVG页面
2. 每页SVG可以：
   - **预览** - 查看渲染效果
   - **编辑** - 修改SVG代码（高级功能）
   - **质量检查** - 查看检查结果和警告
3. 所有页面生成完成后，进入后处理步骤

### 下载PPT

1. Pipeline完成后，页面显示「导出完成」
2. 点击「下载PPT」获取最终文件
3. 导出的PPT包含：
   - 所有SVG页面转换的幻灯片
   - 演讲者备注
   - 可选的过渡动画效果

---

## 开发指南

### 目录结构说明

```
ppt-master-web/
├── backend/                    # FastAPI后端
│   ├── alembic/               # 数据库迁移
│   │   ├── versions/          # 迁移脚本
│   │   └── env.py             # 迁移环境配置
│   ├── app/                   # 应用代码
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI入口
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   ├── models/            # SQLAlchemy模型
│   │   │   ├── __init__.py
│   │   │   ├── project.py     # 项目模型
│   │   │   ├── source_file.py # 源文件模型
│   │   │   ├── design_spec.py # 设计规范模型
│   │   │   ├── spec_lock.py   # 执行锁模型
│   │   │   ├── image.py       # 图片资源模型
│   │   │   ├── svg_page.py    # SVG页面模型
│   │   │   ├── speaker_note.py# 演讲备注模型
│   │   │   ├── pptx_export.py # PPT导出模型
│   │   │   └── pipeline_job.py# Pipeline作业模型
│   │   ├── schemas/           # Pydantic数据模型
│   │   ├── api/               # API路由
│   │   │   ├── deps.py        # 依赖注入
│   │   │   └── v1/            # API v1
│   │   │       ├── projects.py    # 项目API
│   │   │       ├── sources.py     # 源文件API
│   │   │       ├── design_spec.py # Design Spec API
│   │   │       ├── pipeline.py    # Pipeline API
│   │   │       ├── pages.py       # SVG页面API
│   │   │       ├── exports.py     # PPT导出API
│   │   │       ├── images.py      # 图片API
│   │   │       └── websocket.py   # WebSocket
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── project_service.py
│   │   │   ├── pipeline_service.py
│   │   │   ├── storage_service.py
│   │   │   └── llm_service.py
│   │   ├── core/              # 核心模块
│   │   │   ├── pipeline/      # LangChain Pipeline
│   │   │   │   ├── __init__.py
│   │   │   │   ├── graph.py   # StateGraph定义
│   │   │   │   ├── nodes.py   # Pipeline节点
│   │   │   │   └── state.py   # Pipeline状态
│   │   │   ├── storage/       # 存储抽象层
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py    # 抽象接口
│   │   │   │   ├── minio.py   # MinIO实现
│   │   │   │   └── local.py   # 本地存储实现
│   │   │   └── scripts/       # 原skill脚本包装器
│   │   │       └── runner.py
│   │   ├── celery_app.py      # Celery应用配置
│   │   └── tasks/             # Celery任务
│   │       ├── pipeline.py
│   │       ├── source_processing.py
│   │       ├── image_tasks.py
│   │       └── export.py
│   ├── tests/                 # 测试代码
│   ├── Dockerfile
│   ├── pyproject.toml         # Python依赖
│   └── .env.example           # 环境变量模板
├── frontend/                   # Vue 3前端
│   ├── src/
│   │   ├── components/        # Vue组件
│   │   │   ├── PipelineStatus.vue    # Pipeline状态条
│   │   │   ├── EightConfirmations.vue # 8项确认表单
│   │   │   ├── SVGPreview.vue        # SVG预览组件
│   │   │   ├── ProjectCard.vue       # 项目卡片
│   │   │   ├── SourceUploader.vue    # 源文件上传
│   │   │   ├── ImageManager.vue      # 图片管理
│   │   │   └── ExportList.vue        # 导出列表
│   │   ├── views/             # 页面视图
│   │   │   ├── HomeView.vue
│   │   │   ├── ProjectList.vue
│   │   │   ├── ProjectCreate.vue
│   │   │   ├── ProjectDetail.vue
│   │   │   ├── ConfirmationPage.vue
│   │   │   ├── SVGEditor.vue
│   │   │   ├── PPTPreview.vue
│   │   │   └── SettingsView.vue
│   │   ├── stores/            # Pinia状态管理
│   │   │   └── project.ts
│   │   ├── api/               # API客户端
│   │   │   └── client.ts
│   │   ├── router/            # Vue Router
│   │   │   └── index.ts
│   │   ├── types/             # TypeScript类型
│   │   │   └── index.ts
│   │   ├── App.vue
│   │   └── main.ts
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── docker-compose.yml         # Docker Compose配置
├── .env.example               # 环境变量模板
└── README.md                  # 本文档
```

### 后端开发

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 运行测试
pytest

# 代码格式化
black app/ tests/
isort app/ tests/

# 类型检查
mypy app/
```

### 前端开发

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint
npm run type-check
```

### 数据库迁移

```bash
# 创建新的迁移脚本
docker-compose exec backend alembic revision --autogenerate -m "描述变更"

# 应用迁移
docker-compose exec backend alembic upgrade head

# 回滚一次迁移
docker-compose exec backend alembic downgrade -1

# 查看当前版本
docker-compose exec backend alembic current

# 查看历史
docker-compose exec backend alembic history
```

---

## API文档

启动服务后，可以通过以下地址访问交互式API文档：

- **Swagger UI**: http://localhost/api/docs
- **ReDoc**: http://localhost/api/redoc
- **OpenAPI JSON**: http://localhost/api/openapi.json

API文档由FastAPI自动生成，包含所有端点的请求/响应模型和示例。详细的API说明请参考 [docs/api-guide.md](docs/api-guide.md)。

---

## 环境变量参考

### 必填变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL连接字符串 | `postgresql+asyncpg://pptmaster:pptmaster@db:5432/pptmaster` |
| `REDIS_URL` | Redis连接字符串 | `redis://redis:6379/0` |
| `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY` | LLM API Key | `sk-...` |

### 可选变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `MINIO_ENDPOINT` | MinIO服务地址 | `minio:9000` | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO访问密钥 | `minioadmin` | - |
| `MINIO_SECRET_KEY` | MinIO密钥 | `minioadmin` | - |
| `MINIO_BUCKET` | MinIO存储桶名 | `pptmaster` | - |
| `MINIO_SECURE` | 是否使用HTTPS | `false` | `true` |
| `DEFAULT_LLM_PROVIDER` | 默认LLM提供商 | `openai` | `anthropic` |
| `DEFAULT_LLM_MODEL` | 默认LLM模型 | `gpt-4o` | `claude-3-5-sonnet-20241022` |
| `PPT_MASTER_SKILL_DIR` | ppt-master skill目录 | `/app/ppt-master/skills/ppt-master` | - |
| `LOG_LEVEL` | 日志级别 | `info` | `debug` / `warning` |
| `DEBUG` | 调试模式 | `false` | `true` |
| `BACKEND_CORS_ORIGINS` | CORS允许来源 | `*` | `http://localhost,http://localhost:8080` |

### 开发环境变量

```env
# 数据库（开发环境直连）
DATABASE_URL=postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster

# Redis（开发环境直连）
REDIS_URL=redis://localhost:6379/0

# MinIO（开发环境直连）
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# LLM
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# 调试
DEBUG=true
LOG_LEVEL=debug
```

---

## 常见问题FAQ

### Q1: 启动后无法访问Web界面？

**A**: 请按以下步骤排查：

```bash
# 1. 检查所有容器是否正常运行
docker-compose ps

# 2. 查看各服务日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs db

# 3. 检查端口是否被占用
sudo lsof -i :80
sudo lsof -i :8000

# 4. 重新启动服务
docker-compose down
docker-compose up -d
```

### Q2: LLM API调用失败？

**A**: 检查以下几点：

1. **API Key是否正确** - 确认 `.env` 文件中的 API Key 有效且未过期
2. **网络连接** - 确保服务器可以访问 OpenAI/Anthropic API
3. **账户余额** - 确认 API 账户有足够余额
4. **模型可用性** - 确认所选模型对您的账户可用

```bash
# 测试API连通性
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Q3: Pipeline执行失败如何排查？

**A**: 

1. 在Web界面查看Pipeline状态和错误信息
2. 查看后端日志：`docker-compose logs -f backend`
3. 查看Celery Worker日志：`docker-compose logs -f celery_worker`
4. 在数据库中查看 `pipeline_jobs` 表的 `error_message` 和 `error_traceback` 字段
5. 检查项目状态API：`GET /api/projects/{id}/pipeline/jobs`

### Q4: 如何修改Pipeline中使用的LLM模型？

**A**: 可以通过以下方式修改：

1. **全局默认**：修改 `.env` 文件中的 `DEFAULT_LLM_PROVIDER` 和 `DEFAULT_LLM_MODEL`
2. **项目级别**：创建项目时通过API指定 `llm_provider` 和 `llm_model` 字段
3. **运行时切换**：调用 `PUT /api/projects/{id}` 更新项目配置

支持的模型：

| 提供商 | 可用模型 |
|--------|----------|
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` |
| Anthropic | `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229` |

### Q5: 数据库连接失败？

**A**: 

```bash
# 1. 检查PostgreSQL容器状态
docker-compose ps db

# 2. 检查数据库日志
docker-compose logs db

# 3. 进入数据库容器验证
docker-compose exec db psql -U pptmaster -d pptmaster -c "\dt"

# 4. 确保迁移已应用
docker-compose exec backend alembic upgrade head
```

### Q6: 如何备份数据？

**A**: 

```bash
# 备份数据库
docker-compose exec db pg_dump -U pptmaster pptmaster > backup_$(date +%Y%m%d).sql

# 备份MinIO数据
docker run --rm -v ppt-master-web_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup.tar.gz -C /data .

# 恢复数据库
docker-compose exec -T db psql -U pptmaster -d pptmaster < backup_20240101.sql
```

### Q7: 如何清理未完成的Pipeline？

**A**: 

```bash
# 通过Web界面取消
# 或调用API

curl -X POST http://localhost/api/projects/{project_id}/cancel

# 如需强制重置状态
curl -X PUT http://localhost/api/projects/{project_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "draft", "current_step": "init", "step_status": "pending"}'
```

### Q8: 文件上传大小有限制吗？

**A**: 

- 默认单文件上传限制为 **100MB**
- 如需调整，修改后端 `config.py` 中的 `MAX_UPLOAD_SIZE` 配置
- 建议单个PDF文件不超过 **50MB**，以确保转换效率

---

## 贡献指南

我们欢迎所有形式的贡献，包括但不限于：

- 提交Bug报告
- 提交功能请求
- 提交代码（Pull Request）
- 改进文档
- 分享使用经验

### 开发流程

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 代码规范

- **Python**: 使用 Black 格式化，遵循 PEP 8
- **TypeScript**: 使用 ESLint + Prettier
- **提交信息**: 使用 [Conventional Commits](https://conventionalcommits.org/) 规范

### 测试要求

- 新增功能必须包含单元测试
- 所有测试通过后才能合并
- 保持代码覆盖率不低于 80%

```bash
# 运行测试
pytest

# 检查覆盖率
pytest --cov=app --cov-report=html
```

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

```
MIT License

Copyright (c) 2024 PPT Master Web Service

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 相关资源

- [架构说明文档](docs/architecture.md) - 系统架构和技术选型详细说明
- [API使用指南](docs/api-guide.md) - 完整的API接口文档
- [Pipeline使用指南](docs/pipeline-guide.md) - Pipeline工作流详细说明
- [开发文档](docs/development.md) - 开发环境搭建和调试指南
- [ppt-master (原始Skill)](https://github.com/hugohe3/ppt-master) - 原始命令行工具

---

**PPT Master Web Service** - 让PPT制作更智能、更高效