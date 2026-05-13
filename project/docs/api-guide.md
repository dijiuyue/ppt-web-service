# PPT Master Web Service - API使用指南

> 完整的RESTful API文档，包含所有端点、请求/响应示例和错误处理说明。

---

## 目录

- [认证方式](#认证方式)
- [基础URL](#基础url)
- [通用规范](#通用规范)
- [项目API](#项目api)
- [源文件API](#源文件api)
- [Design Spec API](#design-spec-api)
- [Pipeline API](#pipeline-api)
- [SVG页面API](#svg页面api)
- [PPT导出API](#ppt导出api)
- [图片资源API](#图片资源api)
- [WebSocket使用说明](#websocket使用说明)
- [错误码说明](#错误码说明)

---

## 认证方式

> **注意**: 当前版本为内部部署服务，暂未实现用户认证系统。所有API无需认证即可访问。
> 
> 如需添加认证，可通过Nginx层配置Basic Auth或使用API Key。

### Nginx Basic Auth（临时方案）

```nginx
# nginx.conf
location /api {
    auth_basic "PPT Master API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://backend:8000;
}
```

### API Key认证（推荐方案）

如需在后端实现API Key认证，可在请求头中添加：

```
X-API-Key: your-api-key-here
```

---

## 基础URL

| 环境 | 基础URL |
|------|---------|
| 开发环境 | `http://localhost:8000` |
| 生产环境（Docker） | `http://localhost/api` |

所有API端点均基于以上URL。本文档示例使用 `/api` 作为前缀。

---

## 通用规范

### 请求格式

- **Content-Type**: `application/json`（除文件上传外）
- **字符编码**: UTF-8
- **日期格式**: ISO 8601 (`2024-01-15T10:30:00Z`)

### 响应格式

所有响应遵循统一的包装格式：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 分页参数

列表接口支持以下分页参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页数量（最大100） |

分页响应格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

### ID格式

所有资源ID使用 **UUID v4** 格式，例如：`550e8400-e29b-41d4-a716-446655440000`

---

## 项目API

基础路径: `/api/projects`

### 1. 创建项目

**POST** `/api/projects`

创建新的PPT项目。

#### 请求参数

```json
{
  "name": "Q1季度报告",
  "description": "2024年第一季度业务总结报告",
  "canvas_format": "ppt169",
  "llm_provider": "openai",
  "llm_model": "gpt-4o"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 项目名称（2-100字符） |
| `description` | string | ❌ | 项目描述（最大500字符） |
| `canvas_format` | string | ❌ | 画布格式：`ppt169`/`ppt43`/`xhs`/`story`，默认`ppt169` |
| `llm_provider` | string | ❌ | LLM提供商：`openai`/`anthropic`，默认`openai` |
| `llm_model` | string | ❌ | LLM模型名称，默认`gpt-4o` |

#### 响应示例

**成功 (201 Created)**

```json
{
  "code": 201,
  "message": "Project created successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Q1季度报告",
    "description": "2024年第一季度业务总结报告",
    "canvas_format": "ppt169",
    "status": "draft",
    "current_step": "init",
    "step_status": "pending",
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "template_path": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "completed_at": null
  }
}
```

### 2. 项目列表

**GET** `/api/projects`

获取项目列表，支持分页和状态筛选。

#### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页数量 |
| `status` | string | - | 筛选状态：`draft`/`confirming`/`processing`/`completed`/`failed` |
| `sort` | string | `-created_at` | 排序字段，`-`前缀表示降序 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Q1季度报告",
        "description": "2024年第一季度业务总结报告",
        "canvas_format": "ppt169",
        "status": "confirming",
        "current_step": "strategist",
        "step_status": "waiting_confirmation",
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "source_count": 2,
        "page_count": 0,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:35:00Z",
        "completed_at": null
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

### 3. 项目详情

**GET** `/api/projects/{id}`

获取单个项目的详细信息，包含关联数据。

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 项目ID |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Q1季度报告",
    "description": "2024年第一季度业务总结报告",
    "canvas_format": "ppt169",
    "status": "confirming",
    "current_step": "strategist",
    "step_status": "waiting_confirmation",
    "llm_provider": "openai",
    "llm_model": "gpt-4o",
    "template_path": null,
    "source_files": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "original_filename": "report.pdf",
        "file_type": "pdf",
        "file_size": 2048576,
        "conversion_status": "completed",
        "sort_order": 0,
        "created_at": "2024-01-15T10:32:00Z"
      }
    ],
    "design_spec": {
      "confirmation_status": "pending",
      "confirmation_page_count": 15,
      "confirmation_style_mode": "A"
    },
    "svg_pages_count": 0,
    "exports_count": 0,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "completed_at": null
  }
}
```

### 4. 更新项目

**PUT** `/api/projects/{id}`

更新项目基本信息。

#### 请求参数

```json
{
  "name": "Q1季度报告（修订版）",
  "description": "更新描述信息",
  "llm_model": "claude-3-5-sonnet-20241022",
  "llm_provider": "anthropic"
}
```

> **注意**: `status`、`current_step`、`step_status` 等Pipeline相关字段不能直接通过此接口修改，需要通过Pipeline控制接口操作。

#### 响应示例

```json
{
  "code": 200,
  "message": "Project updated successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Q1季度报告（修订版）",
    "description": "更新描述信息",
    "llm_provider": "anthropic",
    "llm_model": "claude-3-5-sonnet-20241022",
    "updated_at": "2024-01-15T10:40:00Z"
  }
}
```

### 5. 删除项目

**DELETE** `/api/projects/{id}`

删除项目及其所有关联数据（源文件、SVG页面、导出文件等）。

#### 响应示例

```json
{
  "code": 200,
  "message": "Project deleted successfully",
  "data": null
}
```

### 6. 启动Pipeline

**POST** `/api/projects/{id}/start`

启动或恢复项目的Pipeline。

#### 请求参数

```json
{
  "from_step": "init"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `from_step` | string | ❌ | 起始步骤，默认从`init`开始 |

#### 响应示例

```json
{
  "code": 200,
  "message": "Pipeline started",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "source_processing",
    "step_status": "running",
    "celery_task_id": "abc123-def456"
  }
}
```

### 7. 取消Pipeline

**POST** `/api/projects/{id}/cancel`

取消当前正在执行的Pipeline。

#### 响应示例

```json
{
  "code": 200,
  "message": "Pipeline cancelled",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "draft",
    "current_step": "init",
    "step_status": "pending"
  }
}
```

---

## 源文件API

基础路径: `/api/projects/{project_id}/sources`

### 1. 上传源文件

**POST** `/api/projects/{project_id}/sources/upload`

上传源文件到项目。支持多文件同时上传。

#### 请求格式

`Content-Type: multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | File[] | ✅ | 文件列表（支持PDF/DOCX/XLSX/PPTX/MD/TXT/HTML/EPUB） |
| `sort_order` | int | ❌ | 排序顺序，默认按上传顺序 |

#### cURL示例

```bash
curl -X POST http://localhost/api/projects/{project_id}/sources/upload \
  -F "files=@/path/to/report.pdf" \
  -F "files=@/path/to/data.xlsx" \
  -F "sort_order=0"
```

#### 响应示例

```json
{
  "code": 200,
  "message": "Files uploaded successfully",
  "data": {
    "uploaded": [
      {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "original_filename": "report.pdf",
        "file_type": "pdf",
        "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/sources/660e8400-e29b-41d4-a716-446655440001/report.pdf",
        "file_size": 2048576,
        "conversion_status": "pending",
        "sort_order": 0,
        "created_at": "2024-01-15T10:32:00Z"
      },
      {
        "id": "660e8400-e29b-41d4-a716-446655440002",
        "original_filename": "data.xlsx",
        "file_type": "xlsx",
        "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/sources/660e8400-e29b-41d4-a716-446655440002/data.xlsx",
        "file_size": 512000,
        "conversion_status": "pending",
        "sort_order": 1,
        "created_at": "2024-01-15T10:32:00Z"
      }
    ],
    "failed": []
  }
}
```

### 2. 添加URL源

**POST** `/api/projects/{project_id}/sources/url`

添加网页URL作为源内容，系统会自动抓取页面内容。

#### 请求参数

```json
{
  "url": "https://example.com/article",
  "title": "示例文章",
  "sort_order": 2
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | ✅ | 网页URL（必须有效的http/https链接） |
| `title` | string | ❌ | 自定义标题 |
| `sort_order` | int | ❌ | 排序顺序 |

#### 响应示例

```json
{
  "code": 200,
  "message": "URL source added",
  "data": {
    "id": "660e8400-e29b-41d4-a716-446655440003",
    "original_filename": "example.com_article.html",
    "file_type": "url",
    "source_url": "https://example.com/article",
    "file_size": 0,
    "conversion_status": "processing",
    "sort_order": 2,
    "created_at": "2024-01-15T10:33:00Z"
  }
}
```

### 3. 源文件列表

**GET** `/api/projects/{project_id}/sources`

获取项目的所有源文件。

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "original_filename": "report.pdf",
      "file_type": "pdf",
      "file_size": 2048576,
      "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/sources/660e8400-e29b-41d4-a716-446655440001/report.pdf",
      "markdown_content": "# Q1季度报告\n\n## 概述\n本季度业绩...",
      "markdown_storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/sources/660e8400-e29b-41d4-a716-446655440001/converted.md",
      "conversion_status": "completed",
      "conversion_error": null,
      "sort_order": 0,
      "created_at": "2024-01-15T10:32:00Z"
    }
  ]
}
```

### 4. 删除源文件

**DELETE** `/api/projects/{project_id}/sources/{source_id}`

删除指定的源文件。

#### 响应示例

```json
{
  "code": 200,
  "message": "Source file deleted",
  "data": null
}
```

---

## Design Spec API

基础路径: `/api/projects/{project_id}/design-spec`

### 1. 获取Design Spec

**GET** `/api/projects/{project_id}/design-spec`

获取项目的Design Spec完整内容。

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440001",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "confirmation_status": "pending",
    "confirmation_canvas": "ppt169",
    "confirmation_page_count": 15,
    "confirmation_audience": "高管团队",
    "confirmation_style_mode": "A",
    "confirmation_style_descriptor": "简洁专业风格，注重数据呈现",
    "confirmation_color_scheme": {
      "primary": "#1a1a2e",
      "secondary": "#16213e",
      "accent": "#e94560",
      "background": "#ffffff",
      "text": "#333333"
    },
    "confirmation_icon_approach": "B",
    "confirmation_typography": {
      "title_font": "Noto Sans SC",
      "body_font": "Noto Sans SC",
      "title_size": "32px",
      "body_size": "16px"
    },
    "confirmation_image_approach": "C",
    "spec_content": "# Design Spec\n\n## 画布\n1280x720 (16:9)...",
    "spec_storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/design_spec.md",
    "confirmed_at": null,
    "created_at": "2024-01-15T10:35:00Z",
    "updated_at": "2024-01-15T10:35:00Z"
  }
}
```

### 2. 获取Eight Confirmations

**GET** `/api/projects/{project_id}/design-spec/confirmations`

单独获取Eight Confirmations内容（用于确认页面展示）。

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "confirmation_status": "pending",
    "confirmations": {
      "canvas": {
        "value": "ppt169",
        "label": "画布格式",
        "description": "16:9 宽屏格式 (1280x720)"
      },
      "page_count": {
        "value": 15,
        "label": "建议页数",
        "description": "包含封面、目录、内容页和总结页"
      },
      "audience": {
        "value": "高管团队",
        "label": "目标受众",
        "description": "C-level管理层，关注核心指标和战略方向"
      },
      "style_mode": {
        "value": "A",
        "label": "风格模式",
        "options": {
          "A": "简洁专业 - 清晰的数据呈现，最小化装饰",
          "B": "视觉冲击力 - 大图、渐变、强烈视觉元素",
          "C": "数据驱动 - 图表为主，仪表板式布局"
        }
      },
      "color_scheme": {
        "value": {
          "primary": "#1a1a2e",
          "secondary": "#16213e",
          "accent": "#e94560",
          "background": "#ffffff",
          "text": "#333333"
        },
        "label": "配色方案",
        "preview": true
      },
      "icon_approach": {
        "value": "B",
        "label": "图标策略",
        "options": {
          "A": "线性图标 (Feather)",
          "B": "填充图标 (Phosphor)",
          "C": "双色图标",
          "D": "不使用图标"
        }
      },
      "typography": {
        "value": {
          "title_font": "Noto Sans SC",
          "body_font": "Noto Sans SC",
          "title_size": "32px",
          "body_size": "16px",
          "title_weight": "700",
          "body_weight": "400"
        },
        "label": "字体方案"
      },
      "image_approach": {
        "value": "C",
        "label": "图片策略",
        "options": {
          "A": "AI生成 - 使用AI为每页生成配图",
          "B": "Web搜索 - 从互联网搜索免版权图片",
          "C": "用户上传 - 使用用户提供的图片",
          "D": "混合模式 - 结合AI生成和搜索",
          "E": "无图片 - 纯文字和图表排版"
        }
      }
    }
  }
}
```

### 3. 确认Eight Confirmations

**POST** `/api/projects/{project_id}/design-spec/confirm`

提交用户对Eight Confirmations的确认。用户可以在确认时修改任何选项。

#### 请求参数

```json
{
  "confirmation_canvas": "ppt169",
  "confirmation_page_count": 18,
  "confirmation_audience": "高管团队",
  "confirmation_style_mode": "A",
  "confirmation_color_scheme": {
    "primary": "#1a1a2e",
    "secondary": "#16213e",
    "accent": "#e94560",
    "background": "#ffffff",
    "text": "#333333"
  },
  "confirmation_icon_approach": "B",
  "confirmation_typography": {
    "title_font": "Noto Sans SC",
    "body_font": "Noto Sans SC",
    "title_size": "32px",
    "body_size": "16px"
  },
  "confirmation_image_approach": "D"
}
```

> **注意**: 所有8个confirmation字段都是可选的。如果不提供某个字段，将使用AI生成的默认值。

#### 响应示例

```json
{
  "code": 200,
  "message": "Eight Confirmations confirmed successfully",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "confirmation_status": "confirmed",
    "confirmed_at": "2024-01-15T10:45:00Z",
    "next_step": "image_acquisition",
    "pipeline_status": "processing"
  }
}
```

### 4. 更新Design Spec（高级）

**PUT** `/api/projects/{project_id}/design-spec`

直接更新Design Spec内容（仅供高级用户，需要了解spec格式）。

#### 请求参数

```json
{
  "spec_content": "# Design Spec\n\n## 自定义内容...",
  "confirmation_color_scheme": {
    "primary": "#ff0000",
    "accent": "#00ff00"
  }
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "Design Spec updated",
  "data": {
    "id": "770e8400-e29b-41d4-a716-446655440001",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

---

## Pipeline API

基础路径: `/api/projects/{project_id}/pipeline`

### 1. Pipeline状态

**GET** `/api/projects/{project_id}/pipeline/status`

获取Pipeline的当前状态。

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "executor",
    "step_status": "running",
    "project_status": "processing",
    "progress": {
      "current_step_index": 5,
      "total_steps": 7,
      "percentage": 71,
      "current_step_label": "页面执行"
    },
    "current_job": {
      "id": "880e8400-e29b-41d4-a716-446655440001",
      "step": "executor",
      "status": "running",
      "started_at": "2024-01-15T10:50:00Z",
      "input_data": {
        "page_count": 18,
        "current_page": 7
      }
    }
  }
}
```

### 2. Job历史

**GET** `/api/projects/{project_id}/pipeline/jobs`

获取Pipeline的Job执行历史。

#### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 20 | 每页数量 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "880e8400-e29b-41d4-a716-446655440001",
        "step": "executor",
        "status": "running",
        "celery_task_id": "task-abc-123",
        "input_data": {"page_count": 18},
        "output_data": null,
        "error_message": null,
        "error_traceback": null,
        "started_at": "2024-01-15T10:50:00Z",
        "completed_at": null,
        "created_at": "2024-01-15T10:50:00Z"
      },
      {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "step": "image_acquisition",
        "status": "completed",
        "celery_task_id": "task-xyz-789",
        "input_data": {"image_count": 5},
        "output_data": {"generated": 3, "sourced": 2},
        "error_message": null,
        "error_traceback": null,
        "started_at": "2024-01-15T10:46:00Z",
        "completed_at": "2024-01-15T10:49:00Z",
        "created_at": "2024-01-15T10:46:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

### 3. 恢复Pipeline

**POST** `/api/projects/{project_id}/pipeline/resume`

从当前步骤恢复执行Pipeline（用于失败后重试或确认后继续）。

#### 响应示例

```json
{
  "code": 200,
  "message": "Pipeline resumed",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "executor",
    "step_status": "running",
    "celery_task_id": "task-resume-456"
  }
}
```

---

## SVG页面API

基础路径: `/api/projects/{project_id}/pages`

### 1. SVG页面列表

**GET** `/api/projects/{project_id}/pages`

获取项目的所有SVG页面。

#### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `quality_status` | string | - | 按质量检查状态筛选 |
| `sort` | string | `page_number` | 排序方式 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440001",
      "page_number": 1,
      "page_name": "cover",
      "filename": "01_cover.svg",
      "svg_storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/svg_output/01_cover.svg",
      "page_rhythm": "anchor",
      "page_layout": "01_cover",
      "page_chart": null,
      "quality_check_status": "passed",
      "quality_check_errors": [],
      "quality_check_warnings": [],
      "speaker_note": {
        "id": "aa0e8400-e29b-41d4-a716-446655440001",
        "note_content": "大家好，今天我将为大家介绍Q1季度的业务表现..."
      },
      "created_at": "2024-01-15T11:00:00Z",
      "updated_at": "2024-01-15T11:00:00Z"
    },
    {
      "id": "990e8400-e29b-41d4-a716-446655440002",
      "page_number": 2,
      "page_name": "toc",
      "filename": "02_toc.svg",
      "svg_storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/svg_output/02_toc.svg",
      "page_rhythm": "breathing",
      "page_layout": "02_toc",
      "page_chart": null,
      "quality_check_status": "passed",
      "quality_check_errors": [],
      "quality_check_warnings": ["建议增加页码"],
      "speaker_note": {
        "id": "aa0e8400-e29b-41d4-a716-446655440002",
        "note_content": "今天的报告分为四个部分..."
      },
      "created_at": "2024-01-15T11:01:00Z",
      "updated_at": "2024-01-15T11:01:00Z"
    }
  ]
}
```

### 2. 获取SVG内容

**GET** `/api/projects/{project_id}/pages/{page_id}`

获取单个SVG页面的完整信息。

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440001",
    "page_number": 1,
    "page_name": "cover",
    "filename": "01_cover.svg",
    "svg_content": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\">...</svg>",
    "page_rhythm": "anchor",
    "page_layout": "01_cover",
    "page_chart": null,
    "quality_check_status": "passed",
    "quality_check_errors": [],
    "quality_check_warnings": [],
    "speaker_note": {
      "id": "aa0e8400-e29b-41d4-a716-446655440001",
      "note_content": "大家好..."
    },
    "created_at": "2024-01-15T11:00:00Z",
    "updated_at": "2024-01-15T11:00:00Z"
  }
}
```

### 3. 获取SVG原始内容

**GET** `/api/projects/{project_id}/pages/{page_id}/svg`

直接返回SVG的原始XML内容（Content-Type: image/svg+xml），可用于`<img>`标签或内嵌显示。

#### 响应

```
HTTP/1.1 200 OK
Content-Type: image/svg+xml

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <!-- SVG内容 -->
</svg>
```

#### HTML使用示例

```html
<!-- 直接嵌入SVG -->
<img src="/api/projects/{project_id}/pages/{page_id}/svg" alt="PPT Page 1" />

<!-- 或使用object标签 -->
<object data="/api/projects/{project_id}/pages/{page_id}/svg" type="image/svg+xml"></object>
```

### 4. 更新SVG（编辑）

**PUT** `/api/projects/{project_id}/pages/{page_id}`

更新SVG页面内容（高级功能，支持手动编辑SVG）。

#### 请求参数

```json
{
  "svg_content": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 1280 720\">...</svg>"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `svg_content` | string | ✅ | SVG XML内容 |

#### 响应示例

```json
{
  "code": 200,
  "message": "SVG page updated",
  "data": {
    "id": "990e8400-e29b-41d4-a716-446655440001",
    "page_number": 1,
    "quality_check_status": "pending",
    "updated_at": "2024-01-15T12:00:00Z"
  }
}
```

---

## PPT导出API

基础路径: `/api/projects/{project_id}/exports`

### 1. 导出列表

**GET** `/api/projects/{project_id}/exports`

获取项目的PPT导出记录列表。

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "bb0e8400-e29b-41d4-a716-446655440001",
      "export_type": "native",
      "filename": "Q1季度报告_20240115_110000.pptx",
      "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/exports/bb0e8400-e29b-41d4-a716-446655440001/Q1季度报告_20240115_110000.pptx",
      "file_size": 3584000,
      "storage_backend": "minio",
      "transition_effect": "fade",
      "animation_effect": null,
      "download_url": "http://minio:9000/pptmaster/projects/.../Q1季度报告.pptx?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ]
}
```

### 2. 下载PPT

**GET** `/api/projects/{project_id}/exports/{export_id}`

下载PPT文件。返回二进制文件流，可直接触发浏览器下载。

#### 响应

```
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation
Content-Disposition: attachment; filename="Q1季度报告_20240115_110000.pptx"

[二进制文件内容]
```

#### cURL下载示例

```bash
curl -O -J http://localhost/api/projects/{project_id}/exports/{export_id}
```

### 3. 重新导出

**POST** `/api/projects/{project_id}/exports`

重新生成PPT导出文件。

#### 请求参数

```json
{
  "export_type": "native",
  "transition_effect": "fade",
  "animation_effect": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `export_type` | string | ❌ | 导出类型：`native`（原生）/ `svg_preview`，默认`native` |
| `transition_effect` | string | ❌ | 幻灯片过渡效果 |
| `animation_effect` | string | ❌ | 动画效果 |

#### 响应示例

```json
{
  "code": 202,
  "message": "Export task started",
  "data": {
    "export_id": "cc0e8400-e29b-41d4-a716-446655440001",
    "status": "pending",
    "celery_task_id": "task-export-123"
  }
}
```

---

## 图片资源API

基础路径: `/api/projects/{project_id}/images`

### 1. 图片列表

**GET** `/api/projects/{project_id}/images`

获取项目的所有图片资源。

#### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `status` | string | - | 按状态筛选 |
| `acquire_via` | string | - | 按获取方式筛选 |

#### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "dd0e8400-e29b-41d4-a716-446655440001",
      "filename": "cover_bg.png",
      "dimensions": "1280x720",
      "ratio": 1.78,
      "purpose": "封面背景",
      "image_type": "Background",
      "acquire_via": "ai",
      "status": "generated",
      "generation_prompt": "现代科技风格的抽象背景，深蓝色调，带有几何图形元素...",
      "generation_backend": "dall-e-3",
      "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/images/dd0e8400-e29b-41d4-a716-446655440001/cover_bg.png",
      "storage_backend": "minio",
      "created_at": "2024-01-15T10:47:00Z",
      "updated_at": "2024-01-15T10:48:00Z"
    },
    {
      "id": "dd0e8400-e29b-41d4-a716-446655440002",
      "filename": "chart_illustration.jpg",
      "dimensions": "800x600",
      "ratio": 1.33,
      "purpose": "数据图表配图",
      "image_type": "Illustration",
      "acquire_via": "web",
      "status": "sourced",
      "search_query": "business growth chart illustration",
      "source_url": "https://example.com/image.jpg",
      "attribution_text": "Photo by Example",
      "license_tier": "no-attribution",
      "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/images/dd0e8400-e29b-41d4-a716-446655440002/chart_illustration.jpg",
      "created_at": "2024-01-15T10:48:00Z",
      "updated_at": "2024-01-15T10:49:00Z"
    }
  ]
}
```

### 2. 上传图片

**POST** `/api/projects/{project_id}/images/upload`

手动上传图片资源。

#### 请求格式

`Content-Type: multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | 图片文件（PNG/JPG/SVG） |
| `purpose` | string | ❌ | 图片用途说明 |
| `image_type` | string | ❌ | 图片类型：`Background`/`Photography`/`Illustration`/`Diagram`/`Decorative` |

#### cURL示例

```bash
curl -X POST http://localhost/api/projects/{project_id}/images/upload \
  -F "file=@/path/to/image.png" \
  -F "purpose=封面背景" \
  -F "image_type=Background"
```

#### 响应示例

```json
{
  "code": 200,
  "message": "Image uploaded successfully",
  "data": {
    "id": "ee0e8400-e29b-41d4-a716-446655440001",
    "filename": "image.png",
    "dimensions": "1200x800",
    "acquire_via": "user",
    "status": "existing",
    "storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/images/ee0e8400-e29b-41d4-a716-446655440001/image.png",
    "original_storage_key": "projects/550e8400-e29b-41d4-a716-446655440000/images/ee0e8400-e29b-41d4-a716-446655440001/original_image.png",
    "created_at": "2024-01-15T12:30:00Z"
  }
}
```

### 3. 更新图片配置

**PUT** `/api/projects/{project_id}/images/{image_id}`

更新图片资源的配置信息。

#### 请求参数

```json
{
  "purpose": "新的用途说明",
  "image_type": "Photography",
  "generation_prompt": "更新后的AI生成提示词",
  "search_query": "更新后的搜索关键词"
}
```

#### 响应示例

```json
{
  "code": 200,
  "message": "Image updated",
  "data": {
    "id": "dd0e8400-e29b-41d4-a716-446655440001",
    "purpose": "新的用途说明",
    "updated_at": "2024-01-15T12:35:00Z"
  }
}
```

---

## WebSocket使用说明

### 连接URL

```
ws://localhost/ws/projects/{project_id}
```

### 消息格式

所有消息使用JSON格式：

```json
{
  "type": "message_type",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": { ... }
}
```

### 消息类型

#### 1. 状态更新 (status_update)

Pipeline整体状态更新。

```json
{
  "type": "status_update",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_step": "strategist",
    "step_status": "running",
    "project_status": "processing",
    "message": "正在分析源内容...",
    "progress": 35
  }
}
```

#### 2. Job更新 (job_update)

单个Job的执行状态更新。

```json
{
  "type": "job_update",
  "timestamp": "2024-01-15T10:31:00Z",
  "data": {
    "job_id": "880e8400-e29b-41d4-a716-446655440001",
    "step": "strategist",
    "status": "completed",
    "output_data": {
      "confirmation_count": 8,
      "spec_generated": true
    }
  }
}
```

#### 3. 步骤变更 (step_change)

Pipeline进入新的步骤。

```json
{
  "type": "step_change",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "previous_step": "strategist",
    "current_step": "image_acquisition",
    "step_status": "running",
    "step_label": "图片获取"
  }
}
```

#### 4. 错误通知 (error)

Pipeline执行过程中发生错误。

```json
{
  "type": "error",
  "timestamp": "2024-01-15T10:36:00Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "step": "executor",
    "error_message": "SVG生成失败: LLM API超时",
    "error_traceback": "Traceback (most recent call last):...",
    "is_fatal": false,
    "retryable": true
  }
}
```

#### 5. 确认通知 (confirmation_needed)

Strategist步骤完成，需要用户确认Eight Confirmations。

```json
{
  "type": "confirmation_needed",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "AI已完成设计分析，请确认以下8项设计决策",
    "confirmations": {
      "canvas": {
        "value": "ppt169",
        "label": "画布格式",
        "description": "16:9 宽屏格式 (1280x720)"
      },
      "page_count": {
        "value": 15,
        "label": "建议页数",
        "description": "包含封面、目录、内容页和总结页"
      },
      "...": "..."
    }
  }
}
```

#### 6. 页面进度 (page_progress)

SVG页面生成进度更新。

```json
{
  "type": "page_progress",
  "timestamp": "2024-01-15T11:05:00Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "current_page": 7,
    "total_pages": 18,
    "percentage": 39,
    "page_name": "content_5",
    "page_label": "业务分析 - 第5页"
  }
}
```

### JavaScript客户端示例

```javascript
// WebSocket连接
const projectId = '550e8400-e29b-41d4-a716-446655440000';
const ws = new WebSocket(`ws://localhost/ws/projects/${projectId}`);

