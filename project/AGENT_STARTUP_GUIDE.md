# PPT Master Web Service - Agent 启动验证指南

> **目标读者**: AI Agent (Kimi / Claude / GPT 等)
> **文档目的**: 让 Agent 能够独立完成项目的启动、验证和修复
> **项目路径**: `/mnt/agents/output/ppt-web-service/project`

---

## 1. 项目概览 (1分钟了解)

### 1.1 一句话描述
PPT Master Web Service 是一个基于 AI 的智能 PPT 生成 Web 服务，通过 LLM 驱动的 LangGraph Pipeline 将源文件自动转换为专业演示文稿。

### 1.2 技术栈清单

| 层级 | 技术 | 版本要求 |
|------|------|----------|
| 前端框架 | Vue 3 + TypeScript | ^3.4 |
| 构建工具 | Vite | ^5.0 |
| UI 组件库 | Element Plus | ^2.5 |
| 状态管理 | Pinia | ^2.1 |
| 路由 | Vue Router | ^4.2 |
| 后端框架 | FastAPI | ^0.110 |
| ORM | SQLAlchemy (async) + asyncpg | ^2.0 |
| 迁移工具 | Alembic | ^1.13 |
| 任务队列 | Celery + Redis | ^5.3 |
| AI Pipeline | LangGraph + LangChain | - |
| LLM 客户端 | OpenAI + Anthropic | - |
| 对象存储 | MinIO / 本地文件系统 | - |
| 数据库 | PostgreSQL (推荐) / SQLite | 15+ |

### 1.3 目录结构速览

```
project/
├── AGENT_STARTUP_GUIDE.md    # 本文档
├── verify_setup.py            # 一键验证脚本
├── check_imports.py           # 模块导入检查脚本
├── README.md                  # 人类用户文档
├── docker/                    # Docker 配置
│   ├── docker-compose.dev.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── backend/                   # FastAPI 后端
│   ├── requirements.txt       # Python 依赖
│   ├── alembic/               # 数据库迁移
│   │   └── env.py
│   └── app/                   # 应用代码
│       ├── main.py            # FastAPI 入口
│       ├── core/              # 核心模块
│       │   ├── config.py      # 配置管理
│       │   ├── database.py    # 数据库连接
│       │   ├── schemas.py     # Pydantic 模型
│       │   ├── security.py    # 安全工具
│       │   └── celery_app.py  # Celery 配置
│       ├── db/
│       │   └── base.py        # SQLAlchemy Base
│       ├── models/            # ORM 模型 (9个)
│       │   ├── __init__.py
│       │   ├── project.py
│       │   ├── source_file.py
│       │   ├── design_spec.py
│       │   ├── spec_lock.py
│       │   ├── image_resource.py
│       │   ├── svg_page.py
│       │   ├── speaker_note.py
│       │   └── pipeline_job.py
│       │   └── pptx_export.py
│       ├── api/               # API 路由
│       │   ├── __init__.py    # 路由注册
│       │   ├── deps.py        # 依赖注入
│       │   ├── projects.py    # 项目 CRUD
│       │   ├── sources.py     # 源文件管理
│       │   ├── design_spec.py # Design Spec
│       │   ├── pipeline.py    # Pipeline 控制
│       │   ├── svg_pages.py   # SVG 页面
│       │   ├── exports.py     # PPTX 导出
│       │   ├── images.py      # 图片资源
│       │   └── websocket.py   # WebSocket
│       ├── services/          # 业务逻辑
│       │   ├── project_service.py
│       │   ├── source_service.py
│       │   ├── design_spec_service.py
│       │   ├── pipeline_service.py
│       │   └── storage_service.py
│       ├── storage/           # 存储抽象
│       │   ├── base.py
│       │   ├── local.py
│       │   ├── minio.py
│       │   └── manager.py
│       └── pipeline/          # LangGraph Pipeline
│           ├── __init__.py
│           ├── constants.py   # 常量和配置
│           ├── state.py       # Pipeline 状态定义
│           ├── graph.py       # StateGraph 构建
│           ├── nodes.py       # Pipeline 节点
│           ├── llm.py         # LLM 客户端
│           ├── prompts.py     # LLM Prompts
│           ├── script_runner.py # 脚本包装器
│           ├── workspace.py   # 临时工作区
│           └── tasks.py       # Celery 任务
└── frontend/                  # Vue 3 前端
    ├── package.json
    ├── vite.config.ts         # Vite 配置(端口5173)
    └── src/
        ├── main.ts            # 入口
        ├── App.vue
        ├── router/index.ts    # 路由
        ├── stores/project.ts  # Pinia Store
        ├── api/               # API 客户端
        ├── components/        # Vue 组件
        └── views/             # 页面视图
```

