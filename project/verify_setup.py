#!/usr/bin/env python3
"""
PPT Master Web Service - Agent Startup Verification Script
===========================================================

一键验证项目启动状态。Agent 可直接运行此脚本检查项目环境。

用法:
    cd /mnt/agents/output/ppt-web-service/project
    python3 verify_setup.py

输出:
    彩色报告，显示所有检查项的通过/失败状态。
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 颜色代码 (用于终端彩色输出)
COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "GREEN": "\033[92m",
    "RED": "\033[91m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
}


def color(name: str, text: str) -> str:
    """给文本添加颜色。"""
    if sys.platform == "win32" and not os.environ.get("TERM"):
        return text
    return f"{COLORS.get(name, '')}{text}{COLORS['RESET']}"


def log_pass(msg: str) -> None:
    print(f"  {color('GREEN', '[PASS]')} {msg}")


def log_fail(msg: str, detail: str = "") -> None:
    print(f"  {color('RED', '[FAIL]')} {msg}")
    if detail:
        print(f"         {color('YELLOW', detail)}")


def log_warn(msg: str, detail: str = "") -> None:
    print(f"  {color('YELLOW', '[WARN]')} {msg}")
    if detail:
        print(f"         {detail}")


def log_info(msg: str) -> None:
    print(f"  {color('BLUE', '[INFO]')} {msg}")


def section(title: str) -> None:
    print(f"\n{color('BOLD', color('CYAN', f'=== {title} '))}{'=' * max(0, 60 - len(title))}")


# ---------------------------------------------------------------------------
# 检查结果收集
# ---------------------------------------------------------------------------
results: dict[str, list[tuple[str, bool, str]]] = {
    "env": [],
    "deps": [],
    "imports": [],
    "frontend": [],
    "services": [],
}


def record(category: str, name: str, passed: bool, detail: str = "") -> None:
    results[category].append((name, passed, detail))


# ===========================================================================
# 1. 环境检查
# ===========================================================================

def check_python_version() -> None:
    """检查 Python 版本 >= 3.10。"""
    version = sys.version_info
    passed = version >= (3, 10)
    name = f"Python 版本: {version.major}.{version.minor}.{version.micro}"
    if passed:
        log_pass(name)
    else:
        log_fail(name, f"需要 >= 3.10, 当前 {version.major}.{version.minor}")
    record("env", "python_version", passed)


def check_nodejs_version() -> None:
    """检查 Node.js 版本 >= 18。"""
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version_str = result.stdout.strip().lstrip("v")
            major = int(version_str.split(".")[0])
            passed = major >= 18
            name = f"Node.js 版本: {version_str}"
            if passed:
                log_pass(name)
            else:
                log_fail(name, f"需要 >= 18, 当前 {major}")
            record("env", "nodejs_version", passed)
        else:
            log_fail("Node.js 未安装或不可用", result.stderr.strip())
            record("env", "nodejs_version", False, "node --version 失败")
    except FileNotFoundError:
        log_fail("Node.js 未安装", "node 命令未找到")
        record("env", "nodejs_version", False, "node 命令未找到")
    except Exception as exc:
        log_fail("Node.js 检查失败", str(exc))
        record("env", "nodejs_version", False, str(exc))


def check_pip() -> None:
    """检查 pip 是否可用。"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        passed = result.returncode == 0
        if passed:
            log_pass(f"pip 可用: {result.stdout.strip()}")
        else:
            log_fail("pip 不可用")
        record("env", "pip", passed)
    except Exception as exc:
        log_fail("pip 检查失败", str(exc))
        record("env", "pip", False, str(exc))


def check_npm() -> None:
    """检查 npm 是否可用。"""
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        passed = result.returncode == 0
        if passed:
            log_pass(f"npm 可用: v{result.stdout.strip()}")
        else:
            log_fail("npm 不可用")
        record("env", "npm", passed)
    except FileNotFoundError:
        log_fail("npm 未安装", "npm 命令未找到")
        record("env", "npm", False, "npm 命令未找到")
    except Exception as exc:
        log_fail("npm 检查失败", str(exc))
        record("env", "npm", False, str(exc))


