# PPT Master Web Service - Pipeline使用指南

> 详细描述PPT生成Pipeline的完整工作流程、每个步骤的输入输出、状态转换和故障处理方法。

---

## 目录

- [Pipeline概述](#pipeline概述)
- [步骤详解](#步骤详解)
- [Eight Confirmations说明](#eight-confirmations说明)
- [状态机转换图](#状态机转换图)
- [人工介入点说明](#人工介入点说明)
- [故障排除](#故障排除)

---

## Pipeline概述

### 什么是Pipeline

Pipeline是PPT Master Web Service的核心工作流，它将源内容（PDF、Word、Excel等文件）通过7个自动化步骤转换为最终的PPT文件。整个流程由LangChain StateGraph编排，Celery异步执行。

### Pipeline步骤总览

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Step 1  │──►│  Step 2  │──►│  Step 3  │──►│  Step 4  │──►│  Step 5  │──►│  Step 6  │──►│  Step 7  │
│   源文件  │   │   项目   │   │   模板   │   │   策略   │   │   图片   │   │   页面   │   │   导出   │
│   处理   │   │   初始化  │   │   选项   │   │   制定   │   │   获取   │   │   执行   │   │   处理   │
└──────────┘   └──────────┘   └──────────┘   └────┬─────┘   └──────────┘   └──────────┘   └──────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │  等待用户确认  │
                                              │ Eight Confirm │
                                              │    ations     │
                                              └──────────────┘
```

| 步骤 | 名称 | 类型 | 耗时 | 说明 |
|------|------|------|------|------|
| 1 | Source Content Processing | 自动 | 10-60秒 | 将源文件转换为Markdown |
| 2 | Project Initialization | 自动 | 1-2秒 | 初始化项目配置和目录 |
| 3 | Template Option | 自动 | <1秒 | 确定画布格式和基础参数 |
| 4 | Strategist Phase | 自动+人工 | 30-120秒 | AI分析内容，需用户确认 |
| 5 | Image Acquisition | 自动 | 30-300秒 | 获取图片资源 |
| 6 | Executor Phase | 自动 | 60-600秒 | 逐页生成SVG |
| 7 | Post-processing & Export | 自动 | 30-120秒 | SVG后处理和PPT导出 |

### 总耗时估计

| 阶段 | 最少耗时 | 典型耗时 | 最多耗时 |
|------|----------|----------|----------|
| 不包含图片获取 | 2-3分钟 | 5-8分钟 | 15分钟 |
| 包含AI图片生成 | 5-7分钟 | 10-15分钟 | 30分钟 |
| 包含Web图片搜索 | 3-5分钟 | 8-12分钟 | 20分钟 |

---

## 步骤详解

### Step 1: Source Content Processing（源文件处理）

**步骤标识**: `source_processing`

**职责**: 将用户上传的各种格式文件转换为统一的Markdown文本，供后续AI分析使用。

**输入**:
- 项目ID
- 项目关联的所有source_files记录

**输出**:
- 每个源文件的 `markdown_content` 字段
- 转换后的Markdown文件存储到MinIO

**支持的文件类型转换**:

| 文件类型 | 转换方式 | 依赖工具 |
|----------|----------|----------|
| PDF | 文本提取 | `pdf_to_md.py` (pymupdf/pdfplumber) |
| DOCX | 文档解析 | `docx_to_md.py` (python-docx) |
| XLSX | 表格转换 | `xlsx_to_md.py` (openpyxl) |
| PPTX | 幻灯片提取 | `pptx_to_md.py` (python-pptx) |
| URL | 网页抓取 | requests + BeautifulSoup |
| MD | 直接使用 | 无需转换 |
| TXT | 直接使用 | 编码检测 + UTF-8转换 |
| HTML | HTML解析 | html2text / BeautifulSoup |
| EPUB | 电子书解析 | ebooklib |

**执行流程**:

```
Celery Worker
    │
    ├── 遍历项目的所有source_files
    │
    ├── 对每个文件:
    │       ├── 从MinIO下载文件到临时目录
    │       ├── 根据file_type选择转换器
    │       ├── 执行转换脚本 (subprocess)
    │       ├── 读取转换后的Markdown内容
    │       ├── 保存markdown_content到数据库
    │       ├── 上传converted.md到MinIO
    │       └── 更新conversion_status = "completed"
    │
    ├── 如果转换失败:
    │       └── conversion_status = "failed"
    │       └── conversion_error = 错误信息
    │
    └── WebSocket推送: conversion_complete
```

**状态转换**:
- 成功: `step_status` → `completed`, `current_step` → `project_init`
- 失败: `step_status` → `failed`

**故障处理**:
- 单个文件转换失败不影响其他文件
- 失败文件可在Web界面查看错误信息
- 支持重新上传和重新转换

---

### Step 2: Project Initialization（项目初始化）

**步骤标识**: `project_init`

**职责**: 初始化项目配置参数，创建存储目录结构。

**输入**:
- 项目ID
- 项目配置（canvas_format, llm_provider, llm_model等）

**输出**:
- 初始化后的项目配置
- MinIO中的项目目录结构

**初始化内容**:

```python
async def initialize_project(project_id: str):
    project = await get_project(project_id)
    
    # 1. 验证配置
    assert project.canvas_format in ["ppt169", "ppt43", "xhs", "story"]
    assert project.llm_provider in ["openai", "anthropic"]
    
    # 2. 创建MinIO目录结构
    base_path = f"projects/{project_id}"
    directories = [
        f"{base_path}/sources",
        f"{base_path}/images",
        f"{base_path}/svg_output",
        f"{base_path}/svg_final",
        f"{base_path}/notes",
        f"{base_path}/exports",
        f"{base_path}/templates",
    ]
    for dir_path in directories:
        await storage.put(f"{dir_path}/.gitkeep", "")
    
    # 3. 初始化设计参数
    canvas_config = {
        "ppt169": {"viewBox": "0 0 1280 720", "width": 1280, "height": 720},
        "ppt43": {"viewBox": "0 0 1024 768", "width": 1024, "height": 768},
        "xhs": {"viewBox": "0 0 900 1200", "width": 900, "height": 1200},
        "story": {"viewBox": "0 0 1080 1920", "width": 1080, "height": 1920},
    }
    project.canvas_config = canvas_config[project.canvas_format]
    
    return project
```

**状态转换**:
- 成功: `step_status` → `completed`, `current_step` → `template_option`
- 失败: `step_status` → `failed`（极少发生）

---

### Step 3: Template Option（模板选项）

**步骤标识**: `template_option`

**职责**: 根据项目配置确定模板参数和基础设计选项。

**说明**: 此步骤在Pipeline中是一个轻量级过渡步骤，主要配置在Step 2中已完成。它检查画布格式并加载对应的模板预设。

**画布格式参数**:

| 画布格式 | viewBox | 用途 | 典型场景 |
|----------|---------|------|----------|
| `ppt169` | `0 0 1280 720` | 16:9宽屏 | 标准演示、会议报告 |
| `ppt43` | `0 0 1024 768` | 4:3标准 | 传统投影、教育课件 |
| `xhs` | `0 0 900 1200` | 3:4竖屏 | 小红书、社交媒体 |
| `story` | `0 0 1080 1920` | 9:16竖屏 | 故事板、竖屏展示 |

**状态转换**:
- 成功: `step_status` → `completed`, `current_step` → `strategist`

---

### Step 4: Strategist Phase（策略制定）

**步骤标识**: `strategist`

**类型**: 🔶 **自动 + 人工介入**（关键步骤）

**职责**: AI深度分析源内容，生成Eight Confirmations（8项设计决策建议）和完整的Design Spec文档。

**这是整个Pipeline中最重要的步骤**，决定了最终PPT的设计方向和质量。

**输入**:
- 所有源文件的 `markdown_content`
- 项目配置（画布格式、LLM配置等）
- 原始的strategist.md prompt模板

**输出**:
- **Eight Confirmations** - 8项设计决策建议（存入design_specs表）
- **Design Spec** - 完整的设计规范文档（Markdown格式，存入MinIO）

**执行流程**:

```
Celery Worker (Strategist Task)
    │
    ├── 1. 收集源内容
    │       └── 读取所有source_files的markdown_content
    │           合并为单一的content文本
    │
    ├── 2. 构建Prompt
    │       ├── 加载strategist.md模板
    │       ├── 注入源内容
    │       ├── 注入画布格式信息
    │       └── 构建完整的system + user prompt
    │
    ├── 3. 调用LLM (gpt-4o / claude-3.5-sonnet)
    │       └── 发送prompt，等待响应 (30-120秒)
    │
    ├── 4. 解析LLM输出
    │       ├── 提取Eight Confirmations
    │       │   ├── confirmation_canvas
    │       │   ├── confirmation_page_count
    │       │   ├── confirmation_audience
    │       │   ├── confirmation_style_mode (A/B/C)
    │       │   ├── confirmation_color_scheme (JSON)
    │       │   ├── confirmation_icon_approach (A/B/C/D)
    │       │   ├── confirmation_typography (JSON)
    │       │   └── confirmation_image_approach (A/B/C/D/E)
    │       ├── 提取完整Design Spec文本
    │       └── 验证数据完整性
    │
    ├── 5. 保存到数据库
    │       ├── 创建design_specs记录
    │       ├── 保存Eight Confirmations字段
    │       └── 保存spec_content
    │
    ├── 6. 保存到MinIO
    │       └── 上传design_spec.md
    │
    ├── 7. 更新项目状态
    │       ├── projects.status = "CONFIRMING"
    │       ├── projects.step_status = "WAITING_CONFIRMATION"
    │       └── 创建pipeline_jobs记录
    │
    └── 8. WebSocket通知
            └── 推送 confirmation_needed 消息
                前端自动跳转确认页面
```

**LLM Prompt结构示例**:

```
[System]
你是一位专业的PPT设计策略师。请根据提供的内容，生成一份完整的设计规范。

[Context]
画布格式: 16:9 (1280x720)
源内容字数: 约5000字
源内容摘要: Q1季度业务报告，包含财务数据、市场分析、团队业绩...

[Instructions]
1. 分析内容类型和目标受众
2. 推荐最佳设计风格
3. 制定配色方案
4. 规划页面结构
5. 确定字体和图标策略
6. 规划图片使用策略

[Output Format]
请按以下格式输出：

## Eight Confirmations

### 1. Canvas (画布)
...

### 2. Page Count (页数)
...

### 3. Audience (受众)
...

### 4. Style Mode (风格)
选项: A/B/C
...

### 5. Color Scheme (配色)
...

### 6. Icon Approach (图标)
选项: A/B/C/D
...

### 7. Typography (字体)
...

### 8. Image Approach (图片)
选项: A/B/C/D/E
...

## Design Spec

### Overview
...

### Page Structure
...

### Design Rules
...
```

**状态转换**:
- 成功: `step_status` → `WAITING_CONFIRMATION`, `project.status` → `CONFIRMING`
- 失败: `step_status` → `failed`
- 用户确认后: `step_status` → `completed`, 继续执行image_acquisition

---

### Step 5: Image Acquisition（图片获取）

**步骤标识**: `image_acquisition`

**职责**: 根据用户在Eight Confirmations中选择的图片策略，获取所需的图片资源。

**输入**:
- 确认后的Eight Confirmations
- Design Spec中的图片规划
- Spec Lock中的图片清单

**输出**:
- 所有图片资源的 `image_resources` 记录
- 图片文件存储到MinIO

**图片策略选项**:

| 选项 | 策略 | 说明 | 耗时 |
|------|------|------|------|
| A | AI生成 | 使用DALL-E 3或Midjourney生成配图 | 30-60秒/张 |
| B | Web搜索 | 从Bing/Google搜索免版权图片 | 5-10秒/张 |
| C | 用户上传 | 使用用户预先上传的图片 | 即时 |
| D | 混合模式 | AI生成 + Web搜索结合 | 视组合而定 |
| E | 无图片 | 纯文字和图表排版，跳过此步骤 | 0秒 |

**执行流程**:

```
Celery Worker (Image Task)
    │
    ├── 如果image_approach == "E" (无图片):
    │       └── 跳过此步骤
    │
    ├── 1. 从Spec Lock读取图片清单
    │       └── images数组: [{name, path, no_crop}, ...]
    │
    ├── 2. 为每个图片创建image_resources记录
    │       └── status = "pending"
    │
    ├── 3. 根据策略获取图片:
    │       │
    │       ├── AI生成 (策略A或D中的AI部分):
    │       │       ├── 构建图片生成prompt
    │       │       ├── 调用DALL-E 3 API
    │       │       ├── 下载生成的图片
    │       │       ├── 上传到MinIO
    │       │       └── 更新status = "generated"
    │       │
    │       ├── Web搜索 (策略B或D中的搜索部分):
    │       │       ├── 构建搜索关键词
    │       │       ├── 调用图片搜索API
    │       │       ├── 下载图片
    │       │       ├── 验证图片质量
    │       │       ├── 上传到MinIO
    │       │       └── 更新status = "sourced"
    │       │
    │       └── 用户上传 (策略C):
    │               ├── 检查用户上传的图片
    │               ├── 复制到项目目录
    │               └── 更新status = "existing"
    │
    ├── 4. 质量检查
    │       ├── 检查图片尺寸是否满足画布要求
    │       ├── 检查图片格式 (PNG/JPG/SVG)
    │       └── 标记不合格的图片为 "needs_manual"
    │
    └── 5. 汇总结果
            └── 更新pipeline_jobs.output_data
                {
                    "total_images": 10,
                    "generated": 4,
                    "sourced": 3,
                    "existing": 2,
                    "placeholder": 1
                }
```

**状态转换**:
- 成功: `step_status` → `completed`, `current_step` → `executor`
- 失败（部分图片）: 继续执行，标记失败的图片
- 全部失败: `step_status` → `failed`

---

### Step 6: Executor Phase（页面执行）

**步骤标识**: `executor`

**职责**: 根据Spec Lock中定义的设计规范，逐页生成SVG页面。

**输入**:
- Spec Lock（机器可读的设计规范）
- Design Spec（完整的设计规范文档）
- 图片资源（来自image_acquisition步骤）
- 源内容Markdown

**输出**:
- SVG页面（存入svg_pages表和MinIO）
- Speaker Notes（演讲备注）

**特点**:
- **逐页顺序生成**（sequential, one at a time）
- 每页独立调用LLM
- 实时WebSocket进度推送
- 每页生成后进行质量检查

**执行流程**:

```
Celery Worker (Executor Task)
    │
    ├── 1. 加载设计规范
    │       ├── Spec Lock (colors, typography, icons, layouts, rhythm)
    │       ├── Design Spec (完整的Markdown文档)
    │       └── 合并的源内容
    │
    ├── 2. 获取页面规划
    │       ├── page_rhythm: {"P01": "anchor", "P02": "dense", ...}
    │       ├── page_layouts: {"P01": "01_cover", "P02": "02_toc", ...}
    │       └── page_charts: {"P05": "bar_chart", ...}
    │
    ├── 3. 逐页生成SVG:
    │       │
    │       FOR page_key, page_rhythm IN page_rhythm.items():
    │       │
    │       ├── 3.1 确定页面参数
    │       │       ├── page_number = int(page_key.replace("P", ""))
    │       │       ├── page_layout = page_layouts.get(page_key)
    │       │       ├── page_chart = page_charts.get(page_key)
    │       │       └── page_name = derive_page_name(page_layout)
    │       │
    │       ├── 3.2 构建页面Prompt
    │       │       ├── 页面类型和布局模板
    │       │       ├── 设计规范 (colors, fonts, icons)
    │       │       ├── 页面内容 (从源内容提取)
    │       │       ├── 图片引用 (如果需要)
    │       │       └── SVG技术规范 (viewBox, namespace等)
    │       │
    │       ├── 3.3 调用LLM生成SVG
    │       │       └── 发送prompt → 接收SVG XML
    │       │
    │       ├── 3.4 解析和验证SVG
    │       │       ├── 提取SVG XML内容
    │       │       ├── 验证SVG语法
    │       │       └── 检查viewBox和尺寸
    │       │
    │       ├── 3.5 SVG质量检查
    │       │       ├── 检查必填元素
    │       │       ├── 检查颜色使用
    │       │       ├── 检查字体引用
    │       │       └── 记录errors和warnings
    │       │
    │       ├── 3.6 生成Speaker Note
    │       │       ├── 基于SVG内容构建note prompt
    │       │       ├── 调用LLM生成演讲备注
    │       │       └── 保存到speaker_notes表
    │       │
    │       ├── 3.7 保存结果
    │       │       ├── 保存svg_content到svg_pages表
    │       │       ├── 上传SVG文件到MinIO (svg_output/)
    │       │       └── 保存speaker_note
    │       │
    │       └── 3.8 WebSocket推送
    │               └── page_progress消息
    │                   {current_page, total_pages, page_name, percentage}
    │
    ├── 4. 汇总结果
    │       └── 统计生成的页面数量和质量检查结果
    │
    └── 5. 保存所有Speaker Notes到MinIO
            └── 上传 notes/total.md
```

**页面节奏类型 (Page Rhythm)**:

| 类型 | 说明 | 适用页面 |
|------|------|----------|
| `anchor` | 视觉焦点页，大图或重要内容 | 封面、章节页 |
| `dense` | 信息密集型，数据丰富 | 内容页、数据页 |
| `breathing` | 留白较多，视觉休息 | 目录、过渡页 |

**页面布局类型 (Page Layout)**:

| 布局 | 说明 |
|------|------|
| `01_cover` | 封面页 |
| `02_toc` | 目录页 |
| `03_chapter` | 章节分隔页 |
| `04_title_content` | 标题+内容页 |
| `05_two_column` | 双栏布局 |
| `06_image_text` | 图文混排 |
| `07_data_chart` | 数据图表页 |
| `08_quote` | 引用页 |
| `09_summary` | 总结页 |
| `10_end` | 结尾页 |

**状态转换**:
- 成功（全部页面）: `step_status` → `completed`, `current_step` → `post_processing`
- 成功（部分页面有警告）: `step_status` → `completed`, 记录warnings
- 失败（关键页面）: `step_status` → `failed`

---

### Step 7: Post-processing & Export（后处理导出）

**步骤标识**: `post_processing`

**职责**: SVG后处理优化、最终质量检查和PPTX导出。

**子步骤**:

#### 7.1 SVG后处理 (finalize_svg)

```
SVG后处理流程:
    │
    ├── 1. 遍历所有SVG页面 (svg_output/)
    │
    ├── 2. 对每个SVG文件:
    │       ├── 字体嵌入处理
    │       │       └── 将引用的外部字体转为内联或路径
    │       ├── SVG路径优化
    │       │       └── 清理不必要的path、合并重复元素
    │       ├── 尺寸标准化
    │       │       └── 确保所有SVG使用相同的viewBox
    │       └── 保存到 svg_final/
    │
    └── 3. 汇总后处理结果
```

#### 7.2 PPT导出 (svg_to_pptx)

```
PPT导出流程:
    │
    ├── 1. 读取所有后处理后的SVG文件 (svg_final/)
    │
    ├── 2. 创建PPTX文件
    │       ├── 初始化Presentation对象
    │       ├── 设置幻灯片尺寸 (匹配画布格式)
    │       └── 设置默认字体
    │
    ├── 3. 逐页转换:
    │       FOR each SVG:
    │           ├── 创建新幻灯片
    │           ├── 将SVG转换为PPT形状
    │           ├── 应用过渡效果 (如配置)
    │           ├── 应用动画效果 (如配置)
    │           └── 添加演讲者备注
    │
    ├── 4. 保存PPT文件
    │       ├── 生成文件名: {project_name}_{timestamp}.pptx
    │       ├── 上传到MinIO (exports/)
    │       └── 创建pptx_exports记录
    │
    └── 5. 完成处理
            ├── 更新projects.status = "COMPLETED"
            ├── 更新projects.completed_at
            └── WebSocket推送: pipeline_completed
```

**状态转换**:
- 成功: `step_status` → `completed`, `project.status` → `COMPLETED`
- 失败: `step_status` → `failed`, `project.status` → `FAILED`

---

## Eight Confirmations说明

### 什么是Eight Confirmations

Eight Confirmations是PPT Master的**核心交互机制**，在Pipeline的Strategist步骤后，AI会生成8项关键设计决策建议，用户需要逐项确认或修改。这确保了最终PPT的设计方向符合用户期望。

### 为什么需要Eight Confirmations

1. **设计方向确认** - 在大量页面生成前确认整体风格
2. **减少返工** - 避免生成后大幅修改
3. **用户参与感** - 让用户参与关键设计决策
4. **质量保证** - AI建议 + 人工判断 = 更好结果

### 逐项说明

#### 1. Canvas（画布格式）

确认PPT的画布尺寸和比例。

| 选项 | 尺寸 | viewBox | 适用场景 |
|------|------|---------|----------|
| `ppt169` | 1280x720 | `0 0 1280 720` | 标准宽屏演示 |
| `ppt43` | 1024x768 | `0 0 1024 768` | 传统投影设备 |
| `xhs` | 900x1200 | `0 0 900 1200` | 小红书/社交媒体 |
| `story` | 1080x1920 | `0 0 1080 1920` | 故事板/竖屏展示 |

#### 2. Page Count（页数）

AI根据内容复杂度建议的PPT总页数。

- 用户可以增加或减少页数
- 建议范围：5-50页
- 典型范围：10-25页

#### 3. Audience（目标受众）

AI分析内容后推断的目标受众。

常见受众类型：
- **高管团队** - 关注结论和战略方向
- **技术团队** - 关注实现细节和技术方案
- **客户/合作伙伴** - 关注价值和合作模式
- **投资者** - 关注财务数据和增长潜力
- **内部团队** - 关注执行计划和协作方式

#### 4. Style Mode（风格模式）

| 选项 | 风格 | 特点 | 适用场景 |
|------|------|------|----------|
| **A** | 简洁专业 | 清晰的数据呈现，最小化装饰，留白适中 | 商务报告、数据分析 |
| **B** | 视觉冲击力 | 大图、渐变、强烈视觉元素，色彩鲜明 | 品牌展示、创意提案 |
| **C** | 数据驱动 | 图表为主，仪表板式布局，信息密度高 | 数据分析、技术报告 |

#### 5. Color Scheme（配色方案）

AI生成的配色方案，包含以下颜色：

```json
{
  "primary": "#1a1a2e",        // 主色 - 用于标题和重点
  "secondary": "#16213e",      // 辅色 - 用于副标题
  "accent": "#e94560",         // 强调色 - 用于CTA和重点标注
  "background": "#ffffff",     // 背景色
  "text": "#333333",           // 正文色
  "text_secondary": "#666666", // 次要文字色
  "border": "#e0e0e0"          // 边框色
}
```

用户可以：
- 接受AI建议的配色
- 修改单个颜色值
- 选择预设的配色方案

#### 6. Icon Approach（图标策略）

| 选项 | 策略 | 说明 |
|------|------|------|
| **A** | 线性图标 (Feather) | 简洁的线条图标，适合专业风格 |
| **B** | 填充图标 (Phosphor) | 实心填充图标，视觉权重较高 |
| **C** | 双色图标 | 两种颜色组合，层次分明 |
| **D** | 不使用图标 | 纯文字排版 |

#### 7. Typography（字体方案）

```json
{
  "title_font": "Noto Sans SC",     // 标题字体
  "body_font": "Noto Sans SC",      // 正文字体
  "title_size": "32px",             // 标题字号
  "body_size": "16px",              // 正文字号
  "title_weight": "700",            // 标题字重
  "body_weight": "400"              // 正文字重
}
```

#### 8. Image Approach（图片策略）

| 选项 | 策略 | 说明 | 耗时 |
|------|------|------|------|
| **A** | AI生成 | 使用DALL-E 3为每页生成配图 | 较长 |
| **B** | Web搜索 | 从互联网搜索免版权图片 | 中等 |
| **C** | 用户上传 | 使用用户预先上传的图片 | 即时 |
| **D** | 混合模式 | AI生成 + Web搜索结合 | 较长 |
| **E** | 无图片 | 纯文字和图表排版 | 即时 |

### 确认界面操作流程

```
用户收到confirmation_needed通知
    │
    ├── 1. 查看AI生成的8项建议
    │       ├── 每项显示AI建议值和说明
    │       └── 提供修改选项
    │
    ├── 2. 逐项审阅（可选修改）
    │       ├── 画布: 确认/切换
    │       ├── 页数: 确认/调整数字
    │       ├── 受众: 确认/编辑文本
    │       ├── 风格: 确认/切换A/B/C
    │       ├── 配色: 确认/调色板选择
    │       ├── 图标: 确认/切换A/B/C/D
    │       ├── 字体: 确认/字体选择
    │       └── 图片: 确认/切换A/B/C/D/E
    │
    ├── 3. 预览效果（如果可用）
    │       └── 基于确认的选项生成预览
    │
    └── 4. 点击「确认」提交
            └── API: POST /api/projects/{id}/design-spec/confirm
                └── Pipeline继续执行
```

---

## 状态机转换图

### 项目状态机

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                                                         │
                    ▼                                                         │
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  draft  │───►│confirming│───►│processing│───►│completed │    │  failed  │◄┘
│ (草稿)  │    │(等待确认) │    │ (执行中)  │    │ (已完成)  │    │ (失败)   │
└────┬────┘    └──────────┘    └─────┬────┘    └──────────┘    └────┬─────┘
     │                                │                              │
     │ 创建项目                        │ Pipeline启动                  │
     │                                │                               │
     │         用户确认Confirmations   │ Pipeline完成                  │ Pipeline失败
     │         或取消                  │ 或取消                        │ 或手动重置
     │                                │                               │
     │◄───────────────────────────────┘                               │
     │◄───────────────────────────────────────────────────────────────┘
```

**状态转换规则**:

| 当前状态 | 允许的操作 | 下一状态 |
|----------|------------|----------|
| `DRAFT` | 启动Pipeline | `PROCESSING` (直接到source_processing) |
| `CONFIRMING` | 确认Eight Confirmations | `PROCESSING` |
| `CONFIRMING` | 取消 | `DRAFT` |
| `PROCESSING` | Pipeline完成 | `COMPLETED` |
| `PROCESSING` | Pipeline失败 | `FAILED` |
| `PROCESSING` | 取消Pipeline | `DRAFT` |
| `COMPLETED` | 重新启动 | `PROCESSING` |
| `FAILED` | 恢复/重试 | `PROCESSING` |
| `FAILED` | 重置 | `DRAFT` |

### Pipeline步骤状态机

```
                         ┌──────────┐
    ┌───────────────────►│  pending │◄──────────────────────────┐
    │                    │ (待执行)  │                           │
    │                    └────┬─────┘                           │
    │                         │ 启动                             │
    │                         ▼                                  │
    │                    ┌──────────┐     失败且可重试           │
    │              ┌────►│ running  │─────────────────────┐     │
    │              │     │ (执行中)  │                     │     │
    │              │     └────┬─────┘                     │     │
    │              │          │                           │     │
    │              │          ▼                           │     │
    │         用户确认 ┌──────────────────┐                │     │
    │              │   │WAITING_CONFIRMATION│              │     │
    │              │   │  (等待用户确认)    │              │     │
    │              │   └────────┬─────────┘              │     │
    │              │            │ 用户确认                 │     │
    │              │            ▼                          │     │
    │              │     ┌──────────┐◄────────────────────┘     │
    │              └─────┤completed │                            │
    │                    │ (已完成)  │────────────────────────────┘
    │                    └──────────┘     取消后重新启动
    │
    │                    ┌──────────┐
    └───────────────────►│  failed  │◄──────────────────────────┐
                         │ (失败)   │                           │
                         └──────────┘                           │
                                                                │
                                                                │
                    用户取消 ←────────────────────────────────────┘
```

### 完整的Pipeline状态转换序列

**成功场景**:

```
[init] 
  │ 启动Pipeline
  ▼
[source_processing] ──► PENDING → RUNNING → COMPLETED
  │
  ▼
[project_init] ──► PENDING → RUNNING → COMPLETED
  │
  ▼
[template_option] ──► PENDING → RUNNING → COMPLETED
  │
  ▼
[strategist] ──► PENDING → RUNNING → WAITING_CONFIRMATION
  │               ▲
  │               │ 用户确认
  ▼               │
[image_acquisition] ──► PENDING → RUNNING → COMPLETED
  │
  ▼
[executor] ──► PENDING → RUNNING → COMPLETED (逐页进度推送)
  │
  ▼
[post_processing] ──► PENDING → RUNNING → COMPLETED
  │
  ▼
[COMPLETED] ──► 项目完成，可下载PPT
```

**失败重试场景**:

```
[executor] ──► RUNNING → FAILED (第7页SVG生成超时)
  │
  │ 用户点击「重试」
  ▼
[executor] ──► PENDING → RUNNING → COMPLETED (从第7页继续)
  │
  ▼
[post_processing] ──► ... → COMPLETED
```

---

## 人工介入点说明

### Pipeline中的人工介入点

| 介入点 | 步骤 | 说明 | 必需/可选 |
|--------|------|------|-----------|
| **Eight Confirmations** | Strategist后 | 确认8项设计决策 | **必需** |
| **图片上传** | Image Acquisition中 | 如果选择策略C，需要上传图片 | 条件必需 |
| **SVG编辑** | Executor后 | 手动编辑不满意的SVG页面 | 可选 |
| **质量检查** | Post-processing前 | 审查并修复有问题的页面 | 可选 |

### 介入点详细说明

#### 介入点1: Eight Confirmations（必需）

- **触发时机**: Strategist步骤完成后
- **停留时间**: 无限期（直到用户确认或取消）
- **操作**: 确认或修改8项设计决策
- **影响**: 决定后续所有页面的设计方向

#### 介入点2: 图片上传（条件必需）

- **触发时机**: Image Acquisition步骤中，当图片策略为C（用户上传）时
- **停留时间**: 无限期
- **操作**: 上传所需的图片文件
- **影响**: 影响包含图片的页面的视觉效果

#### 介入点3: SVG编辑（可选）

- **触发时机**: Executor步骤完成后（Pipeline状态为COMPLETED或FAILED）
- **操作**: 通过 `PUT /api/projects/{id}/pages/{page_id}` 修改SVG内容
- **影响**: 修改后的SVG会在下次导出时生效

#### 介入点4: 质量检查（可选）

- **触发时机**: Post-processing步骤前
- **操作**: 查看quality_check报告，修复有问题的页面
- **影响**: 确保导出PPT的质量

---

## 故障排除

### 常见问题与解决方案

#### 问题1: Pipeline卡在Source Processing

**现象**: 源文件转换长时间没有进展

**排查步骤**:

```bash
# 1. 检查Celery Worker是否运行
docker-compose ps celery_worker

# 2. 查看Worker日志
docker-compose logs -f celery_worker | grep source_processing

# 3. 检查源文件状态
curl http://localhost/api/projects/{project_id}/sources
# 查看conversion_status字段

# 4. 检查文件是否损坏
docker-compose exec backend python -c "
import asyncio
from app.services.storage_service import StorageManager
async def check():
    storage = StorageManager.get_backend()
    data = await storage.get('projects/{project_id}/sources/{source_id}/{filename}')
    print(f'File size: {len(data)} bytes')
asyncio.run(check())
"
```

**解决方案**:
- 如果文件过大（>50MB），尝试拆分PDF后重新上传
- 如果是加密PDF，先解密再上传
- 如果转换器报错，尝试其他格式（如PDF转Word后再上传）

#### 问题2: Strategist步骤LLM调用超时

**现象**: Strategist步骤运行很长时间后失败

**排查步骤**:

```bash
# 1. 检查LLM API连通性
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"

# 2. 查看后端日志
docker-compose logs backend | grep strategist

# 3. 检查源内容大小
curl http://localhost/api/projects/{project_id}/sources | jq '.data[].markdown_content | length'
# 如果内容超过10000字，可能需要精简
```

**解决方案**:
- 检查API Key是否有效
- 如果源内容过长，删除不必要的源文件
- 切换LLM提供商（OpenAI ↔ Anthropic）
- 检查网络连接，确保能访问LLM API

#### 问题3: 用户确认后Pipeline没有继续

**现象**: 确认Eight Confirmations后，Pipeline状态没有变化

**排查步骤**:

```bash
# 1. 检查确认是否成功
curl http://localhost/api/projects/{project_id}/design-spec
# 查看confirmation_status应为"confirmed"

# 2. 检查Celery任务队列
docker-compose exec redis redis-cli -n 0 LLEN celery

# 3. 检查Worker状态
docker-compose logs -f celery_worker | grep image_acquisition

# 4. 手动恢复
curl -X POST http://localhost/api/projects/{project_id}/pipeline/resume
```

**解决方案**:
- 等待Celery Worker处理（队列可能有延迟）
- 手动调用resume API恢复Pipeline
- 如果Worker未运行，重启Worker: `docker-compose restart celery_worker`

#### 问题4: Executor步骤页面生成失败

**现象**: 部分SVG页面生成失败，quality_check_status为failed

**排查步骤**:

```bash
# 1. 查看失败的页面
curl "http://localhost/api/projects/{project_id}/pages?quality_status=failed"

# 2. 查看具体的错误信息
curl http://localhost/api/projects/{project_id}/pages/{page_id} | jq '.data.quality_check_errors'

# 3. 查看pipeline_jobs错误日志
curl http://localhost/api/projects/{project_id}/pipeline/jobs | jq '.data.items[].error_message'
```

**解决方案**:
- 如果少量页面失败，可以手动编辑修复后重新导出
- 如果大量页面失败，可能是Spec Lock有问题，建议重新启动Pipeline
- 检查LLM API是否稳定

#### 问题5: PPT导出失败

**现象**: Post-processing步骤失败，无法下载PPT

**排查步骤**:

```bash
# 1. 检查svg_final目录是否存在
docker-compose exec minio mc ls local/pptmaster/projects/{project_id}/svg_final/

# 2. 检查导出日志
docker-compose logs celery_worker | grep svg_to_pptx

# 3. 检查磁盘空间
df -h
```

**解决方案**:
- 确保所有SVG页面都存在且有效
- 检查MinIO存储空间是否充足
- 手动重新导出: `POST /api/projects/{project_id}/exports`

### 强制重置Pipeline

如果Pipeline完全卡死，可以强制重置：

```bash
# 1. 取消Pipeline
curl -X POST http://localhost/api/projects/{project_id}/cancel

# 2. 重置项目状态
curl -X PUT http://localhost/api/projects/{project_id} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "draft",
    "current_step": "init",
    "step_status": "pending"
  }'

# 3. 重新启动Pipeline
curl -X POST http://localhost/api/projects/{project_id}/start
```

### 日志查看指南

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志（实时）
docker-compose logs -f backend
docker-compose logs -f celery_worker
docker-compose logs -f frontend
docker-compose logs -f db
docker-compose logs -f redis

# 查看最近100行日志
docker-compose logs --tail=100 backend

# 查看特定时间段的日志
docker-compose logs --since="2024-01-15T10:00:00" backend

# 搜索特定关键词
docker-compose logs celery_worker | grep "ERROR"
docker-compose logs backend | grep "strategist"
```

---

*本文档由 PPT Master Web Service 团队维护，如有疑问请联系开发团队。*