---

## 2. 启动检查清单 (按顺序执行)

### Step 1: 环境检查

```bash
# 1.1 检查 Python 版本 (>= 3.10)
python3 --version
# 预期: Python 3.10.x 或更高

# 1.2 检查 Node.js 版本 (>= 18)
node --version
# 预期: v18.x 或更高

# 1.3 检查可用的包管理器
pip --version      # 或 pip3
npm --version

# 1.4 确认项目路径存在
ls -la /mnt/agents/output/ppt-web-service/project/
```

### Step 2: 后端启动

#### 2.1 安装 Python 依赖

```bash
cd /mnt/agents/output/ppt-web-service/project/backend

# 方式A: 一次性安装 (可能超时)
pip install -r requirements.txt

# 方式B: 逐个安装 (推荐，避免超时)
pip install fastapi uvicorn python-multipart
pip install sqlalchemy asyncpg alembic
pip install pydantic pydantic-settings
pip install minio
pip install celery redis
pip install openai anthropic
pip install langchain langchain-openai
pip install langgraph              # 关键: 不在 requirements.txt 中
pip install tenacity               # 关键: 不在 requirements.txt 中
pip install aiofiles python-magic Pillow requests httpx
pip install kombu                  # Celery 依赖
```

#### 2.2 验证关键导入

```python
import sys
sys.path.insert(0, "/mnt/agents/output/ppt-web-service/project/backend")

# 测试核心模块
from app.models import Project, SourceFile  # 应 OK
from app.api import api_router             # 应 OK (如果 deps.py 导入已修复)
from app.core.schemas import ProjectStatus, PipelineStep  # 应 OK
from app.pipeline.graph import PPTMasterPipeline, get_pipeline  # 需要 langgraph
```

#### 2.3 运行导入检查脚本

```bash
cd /mnt/agents/output/ppt-web-service/project
python3 check_imports.py
# 预期: 大部分模块 OK
# pipeline 相关模块可能需要 langgraph 安装后才能通过
```

### Step 3: 前端启动

```bash
cd /mnt/agents/output/ppt-web-service/project/frontend

# 3.1 安装依赖
npm install

# 3.2 启动开发服务器
npm run dev
# 预期输出:
#   VITE v5.x  ready in xxx ms
#   Local:   http://localhost:5173/
#   Network: http://0.0.0.0:5173/
```

### Step 4: 验证方法

#### 4.1 使用验证脚本

```bash
cd /mnt/agents/output/ppt-web-service/project
python3 verify_setup.py
# 这会输出彩色报告，显示所有检查项的状态
```

#### 4.2 手动验证后端服务

```bash
cd /mnt/agents/output/ppt-web-service/project/backend

# 设置环境变量 (开发模式)
export DEBUG=true
export DATABASE_URL="postgresql+asyncpg://pptmaster:pptmaster@localhost:5432/pptmaster"
# 如果没有 PostgreSQL，使用 SQLite:
# export DATABASE_URL="sqlite+aiosqlite:///./pptmaster.db"

# 启动后端
uvicorn app.main:app --reload --port 8000
```

#### 4.3 测试健康检查端点

```bash
# 健康检查
curl http://localhost:8000/health
# 预期: {"status":"ok","version":"0.1.0","services":{...}}

# API 文档
curl http://localhost:8000/openapi.json
# 预期: 返回 OpenAPI JSON

# Swagger UI (浏览器访问)
# http://localhost:8000/docs
```

---

## 3. 已知问题与修复 (非常重要)

> 以下问题在实际代码验证中发现。每个问题都有 **症状-诊断-修复** 三段式说明。
> **当前代码状态**: 部分问题已修复，部分仍存在。Agent 应按此指南检查并修复。

### 问题 1: `storage_service.py` 缺少 `Any` 导入