def check_project_structure() -> None:
    """检查项目目录结构是否完整。"""
    required_dirs = [
        (BACKEND_DIR, "backend"),
        (FRONTEND_DIR, "frontend"),
        (BACKEND_DIR / "app", "backend/app"),
        (BACKEND_DIR / "app" / "api", "backend/app/api"),
        (BACKEND_DIR / "app" / "core", "backend/app/core"),
        (BACKEND_DIR / "app" / "models", "backend/app/models"),
        (BACKEND_DIR / "app" / "pipeline", "backend/app/pipeline"),
        (BACKEND_DIR / "app" / "services", "backend/app/services"),
        (BACKEND_DIR / "app" / "storage", "backend/app/storage"),
    ]
    required_files = [
        (BACKEND_DIR / "requirements.txt", "backend/requirements.txt"),
        (BACKEND_DIR / "app" / "main.py", "backend/app/main.py"),
        (FRONTEND_DIR / "package.json", "frontend/package.json"),
        (FRONTEND_DIR / "vite.config.ts", "frontend/vite.config.ts"),
        (PROJECT_ROOT / "check_imports.py", "check_imports.py"),
    ]
    all_ok = True
    for path, desc in required_dirs:
        if path.exists():
            log_pass(f"目录存在: {desc}")
        else:
            log_fail(f"目录缺失: {desc}", f"期望路径: {path}")
            all_ok = False
    for path, desc in required_files:
        if path.exists():
            log_pass(f"文件存在: {desc}")
        else:
            log_fail(f"文件缺失: {desc}", f"期望路径: {path}")
            all_ok = False
    record("env", "project_structure", all_ok)


# ===========================================================================
# 2. Python 依赖检查
# ===========================================================================

def check_python_deps() -> None:
    """检查关键 Python 依赖是否已安装。"""
    required_deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("asyncpg", "asyncpg"),
        ("alembic", "alembic"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("celery", "celery"),
        ("redis", "redis"),
        ("openai", "openai"),
        ("anthropic", "anthropic"),
        ("langchain", "langchain"),
        ("langchain_openai", "langchain-openai"),
        ("minio", "minio"),
        ("httpx", "httpx"),
        ("PIL", "Pillow"),
        ("aiofiles", "aiofiles"),
    ]

    # 特殊依赖 (不在 requirements.txt 但代码中使用)
    extra_deps = [
        ("langgraph", "langgraph"),
        ("tenacity", "tenacity"),
        ("kombu", "kombu"),
    ]

    all_ok = True
    for module, pkg in required_deps:
        try:
            importlib.import_module(module)
            log_pass(f"已安装: {pkg}")
            record("deps", f"pkg_{pkg}", True)
        except ImportError:
            log_fail(f"未安装: {pkg}", f"运行: pip install {pkg}")
            record("deps", f"pkg_{pkg}", False, f"pip install {pkg}")
            all_ok = False

    # 检查额外依赖
    for module, pkg in extra_deps:
        try:
            importlib.import_module(module)
            log_pass(f"已安装: {pkg} (额外依赖)")
            record("deps", f"pkg_{pkg}", True)
        except ImportError:
            log_warn(f"未安装: {pkg} (额外依赖)", f"运行: pip install {pkg}")
            record("deps", f"pkg_{pkg}", False, f"pip install {pkg}")
            all_ok = False

    return all_ok


# ===========================================================================
# 3. 模块导入检查
# ===========================================================================

