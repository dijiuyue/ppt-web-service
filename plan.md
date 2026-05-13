# PPT Master Web Service - 项目计划

## 目标
将 https://github.com/hugohe3/ppt-master (PPT生成Skill) 改造为前后端分离的Web服务。

## 技术分析

### 原Skill核心Pipeline (7 Steps)
```
Source Document → Create Project → [Template] → Strategist → [Image_Generator] → Executor → Post-processing → Export
```

### 中间产物映射到数据库
| Step | 中间产物 | DB表 | 说明 |
|------|---------|------|------|
| 1 | sources/*.md | source_files | 源文件内容(BLOB) + 转换后markdown |
| 2 | 项目目录结构 | projects | 项目元数据 |
| 3 | templates/*.svg | project_templates | 模板配置引用 |
| 4 | design_spec.md | design_specs | 设计规范(全文) |
| 4 | spec_lock.md | spec_locks | 执行锁(全文) |
| 5 | images/*, image_prompts.md | image_resources | 图片资源表 + 文件存储 |
| 6 | svg_output/*.svg | svg_pages | SVG页面内容(CLOB) |
| 6 | notes/total.md | speaker_notes | 演讲者备注 |
| 7 | exports/*.pptx | pptx_exports | 导出文件(BLOB) |

### 关键难点
1. **文件系统抽象**: 原skill大量使用文件系统作为中间产物传递介质，需要抽象为DB+对象存储
2. **LangChain工作流编排**: 7个step串行执行，Step 4有BLOCKING用户确认点
3. **脚本集成**: 复用原skill的Python脚本(pdf_to_md, svg_to_pptx等)
4. **状态管理**: Pipeline状态机设计

## 技术栈
- **前端**: Vue 3 + TypeScript + Element Plus
- **后端**: FastAPI + LangChain + SQLAlchemy + Celery (异步任务)
- **数据库**: PostgreSQL (主) + MinIO/S3 (对象存储)
- **LLM**: OpenAI/Anthropic API (服务端配置)
- **消息队列**: Redis + Celery

## 执行计划

### Stage 1: 架构设计与基础框架 (并行)
- 1a: 数据库模型设计 (SQLAlchemy models)
- 1b: FastAPI项目骨架 + API路由设计
- 1c: 文件存储抽象层 (兼容本地文件系统和对象存储)
- 1d: LangChain Pipeline工作流编排框架

### Stage 2: 核心Pipeline实现 (串行)
- 2a: Step 1-2 (Source Processing + Project Init)
- 2b: Step 4 (Strategist Phase - 含BLOCKING确认)
- 2c: Step 5 (Image Acquisition)
- 2d: Step 6 (Executor - SVG Generation)
- 2e: Step 7 (Post-processing + Export)

### Stage 3: 前端开发 (并行)
- 3a: Vue项目搭建 + 基础UI组件
- 3b: 项目创建/列表页面
- 3c: Design Spec确认页面 (Eight Confirmations)
- 3d: Pipeline进度追踪页面
- 3e: PPT预览/下载页面

### Stage 4: 集成与部署
- 4a: Docker Compose配置
- 4b: 集成测试
- 4c: 文档

## Skill依赖
- 使用 `vibecoding-general-swarm` 技能进行代码开发