- **文件**: `backend/app/services/storage_service.py`
- **状态**: 已修复 (当前代码第14行已有 `from typing import Any, Optional`)
- **症状**: `NameError: name 'Any' is not defined`
  ```
  File ".../storage_service.py", line 277, in initialize
      def initialize(cls, backend_type: str = "local", **kwargs: Any) -> StorageBackend:
  NameError: name 'Any' is not defined
  ```
- **诊断**: `typing` 模块导入缺少 `Any`
- **修复**: 确保第14行包含 `Any`:
  ```python
  from typing import Any, Optional  # 确保 Any 已导入
  ```

### 问题 2: `deps.py` 缺少 `Any` 导入

- **文件**: `backend/app/api/deps.py`
- **状态**: 已修复 (当前代码第12行已有 `from typing import Any, AsyncGenerator, Optional`)
- **症状**: API 模块级联导入失败
  ```
  File ".../deps.py", line 23, in <module>
      _db_session_factory: Optional[Any] = None
  NameError: name 'Any' is not defined
  ```
- **诊断**: `typing` 模块导入缺少 `Any`
- **修复**: 确保第12行包含 `Any`:
  ```python
  from typing import Any, AsyncGenerator, Optional  # 确保 Any 已导入
  ```

### 问题 3: `design_spec_service.py` 错误的 `SpecLock` 导入路径

- **文件**: `backend/app/services/design_spec_service.py`
- **状态**: 已修复 (当前代码第20行已是正确路径)
- **症状**: `ImportError: cannot import name 'SpecLock' from 'app.core.schemas'`
  ```
  ImportError: cannot import name 'SpecLock' from 'app.core.schemas'
  ```
- **诊断**: `SpecLock` 是 ORM 模型，不在 `schemas` 模块中，应在 `app.models.spec_lock`
- **修复**: 确保第20行:
  ```python
  from app.models.spec_lock import SpecLock  # 正确的导入路径
  ```

### 问题 4: `requirements.txt` 缺失 `langgraph` 和 `tenacity`

- **文件**: `backend/requirements.txt`
- **状态**: 未修复 (需要 Agent 手动安装)
- **症状 A**: Pipeline 模块导入失败
  ```
  ModuleNotFoundError: No module named 'langgraph'
  # 影响: app/pipeline/graph.py 导入失败
  ```
- **症状 B**: LLM 客户端导入失败
  ```
  ModuleNotFoundError: No module named 'tenacity'
  # 影响: app/pipeline/llm.py 导入失败
  ```
- **诊断**: `langgraph` 和 `tenacity` 被代码使用但不在 requirements.txt 中
- **修复**:
  ```bash
  pip install langgraph tenacity kombu
  # 或使用 --no-cache-dir 避免超时:
  pip install --no-cache-dir langgraph
  pip install --no-cache-dir tenacity
  pip install --no-cache-dir kombu
  ```

### 问题 5: 运行时缺少 PostgreSQL

- **文件**: `backend/app/main.py`, `backend/app/core/database.py`
- **状态**: 可配置
- **症状**: 数据库连接失败
  ```
  ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 5432)
  # 或 asyncpg 相关错误
  ```
- **诊断**: 默认配置使用 PostgreSQL+asyncpg，但数据库服务未运行
- **修复方案 A**: 使用 SQLite 内存模式 (仅用于快速验证)
  ```bash
  export DATABASE_URL="sqlite+aiosqlite:///./pptmaster.db"
  export AUTO_CREATE_TABLES="true"
  ```
- **修复方案 B**: 使用 SQLite 文件模式
  ```bash
  export DATABASE_URL="sqlite+aiosqlite:///./pptmaster.db"
  export STORAGE_BACKEND="local"
  export LOCAL_STORAGE_DIR="./storage"
  ```
- **修复方案 C**: 启动 PostgreSQL (Docker)
  ```bash
  docker run -d --name pptmaster-db \
    -e POSTGRES_USER=pptmaster \
    -e POSTGRES_PASSWORD=pptmaster \
    -e POSTGRES_DB=pptmaster \
    -p 5432:5432 \
    postgres:15
  ```

### 问题 6: `pipeline_service.py` 使用 `get_sync_session` (不存在)