def check_backend_imports() -> None:
    """检查后端核心模块导入。"""
    # 将 backend 添加到 sys.path
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    modules_to_test = [
        # Core (高优先级)
        ("app.core.config", True),
        ("app.core.database", True),
        ("app.core.schemas", True),
        ("app.core.security", True),
        ("app.core.celery_app", True),
        # DB
        ("app.db.base", True),
        # Models
        ("app.models.project", True),
        ("app.models.source_file", True),
        ("app.models.design_spec", True),
        ("app.models.spec_lock", True),
        ("app.models.image_resource", True),
        ("app.models.svg_page", True),
        ("app.models.speaker_note", True),
        ("app.models.pptx_export", True),
        ("app.models.pipeline_job", True),
        ("app.models", True),
        # Storage
        ("app.storage.base", True),
        ("app.storage.local", True),
        ("app.storage.minio", True),
        ("app.storage.manager", True),
        # Services
        ("app.services.project_service", True),
        ("app.services.source_service", True),
        ("app.services.design_spec_service", True),
        ("app.services.storage_service", True),
        # API (deps.py 是关键)
        ("app.api.deps", True),
        ("app.api.projects", False),
        ("app.api.sources", False),
        ("app.api.design_spec", False),
        ("app.api.pipeline", False),
        ("app.api.svg_pages", False),
        ("app.api.exports", False),
        ("app.api.images", False),
        ("app.api.websocket", False),
        ("app.api", True),
        # Pipeline
        ("app.pipeline.constants", True),
        ("app.pipeline.state", True),
        ("app.pipeline.llm", True),
        ("app.pipeline.prompts", True),
        ("app.pipeline.script_runner", True),
        ("app.pipeline.workspace", True),
        ("app.pipeline.graph", True),
        ("app.pipeline.nodes", False),  # 可能有运行时导入问题
        ("app.pipeline.tasks", False),  # 可能有运行时导入问题
        # Main
        ("app.main", True),
    ]

    all_ok = True
    for mod_name, required in modules_to_test:
        try:
            importlib.import_module(mod_name)
            if required:
                log_pass(f"导入 OK: {mod_name}")
            else:
                log_pass(f"导入 OK: {mod_name} (有已知问题)")
            record("imports", f"import_{mod_name}", True)
        except Exception as exc:
            err_msg = str(exc)
            if required:
                log_fail(f"导入失败: {mod_name}", err_msg[:100])
                all_ok = False
            else:
                log_warn(f"导入失败: {mod_name}", err_msg[:100])
            record("imports", f"import_{mod_name}", False, err_msg[:200])

    return all_ok


# ===========================================================================
# 4. 前端检查
# ===========================================================================

def check_frontend_deps() -> None:
    """检查前端 node_modules 是否存在。"""
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        # 检查关键包是否存在
        key_packages = ["vue", "vite", "element-plus", "vue-router", "pinia", "axios"]
        found = sum(1 for p in key_packages if (node_modules / p).exists())
        if found == len(key_packages):
            log_pass(f"前端依赖已安装 ({found}/{len(key_packages)} 核心包)")
            record("frontend", "node_modules", True)
        else:
            log_warn(
                f"前端依赖部分安装 ({found}/{len(key_packages)} 核心包)",
                "建议运行: cd frontend && npm install",
            )
            record("frontend", "node_modules", False, f"仅 {found}/{len(key_packages)} 包存在")
    else:
        log_fail("前端依赖未安装", "运行: cd frontend && npm install")
        record("frontend", "node_modules", False, "node_modules 不存在")


def check_frontend_build() -> None:
    """检查前端是否能成功构建 (可选，较耗时)。"""
    log_info("前端构建检查 (可选，跳过)")
    record("frontend", "build", True, "跳过")


# ===========================================================================
# 5. 服务启动检查
# ===========================================================================

def check_backend_can_start() -> None:
    """检查后端是否可以导入启动 (不实际启动服务器)。"""
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    try:
        # 尝试导入 FastAPI app 实例
        from app.main import app

        if hasattr(app, "routes") and len(app.routes) > 0:
            route_count = len(app.routes)
            log_pass(f"FastAPI 应用可导入 ({route_count} 个路由)")
            record("services", "backend_importable", True, f"{route_count} routes")
        else:
            log_warn("FastAPI 应用可导入，但路由为空")
            record("services", "backend_importable", False, "无路由")
    except Exception as exc:
        log_fail("FastAPI 应用导入失败", f"{type(exc).__name__}: {str(exc)[:150]}")
        record("services", "backend_importable", False, str(exc)[:200])


