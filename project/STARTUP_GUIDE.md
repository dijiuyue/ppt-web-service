# PPT Master Web Service — 启动运行指南

> **目标：按照本指南操作，可在 10 分钟内启动完整服务。**

---

## 一、环境要求

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| Python | >= 3.10 | 后端运行时 |
| Node.js | >= 18 | 前端构建 |
| pip | >= 23 | Python包管理 |
| npm | >= 9 | Node包管理 |
| (可选) Docker | >= 24 | 容器化部署 |
| (可选) Docker Compose | >= 2 | 编排部署 |

---

## 二、项目结构

```
/mnt/agents/output/ppt-web-service/project/
├── backend/              # FastAPI 后端
│   ├── app/              # 应用代码 (44个模块)
│   ├── tests/            # 测试套件 (304个用例)
│   ├── alembic/          # 数据库迁移
│   ├── requirements.txt  # Python依赖
│   └── Dockerfile        # 后端镜像
├── frontend/             # Vue3 前端
│   ├── src/              # 源代码
│   ├── package.json      # Node依赖
│   └── Dockerfile        # 前端镜像
├── docker/               # Docker配置
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── nginx.conf
│   └── entrypoint.sh
└── ppt-report/           # 架构汇报PPT
    └── ppt-master-report.pptd
```

---

## 三、方式一：本地手动启动（推荐开发环境）

### 步骤 1：安装后端依赖

```bash
cd /mnt/agents/output/ppt-web-service/project/backend

# 使用阿里云镜像加速（国内环境推荐）
pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

> **验证安装**：运行 `python3 -c "import app.main; print('OK')"` 应输出 `OK`

### 步骤 2：配置环境变量

```bash
# 创建 .env 文件
cat > .env << 'EOF'
# === 数据库 ===
DATABASE_URL=sqlite+aiosqlite:///./pptmaster.db

# === Redis (如未安装Redis，可使用内存模式) ===
REDIS_URL=redis://localhost:6379/0

# === MinIO (开发环境使用本地文件系统替代) ===
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=./storage

# === LLM API Key (必须配置) ===
OPENAI_API_KEY=sk-your-openai-key-here

# === 安全 ===
SECRET_KEY=your-secret-key-here-change-in-production

# === PPT Master Skill 路径 ===
PPT_MASTER_SKILL_DIR=/path/to/ppt-master/skills/ppt-master
EOF
```

> **重点配置**：
> - `OPENAI_API_KEY`：**必须替换**为你的真实 OpenAI API Key
> - `DATABASE_URL`：默认使用 SQLite（零配置），生产环境替换为 PostgreSQL
> - `STORAGE_BACKEND`：开发用 `local`，生产用 `minio`
> - `PPT_MASTER_SKILL_DIR`：指向原 ppt-master skill 的目录

### 步骤 3：启动后端服务

```bash
cd /mnt/agents/output/ppt-web-service/project/backend

# 方式A：开发模式（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式B：生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

> **验证启动**：访问 http://localhost:8000/docs 应看到 API 文档

### 步骤 4：安装并启动前端

```bash
cd /mnt/agents/output/ppt-web-service/project/frontend

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

> **访问地址**：http://localhost:5173

### 步骤 5：验证完整服务

```bash
# 健康检查
curl http://localhost:8000/health

# 创建测试项目
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Test project","canvas_format":"ppt169"}'

# 查看API文档（浏览器打开）
open http://localhost:8000/docs
```

---

## 四、方式二：Docker Compose 启动（推荐生产环境）

### 步骤 1：配置环境变量

```bash
cd /mnt/agents/output/ppt-web-service/project
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 步骤 2：一键启动

```bash
cd /mnt/agents/output/ppt-web-service/project/docker
docker-compose -f docker-compose.dev.yml up --build
```

> **包含服务**：PostgreSQL + Redis + MinIO + Backend + Frontend

### 步骤 3：访问服务

| 服务 | 地址 |
|------|------|
| Web 界面 | http://localhost |
| API 文档 | http://localhost/api/docs |
| MinIO 控制台 | http://localhost:9001 |

---

## 五、验证清单

启动后逐项确认：

- [ ] `curl http://localhost:8000/health` 返回 `{"status":"ok"}`
- [ ] 浏览器打开 `/docs` 可见 35 个 API 端点
- [ ] `python3 -m pytest tests/ -q` 显示 304 passed
- [ ] 前端页面正常加载（无白屏/404）
- [ ] 可成功创建项目并查看详情

---

## 六、关键环境变量参考

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_API_KEY` | **是** | - | OpenAI API Key |
| `ANTHROPIC_API_KEY` | 否 | - | Anthropic API Key（可选） |
| `DATABASE_URL` | 否 | SQLite | 数据库连接字符串 |
| `REDIS_URL` | 否 | localhost | Redis 连接地址 |
| `STORAGE_BACKEND` | 否 | local | `local` 或 `minio` |
| `SECRET_KEY` | 否 | auto | JWT 签名密钥 |
| `PPT_MASTER_SKILL_DIR` | 否 | - | 原 Skill 路径 |

---

## 七、测试

```bash
cd /mnt/agents/output/ppt-web-service/project/backend

# 运行全部测试
python3 -m pytest tests/ -v

# 预期结果：304 passed, 0 failed
```

---

## 八、常见问题

### Q1: pip install 超时
```bash
# 使用阿里云镜像
pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
```

### Q2: 数据库连接失败
```bash
# 默认使用 SQLite，无需额外配置
# 如需 PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/pptmaster
```

### Q3: 前端 npm install 失败
```bash
# 切换 npm 镜像
npm config set registry https://registry.npmmirror.com
npm install
```

### Q4: 导入原 PPT Master Skill 脚本
```bash
# 克隆原 skill 仓库
git clone https://github.com/hugohe3/ppt-master.git /opt/ppt-master

# 配置环境变量
echo "PPT_MASTER_SKILL_DIR=/opt/ppt-master/skills/ppt-master" >> backend/.env
```

---

## 九、模块验证状态

| 层级 | 模块数 | 导入状态 | 测试状态 |
|------|--------|----------|----------|
| Core (config/database) | 5 | **OK** | passed |
| Models (9张表) | 9 | **OK** | passed |
| Storage (local/minio) | 4 | **OK** | passed |
| Services (5个业务) | 5 | **OK** | passed |
| Pipeline (langchain) | 9 | **OK** | passed |
| API (8组路由) | 9 | **OK** | passed |
| Main | 1 | **OK** | - |
| **合计** | **44** | **44/44 OK** | **304/304** |