- **文件**: `backend/app/services/pipeline_service.py`
- **状态**: 未修复
- **位置**: 第428行 `from app.models.database import get_sync_session`
- **症状**: Celery 任务执行时失败
  ```
  ModuleNotFoundError: No module named 'app.models.database'
  # 或 ImportError: cannot import name 'get_sync_session'
  ```
- **诊断**: `app.models.database` 模块不存在。同步会话需要通过其他方式获取
- **修复**: 这是一个运行时问题，仅在 Celery worker 执行任务时触发。
  当前代码底部的 `timedelta` 导入已通过 try/except 保护 (第541-544行)。
  对于 `get_sync_session` 的引用，需要在实际部署时添加同步会话支持。
  **快速验证时**: 此问题不影响后端导入检查，可以暂时忽略。

### 问题 7: `nodes.py` 和 `tasks.py` 使用错误导入路径

- **文件**: `backend/app/pipeline/nodes.py`, `backend/app/pipeline/tasks.py`
- **状态**: 未修复 (懒导入，仅在运行时触发)
- **涉及导入**:
  - `from app.database import async_session_factory` -> 应为 `from app.core.database import get_session_maker`
  - `from app.storage import get_storage_backend` -> 应为 `from app.services.storage_service import get_storage_backend`
  - `from app.websocket import ws_manager` -> 应为 `from app.api.websocket import ws_manager`
  - `from app.models.database import get_sync_session` -> 模块不存在
  - `from app.celery_app import app` -> 应为 `from app.core.celery_app import celery_app`
- **症状**: Pipeline 实际运行时失败
- **诊断**: 这些是函数内部的懒导入 (lazy import)，不会导致模块级导入失败。
  只有在实际执行 pipeline 节点时才会触发。
- **修复**: 运行 full pipeline 前需要修复这些路径。
  **快速验证时**: 此问题不影响导入检查，可以暂时忽略。

---

## 4. 快速修复命令

### 依赖安装

```bash
# 核心依赖 (必须)
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic
pip install pydantic pydantic-settings python-multipart
pip install langchain langchain-openai langgraph tenacity kombu

# 存储和任务队列
pip install minio celery redis

# LLM 客户端
pip install openai anthropic httpx

# 工具库
pip install aiofiles python-magic Pillow requests

# 开发依赖 (可选)
pip install pytest pytest-asyncio black ruff mypy
```

### 环境变量配置

```bash
# 开发环境快速配置
export DEBUG=true
export LOG_LEVEL=debug
export DATABASE_URL="sqlite+aiosqlite:///./pptmaster.db"  # 无 PostgreSQL 时使用
export STORAGE_BACKEND="local"
export LOCAL_STORAGE_DIR="./storage"
export REDIS_URL="redis://localhost:6379/0"
export API_KEY=""  # 开发模式留空
```

### 后端启动命令

```bash
cd /mnt/agents/output/ppt-web-service/project/backend

# 方式1: 直接启动 (开发)
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

# 方式2: 使用环境变量
DEBUG=true STORAGE_BACKEND=local uvicorn app.main:app --port 8000
```

### 前端启动命令

```bash
cd /mnt/agents/output/ppt-web-service/project/frontend
npm install
npm run dev  # 启动在 http://localhost:5173
```

### 数据库初始化 (SQLite 模式)

```bash
cd /mnt/agents/output/ppt-web-service/project/backend
export DATABASE_URL="sqlite+aiosqlite:///./pptmaster.db"
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from app.core.database import init_db
asyncio.run(init_db())
print('Tables created')
"
```

---

## 5. 文件清单 (核心文件速查)

### 5.1 后端核心文件

| 文件路径 | 用途 | 优先级 |
|---------|------|--------|
| `backend/app/main.py` | FastAPI 应用入口 | 必需 |
| `backend/app/core/config.py` | 配置管理 (pydantic-settings) | 必需 |
| `backend/app/core/database.py` | 数据库引擎和会话 | 必需 |
| `backend/app/core/schemas.py` | Pydantic v2 请求/响应模型 | 必需 |
| `backend/app/core/celery_app.py` | Celery 配置 | 必需 |
| `backend/app/db/base.py` | SQLAlchemy Base | 必需 |
| `backend/app/models/__init__.py` | 模型导出 | 必需 |
| `backend/app/models/project.py` | 项目 ORM 模型 | 必需 |
| `backend/app/api/__init__.py` | API 路由注册 | 必需 |
| `backend/app/api/deps.py` | 依赖注入 (DB/Storage) | 必需 |
| `backend/app/services/storage_service.py` | 存储抽象层 | 必需 |
| `backend/app/pipeline/graph.py` | LangGraph StateGraph | 需 langgraph |
| `backend/app/pipeline/nodes.py` | Pipeline 节点实现 | 运行时需修复导入 |
| `backend/app/pipeline/llm.py` | LLM 客户端封装 | 需 tenacity |
| `backend/app/pipeline/state.py` | Pipeline 状态定义 | 必需 |
| `backend/app/pipeline/constants.py` | 常量配置 | 必需 |