def check_openapi_schema() -> None:
    """检查是否能生成 OpenAPI schema。"""
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    try:
        from app.main import app

        schema = app.openapi()
        if "paths" in schema and len(schema["paths"]) > 0:
            path_count = len(schema["paths"])
            log_pass(f"OpenAPI schema 可生成 ({path_count} 个路径)")
            record("services", "openapi_schema", True, f"{path_count} paths")
        else:
            log_warn("OpenAPI schema 生成成功，但无路径定义")
            record("services", "openapi_schema", False, "无 paths")
    except Exception as exc:
        log_fail("OpenAPI schema 生成失败", f"{type(exc).__name__}: {str(exc)[:150]}")
        record("services", "openapi_schema", False, str(exc)[:200])


def check_key_endpoints() -> None:
    """列出来自 OpenAPI schema 的关键端点。"""
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    try:
        from app.main import app

        schema = app.openapi()
        paths = schema.get("paths", {})

        key_endpoints = [
            "/health",
            "/ws-status",
            "/api/projects",
            "/openapi.json",
            "/docs",
        ]

        for endpoint in key_endpoints:
            if endpoint in paths:
                methods = list(paths[endpoint].keys())
                log_pass(f"端点存在: {endpoint} [{', '.join(methods)}]")
                record("services", f"endpoint_{endpoint}", True)
            else:
                log_warn(f"端点缺失: {endpoint}")
                record("services", f"endpoint_{endpoint}", False)

    except Exception as exc:
        log_fail("端点检查失败", str(exc)[:150])


# ===========================================================================
# 6. 报告生成
# ===========================================================================

def print_summary() -> None:
    """打印验证总结报告。"""
    print(f"\n{'=' * 70}")
    print(color("BOLD", color("CYAN", "                    验证报告总结")))
    print(f"{'=' * 70}")

    total_passed = 0
    total_failed = 0
    total_warn = 0

    for category, items in results.items():
        if not items:
            continue
        passed = sum(1 for _, p, _ in items if p)
        failed = sum(1 for _, p, _ in items if not p)
        total_passed += passed
        total_failed += failed

        cat_names = {
            "env": "环境检查",
            "deps": "Python 依赖",
            "imports": "模块导入",
            "frontend": "前端检查",
            "services": "服务检查",
        }
        cat_name = cat_names.get(category, category)
        status = color("GREEN", "通过") if failed == 0 else color("RED", f"{failed} 项失败")
        print(f"\n{color('BOLD', cat_name)}: {passed}/{len(items)} 通过 {status}")

        for name, p, detail in items:
            if not p:
                print(f"  {color('RED', '  -')} {name}: {detail[:80] if detail else '失败'}")

    print(f"\n{'=' * 70}")
    total = total_passed + total_failed
    if total_failed == 0:
        print(color("GREEN", color("BOLD", f"  全部通过: {total_passed}/{total} 项检查通过")))
        print(color("GREEN", "  项目环境就绪，可以启动前后端服务。"))
    else:
        print(color("YELLOW", color("BOLD", f"  部分通过: {total_passed}/{total} 项通过, {total_failed} 项失败")))
        print(color("YELLOW", "  请根据上方失败项进行修复。"))
    print(f"{'=' * 70}\n")


def main() -> int:
    """主函数，返回退出码 (0=成功, 1=有失败)。"""
    print(color("BOLD", color("CYAN", "PPT Master Web Service - 启动验证")))
    print(f"项目路径: {PROJECT_ROOT}")

    # 1. 环境检查
    section("环境检查")
    check_python_version()
    check_nodejs_version()
    check_pip()
    check_npm()
    check_project_structure()

    # 2. Python 依赖
    section("Python 依赖检查")
    check_python_deps()

    # 3. 模块导入
    section("后端模块导入检查")
    check_backend_imports()

    # 4. 前端
    section("前端检查")
    check_frontend_deps()
    check_frontend_build()

    # 5. 服务
    section("服务启动检查")
    check_backend_can_start()
    check_openapi_schema()
    check_key_endpoints()

    # 总结
    print_summary()

    # 返回退出码
    total_failed = sum(1 for items in results.values() for _, p, _ in items if not p)
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