// 连接建立
ws.onopen = () => {
  console.log('WebSocket connected');
};

// 接收消息
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'status_update':
      updatePipelineStatus(message.data);
      break;
    case 'step_change':
      showCurrentStep(message.data);
      break;
    case 'confirmation_needed':
      showConfirmationPage(message.data.confirmations);
      break;
    case 'page_progress':
      updatePageProgress(message.data);
      break;
    case 'error':
      showErrorNotification(message.data);
      break;
    default:
      console.log('Unknown message type:', message.type);
  }
};

// 连接关闭
ws.onclose = () => {
  console.log('WebSocket disconnected');
  // 可选：自动重连
  setTimeout(() => reconnectWebSocket(), 5000);
};

// 错误处理
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// 断开连接
function disconnect() {
  ws.close();
}
```

### Vue 3 Composable示例

```typescript
// composables/useWebSocket.ts
import { ref, onMounted, onUnmounted } from 'vue';

export function useProjectWebSocket(projectId: string) {
  const isConnected = ref(false);
  const lastMessage = ref(null);
  const connectionError = ref(null);
  let ws: WebSocket | null = null;
  let reconnectTimer: number | null = null;

  const connect = () => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/projects/${projectId}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isConnected.value = true;
      connectionError.value = null;
    };

    ws.onmessage = (event) => {
      lastMessage.value = JSON.parse(event.data);
    };

    ws.onclose = () => {
      isConnected.value = false;
      // 自动重连
      reconnectTimer = window.setTimeout(connect, 5000);
    };

    ws.onerror = (error) => {
      connectionError.value = error;
    };
  };

  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    ws?.close();
  };

  onMounted(connect);
  onUnmounted(disconnect);

  return {
    isConnected,
    lastMessage,
    connectionError,
    connect,
    disconnect
  };
}
```

---

## 错误码说明

### HTTP状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | 成功 | 请求处理成功 |
| 201 | 已创建 | 资源创建成功 |
| 202 | 已接受 | 异步任务已启动 |
| 400 | 请求参数错误 | 请求参数格式错误或缺少必填字段 |
| 404 | 资源不存在 | 请求的资源ID不存在 |
| 409 | 状态冲突 | 当前状态不允许执行此操作（如Pipeline运行中不能再次启动） |
| 422 | 验证错误 | 数据验证失败（如无效的枚举值） |
| 500 | 服务器内部错误 | 服务器端发生异常 |
| 503 | 服务不可用 | 依赖服务（如LLM API）不可用 |

### 业务错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| `PROJECT_NOT_FOUND` | 项目不存在 | 检查项目ID是否正确 |
| `PROJECT_STATUS_INVALID` | 项目状态无效 | 当前状态不允许此操作 |
| `PIPELINE_ALREADY_RUNNING` | Pipeline已在运行 | 等待当前Pipeline完成或取消后重试 |
| `PIPELINE_STEP_FAILED` | Pipeline步骤失败 | 查看错误详情，修复后重试 |
| `SOURCE_FILE_NOT_FOUND` | 源文件不存在 | 检查源文件ID |
| `SOURCE_CONVERSION_FAILED` | 源文件转换失败 | 检查文件格式是否支持 |
| `DESIGN_SPEC_NOT_FOUND` | Design Spec不存在 | 先执行Strategist步骤 |
| `CONFIRMATION_NOT_PENDING` | 当前无需确认 | 检查项目状态 |
| `SVG_PAGE_NOT_FOUND` | SVG页面不存在 | 页面尚未生成或ID错误 |
| `EXPORT_NOT_FOUND` | 导出文件不存在 | 导出任务尚未完成 |
| `LLM_API_ERROR` | LLM API调用失败 | 检查API Key和LLM服务状态 |
| `STORAGE_ERROR` | 存储操作失败 | 检查MinIO服务状态 |
| `CELERY_TASK_ERROR` | Celery任务执行失败 | 查看Worker日志 |

### 错误响应格式

```json
{
  "code": 400,
  "message": "Validation error",
  "data": {
    "error_code": "VALIDATION_ERROR",
    "error_detail": {
      "name": ["项目名称不能为空"],
      "canvas_format": ["无效的画布格式，可选值为: ppt169, ppt43, xhs, story"]
    },
    "request_id": "req-abc123-def456"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误处理示例

```javascript
// 前端错误处理示例
async function handleApiRequest(apiCall) {
  try {
    const response = await apiCall();
    return response.data;
  } catch (error) {
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        showValidationError(data.data?.error_detail);
        break;
      case 404:
        showNotFoundError(data.message);
        break;
      case 409:
        showConflictError(data.message);
        break;
      case 422:
        showValidationError(data.data?.error_detail);
        break;
      case 500:
        showServerError(data.message);
        break;
      case 503:
        showServiceUnavailableError(data.message);
        break;
      default:
        showGenericError(data.message || '未知错误');
    }
    
    throw error;
  }
}
```

---

*本文档由 PPT Master Web Service 团队维护，API版本: v1*