### 5.2 前端核心文件

| 文件路径 | 用途 | 优先级 |
|---------|------|--------|
| `frontend/package.json` | 依赖定义 | 必需 |
| `frontend/vite.config.ts` | Vite 配置 (代理/API) | 必需 |
| `frontend/src/main.ts` | 应用入口 | 必需 |
| `frontend/src/App.vue` | 根组件 | 必需 |
| `frontend/src/router/index.ts` | 路由配置 | 必需 |
| `frontend/src/api/client.ts` | API 客户端 (axios) | 必需 |

### 5.3 配置和工具文件

| 文件路径 | 用途 | 优先级 |
|---------|------|--------|
| `backend/requirements.txt` | Python 依赖清单 | 必需 |
| `docker/docker-compose.dev.yml` | 开发环境编排 | 可选 |
| `AGENT_STARTUP_GUIDE.md` | 本文档 | 参考 |
| `verify_setup.py` | 一键验证脚本 | 工具 |
| `check_imports.py` | 模块导入检查 | 工具 |

---

## 6. 验证成功标准

Agent 完成以下所有步骤即为验证成功:

- [ ] Python >= 3.10 已安装
- [ ] Node.js >= 18 已安装
- [ ] pip 和 npm 可用
- [ ] `pip install` 完成 (所有依赖安装成功)
- [ ] `python3 check_imports.py` 核心模块全部 OK
- [ ] `npm install` 完成
- [ ] `npm run dev` 启动成功 (端口 5173)
- [ ] 后端 `uvicorn app.main:app` 启动成功 (端口 8000)
- [ ] `curl http://localhost:8000/health` 返回 200
- [ ] `curl http://localhost:8000/openapi.json` 返回 JSON
- [ ] `python3 verify_setup.py` 全部检查通过

---

## 7. 常见问题速查

### Q1: `pip install` 超时怎么办?
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 或使用 --no-cache-dir
pip install --no-cache-dir -r requirements.txt
# 或逐个安装
for pkg in fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings minio celery redis openai anthropic langchain langchain-openai langgraph tenacity; do
    pip install "$pkg" || echo "Failed: $pkg"
done
```

### Q2: `langgraph` 安装特别慢?
```bash
# langgraph 依赖较多，使用 --no-cache-dir 并增加超时时间
pip install --no-cache-dir --timeout 300 langgraph
# 或者先安装其依赖
pip install langchain langchain-core langgraph-checkpoint
pip install --no-cache-dir langgraph
```

### Q3: 前端 `npm install` 失败?
```bash
# 清除缓存重试
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# 或使用 yarn
yarn install
```

### Q4: 后端启动报数据库错误?
```bash
# 切换到 SQLite 模式 (无需 PostgreSQL)
export DATABASE_URL="sqlite+aiosqlite:///./pptmaster.db"
export AUTO_CREATE_TABLES="true"
# 确保安装了 aiosqlite
pip install aiosqlite
```

### Q5: 端口被占用?
```bash
# 检查占用
lsof -i :8000  # 后端端口
lsof -i :5173  # 前端端口
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# 更换端口
uvicorn app.main:app --port 8080
# 前端修改 vite.config.ts 中的 port
```

### Q6: `ModuleNotFoundError: No module named 'xxx'`?
```bash
# 通用修复: 安装缺失的模块
pip install xxx

# 常见缺失模块:
pip install langgraph tenacity kombu aiosqlite
```

---

> **文档版本**: 1.0
> **最后更新**: 2024
> **编写说明**: 本文档由 Agent 验证过程中发现的问题整理而成，供后续 Agent 参考使用。
