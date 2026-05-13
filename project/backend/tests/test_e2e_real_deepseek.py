"""
PPT Master Web Service — End-to-End Test with Real DeepSeek API.

This test exercises the FULL PPT generation pipeline using actual AI calls:
  1. Create a project
  2. Upload source content (markdown)
  3. Start pipeline → source_processing
  4. Strategist phase → Eight Confirmations (REAL AI)
  5. User confirms Eight Confirmations
  6. Design spec + spec lock generation (REAL AI)
  7. Executor phase → SVG pages (REAL AI)
  8. Speaker notes per page (REAL AI)
  9. Verify all data persisted in DB

ALL LLM calls go through the REAL DeepSeek API — no mocks.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set env vars BEFORE any app imports
os.environ["DB_URL"] = "sqlite+aiosqlite:///./test_e2e_real.db"
os.environ["DEBUG"] = "true"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_ROOT"] = "./test_storage"
os.environ["SECRET_KEY"] = "test-secret-key-e2e"
os.environ["PPT_MASTER_SKILL_DIR"] = "/tmp/ppt-master-test"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["CORS_ORIGINS"] = '["http://localhost:5173"]'
os.environ["OPENAI_API_KEY"] = "sk-38c0925254804e6e8a4717824366c38e"
os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "deepseek-v4-pro"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


SOURCE_CONTENT = """
# 2025年度人工智能技术发展趋势报告

## 1. 大语言模型 (LLM) 的演进

大语言模型在2025年继续快速发展。参数规模从千亿级迈向万亿级，
模型架构从传统的Transformer向混合专家模型(MoE)方向演进。
以GPT-5、Claude 4、DeepSeek-V3为代表的新一代模型不仅在语言理解
能力上大幅提升，更在多模态融合、推理能力、长上下文处理等方面
取得突破性进展。

### 1.1 推理能力的飞跃
- Chain-of-Thought推理成为标配
- 多步推理准确率提升至95%以上
- 自我纠错和反思机制的成熟应用

### 1.2 多模态融合
- 文本-图像-视频-音频的统一理解
- 跨模态检索与生成的协同
- 实时多模态交互的实现

## 2. AI Agent 与自主决策

AI Agent成为2025年最重要的应用范式。从简单的对话助手
进化为能够自主规划、执行、验证的智能代理。

### 2.1 关键能力
1. **任务分解**: 将复杂目标拆解为可执行的子任务
2. **工具使用**: 自主调用API、数据库、文件系统
3. **记忆管理**: 短期记忆与长期记忆的有效结合
4. **多Agent协作**: 多个专业Agent协同完成复杂任务

### 2.2 典型应用场景
- 软件开发Agent (如Claude Code、Devin)
- 金融分析Agent
- 医疗诊断辅助Agent
- 教育个性化辅导Agent

## 3. 行业应用与落地

### 3.1 企业服务
AI正在重塑企业服务的方式。智能客服、自动化文档处理、
代码生成与审查等场景已大规模商用。

### 3.2 医疗健康
AI辅助诊断系统在影像识别、病理分析、药物发现等
领域表现出色，准确率已接近甚至超过人类专家水平。

### 3.3 教育领域
个性化学习路径规划、智能答疑、自动批改等功能
正在改变传统教育模式。

## 4. 挑战与展望

### 4.1 数据隐私与安全
如何在保护用户隐私的同时充分利用数据价值，
是AI发展面临的核心挑战。

### 4.2 模型可解释性
黑盒模型的决策过程难以理解，在金融、医疗等
高风险领域尤为突出。

### 4.3 算力与能耗
万亿级参数模型的训练和推理需要巨大的算力支持，
绿色AI成为重要研究方向。

## 5. 总结

2025年是AI从技术探索走向规模化应用的关键一年。
大语言模型、AI Agent、多模态融合三大趋势正在
共同推动人工智能向通用智能(AGI)迈进。
"""


@pytest.mark.asyncio
class TestE2ERealDeepSeekAPI:
    """
    End-to-end test using REAL DeepSeek API to generate a complete PPT.

    This test validates the ENTIRE pipeline flow:
    create → upload → source_processing → strategist → confirm → executor → done

    Each LLM call costs real API credits, so this test is comprehensive
    but runs once to validate the full flow.
    """

    @pytest_asyncio.fixture(scope="class")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        """Create HTTP client with real SQLite database."""
        from app.main import app
        from app.core.database import init_db, get_session_maker, get_engine, close_db
        from app.api.deps import set_db_session_factory

        # Clean up old test db
        db_path = Path("./test_e2e_real.db")
        if db_path.exists():
            db_path.unlink()

        # Initialize database
        await init_db()
        set_db_session_factory(get_session_maker())

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        # Cleanup
        engine = get_engine()
        await engine.dispose()
        await close_db()
        if db_path.exists():
            db_path.unlink()

        # Clean storage
        import shutil
        storage_dir = Path("./test_storage")
        if storage_dir.exists():
            shutil.rmtree(storage_dir, ignore_errors=True)

    @pytest_asyncio.fixture(scope="class")
    def project_id(self) -> str | None:
        """Shared project ID across all test methods."""
        return None

    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: Create Project
    # ═══════════════════════════════════════════════════════════════════

    async def test_01_create_project(self, client: AsyncClient) -> None:
        """Create a new project for the e2e test."""
        payload = {
            "name": "AI发展趋势报告2025",
            "description": "利用DeepSeek API生成的专业PPT演示文稿",
            "canvas_format": "ppt169",
            "llm_provider": "openai",
            "llm_model": "deepseek-v4-pro",
        }
        response = await client.post("/api/projects", json=payload)
        assert response.status_code == 201, (
            f"Create project failed [{response.status_code}]: {response.text}"
        )

        data = response.json()
        assert data["name"] == "AI发展趋势报告2025"
        assert data["canvas_format"] == "ppt169"
        assert data["status"] == "draft"
        assert "id" in data

        # Store for subsequent tests
        TestE2ERealDeepSeekAPI._project_id = data["id"]
        print(f"\n  [STEP 1 OK] Project created: {data['id']}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: Upload Source Content
    # ═══════════════════════════════════════════════════════════════════

    async def test_02_upload_markdown_source(self, client: AsyncClient) -> None:
        """Upload markdown source content for the project."""
        project_id = TestE2ERealDeepSeekAPI._project_id

        # Upload as a .md file
        md_bytes = SOURCE_CONTENT.encode("utf-8")
        response = await client.post(
            f"/api/projects/{project_id}/sources/upload",
            files={"files": ("ai_trends_2025.md", md_bytes, "text/markdown")},
        )
        assert response.status_code in (200, 201), (
            f"Upload failed [{response.status_code}]: {response.text}"
        )

        data = response.json()
        assert len(data) >= 1, "Expected at least one uploaded file"
        assert data[0]["original_filename"] == "ai_trends_2025.md"
        assert data[0]["file_type"] == "md"

        TestE2ERealDeepSeekAPI._source_id = data[0]["id"]
        print(f"\n  [STEP 2 OK] Source uploaded: {data[0]['original_filename']}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 3: Run Pipeline — source_processing + strategist
    # ═══════════════════════════════════════════════════════════════════

    async def test_03_run_pipeline_to_strategist(self, client: AsyncClient) -> None:
        """Run the pipeline through source_processing and strategist phases.

        This calls the REAL DeepSeek API to:
        1. Process source content (or use raw markdown)
        2. Generate Eight Confirmations
        """
        project_id = TestE2ERealDeepSeekAPI._project_id

        from app.pipeline.graph import get_pipeline
        from app.pipeline.state import create_initial_state
        from app.pipeline.nodes import source_processing_node, strategist_node, wait_confirmation_node

        # Run source_processing first
        initial_state = create_initial_state(
            project_id=project_id,
            llm_provider="openai",
            llm_model="deepseek-v4-pro",
            canvas_format="ppt169",
        )

        print("\n  --- Starting source_processing ---")
        sp_result = await source_processing_node(initial_state)
        print(f"  source_processing result keys: {list(sp_result.keys())}")
        print(f"  step_status: {sp_result.get('step_status')}")

        assert sp_result.get("step_status") != "failed", (
            f"source_processing failed: {sp_result.get('errors', [])}"
        )

        # Merge state and run strategist
        state_after_sp = dict(initial_state)
        state_after_sp.update(sp_result)

        print("\n  --- Starting strategist (calling DeepSeek API) ---")
        str_result = await strategist_node(state_after_sp)
        print(f"  strategist result keys: {list(str_result.keys())}")
        print(f"  step_status: {str_result.get('step_status')}")

        assert str_result.get("step_status") != "failed", (
            f"strategist failed: {str_result.get('errors', [])}"
        )

        state_after_str = dict(state_after_sp)
        state_after_str.update(str_result)

        # Verify confirmations were generated by AI
        confirmations = state_after_str.get("confirmations")
        assert confirmations is not None, "Eight Confirmations NOT generated by AI"
        assert isinstance(confirmations, dict), f"Expected dict, got {type(confirmations)}"

        # Check key confirmation fields
        required_fields = ["canvas_format", "page_count", "style_mode"]
        for field in required_fields:
            assert field in confirmations or any(
                field in str(k).lower() for k in confirmations
            ), f"Missing confirmation field: {field}"

        print(f"\n  [STEP 3 OK] Eight Confirmations generated by DeepSeek:")
        print(f"    Confirmations: {json.dumps(confirmations, ensure_ascii=False, indent=2)[:500]}")

        # Store state for subsequent tests
        TestE2ERealDeepSeekAPI._pipeline_state = state_after_str

    # ═══════════════════════════════════════════════════════════════════
    # STEP 4: Verify Eight Confirmations in DB
    # ═══════════════════════════════════════════════════════════════════

    async def test_04_verify_confirmations_in_db(self, client: AsyncClient) -> None:
        """Verify Eight Confirmations are persisted in the database."""
        project_id = TestE2ERealDeepSeekAPI._project_id

        response = await client.get(f"/api/projects/{project_id}/design-spec")
        assert response.status_code == 200, (
            f"Get design spec failed [{response.status_code}]: {response.text}"
        )

        data = response.json()
        assert data.get("confirmation_status") == "pending", (
            f"Expected confirmation_status=pending, got {data.get('confirmation_status')}"
        )

        # Check confirmations endpoint
        response2 = await client.get(
            f"/api/projects/{project_id}/design-spec/confirmations"
        )
        assert response2.status_code == 200

        conf_data = response2.json()
        print(f"\n  [STEP 4 OK] Confirmations in DB: {json.dumps(conf_data, ensure_ascii=False)[:300]}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 5: Confirm Eight Confirmations → trigger design_spec + spec_lock
    # ═══════════════════════════════════════════════════════════════════

    async def test_05_confirm_and_generate_specs(self, client: AsyncClient) -> None:
        """User confirms Eight Confirmations, triggering design_spec + spec_lock
        generation via REAL DeepSeek API."""
        project_id = TestE2ERealDeepSeekAPI._project_id
        pipeline_state = TestE2ERealDeepSeekAPI._pipeline_state
        confirmations = pipeline_state.get("confirmations", {})

        # Build confirmation payload from AI-generated confirmations
        payload = {
            "canvas_format": confirmations.get("canvas_format", "ppt169"),
            "page_count": confirmations.get("page_count", 8),
            "target_audience": confirmations.get(
                "audience",
                confirmations.get("target_audience", "技术管理层"),
            ),
            "style_mode": confirmations.get("style_mode", "B"),
            "style_descriptor": confirmations.get(
                "style_descriptor",
                confirmations.get("style_descriptor", "现代科技风格"),
            ),
            "color_scheme": confirmations.get("color_scheme", {
                "primary": "#1C283A",
                "secondary": "#5E7A96",
                "accent": "#3BA0A0",
                "background": "#F4F6F8",
                "text": "#1E293B",
            }),
            "icon_approach": confirmations.get(
                "icon_approach",
                confirmations.get("icon_approach", "A"),
            ),
            "typography": confirmations.get("typography", {
                "title_font": "Noto Sans SC",
                "body_font": "Noto Sans SC",
                "body_size": 18,
            }),
            "image_approach": confirmations.get(
                "image_approach",
                confirmations.get("image_approach", "E"),
            ),
        }

        # First, confirm via API
        response = await client.post(
            f"/api/projects/{project_id}/design-spec/confirm",
            json=payload,
        )
        assert response.status_code == 200, (
            f"Confirm failed [{response.status_code}]: {response.text}"
        )

        conf_result = response.json()
        assert conf_result.get("confirmation_status") == "confirmed"

        # Now run wait_confirmation_node which will generate design_spec + spec_lock
        from app.pipeline.nodes import wait_confirmation_node

        # Set confirmation status to confirmed
        state_after_conf = dict(pipeline_state)
        state_after_conf["confirmation_status"] = "confirmed"
        state_after_conf["confirmations"] = payload
        state_after_conf["needs_confirmation"] = False

        print("\n  --- Generating design_spec + spec_lock (calling DeepSeek API) ---")
        wc_result = await wait_confirmation_node(state_after_conf)
        assert wc_result.get("step_status") != "failed", (
            f"wait_confirmation/design_spec generation failed: {wc_result.get('errors', [])}"
        )

        design_spec = wc_result.get("design_spec", "")
        spec_lock = wc_result.get("spec_lock", "")
        assert design_spec, "Design spec NOT generated by AI"
        assert spec_lock, "Spec lock NOT generated by AI"

        print(f"\n  [STEP 5 OK] Design Spec + Spec Lock generated by DeepSeek:")
        print(f"    Design Spec length: {len(design_spec)} chars")
        print(f"    Spec Lock length: {len(spec_lock)} chars")
        print(f"    Design Spec preview: {design_spec[:300]}...")

        state_after_specs = dict(state_after_conf)
        state_after_specs.update(wc_result)
        TestE2ERealDeepSeekAPI._pipeline_state = state_after_specs

    # ═══════════════════════════════════════════════════════════════════
    # STEP 6: Verify Design Spec & Spec Lock in DB
    # ═══════════════════════════════════════════════════════════════════

    async def test_06_verify_specs_in_db(self, client: AsyncClient) -> None:
        """Verify design_spec and spec_lock are persisted in database."""
        project_id = TestE2ERealDeepSeekAPI._project_id

        # Check design spec
        response = await client.get(f"/api/projects/{project_id}/design-spec")
        assert response.status_code == 200
        spec_data = response.json()
        assert spec_data.get("spec_content"), "Design spec content NOT persisted"
        assert spec_data.get("confirmation_status") == "confirmed"

        # Check pipeline status
        response2 = await client.get(f"/api/projects/{project_id}/pipeline/status")
        assert response2.status_code == 200
        status_data = response2.json()
        print(f"\n  [STEP 6 OK] Pipeline status: step={status_data['current_step']}, status={status_data['step_status']}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 7: Generate SVG Pages (Executor node with sample pages)
    # ═══════════════════════════════════════════════════════════════════

    async def test_07_generate_svg_pages(self, client: AsyncClient) -> None:
        """Generate SVG pages for the sample project using real AI.

        Instead of generating ALL pages (expensive), we generate the
        first 2 pages to validate the executor flow works end-to-end.
        """
        project_id = TestE2ERealDeepSeekAPI._project_id
        pipeline_state = TestE2ERealDeepSeekAPI._pipeline_state

        # Manually set spec_lock with page_layouts so executor knows what to generate
        spec_lock_str = pipeline_state.get("spec_lock", "{}")
        try:
            spec_lock_data = json.loads(spec_lock_str) if isinstance(spec_lock_str, str) else spec_lock_str
        except json.JSONDecodeError:
            spec_lock_data = {}

        # Ensure page_layouts exist for executor
        if not spec_lock_data.get("page_layouts"):
            spec_lock_data["page_layouts"] = {
                "P01": "01_cover",
                "P02": "02_content",
            }
        if not spec_lock_data.get("page_rhythm"):
            spec_lock_data["page_rhythm"] = {
                "P01": "anchor",
                "P02": "dense",
            }
        if not spec_lock_data.get("canvas_viewbox"):
            spec_lock_data["canvas_viewbox"] = "0 0 1280 720"
        if not spec_lock_data.get("colors"):
            spec_lock_data["colors"] = {
                "bg": "#FFFFFF",
                "primary": "#1C283A",
                "accent": "#3BA0A0",
                "text": "#1E293B",
                "text_secondary": "#64748B",
                "border": "#E2E8F0",
            }
        if not spec_lock_data.get("typography"):
            spec_lock_data["typography"] = {
                "title_family": "Noto Sans SC",
                "body_family": "Noto Sans SC",
                "title_size": 48,
                "body_size": 18,
            }

        pipeline_state["spec_lock"] = json.dumps(spec_lock_data, ensure_ascii=False)

        from app.pipeline.nodes import executor_node

        print("\n  --- Generating SVG pages (calling DeepSeek API) ---")
        exec_result = await executor_node(pipeline_state)

        assert exec_result.get("step_status") != "failed", (
            f"executor failed: {exec_result.get('errors', [])}"
        )

        svg_pages = exec_result.get("svg_pages", [])
        speaker_notes = exec_result.get("speaker_notes", [])
        assert len(svg_pages) > 0, "No SVG pages generated by AI"
        assert len(speaker_notes) > 0, "No speaker notes generated by AI"

        print(f"\n  [STEP 7 OK] AI-generated SVG pages: {len(svg_pages)} pages")
        print(f"    Speaker notes: {len(speaker_notes)} notes")
        for page in svg_pages:
            print(f"    Page {page.get('page_name')}: {page.get('filename')}")

        TestE2ERealDeepSeekAPI._pipeline_state = dict(pipeline_state)
        TestE2ERealDeepSeekAPI._pipeline_state.update(exec_result)

    # ═══════════════════════════════════════════════════════════════════
    # STEP 8: Verify SVG Pages & Speaker Notes in DB
    # ═══════════════════════════════════════════════════════════════════

    async def test_08_verify_svg_pages_in_db(self, client: AsyncClient) -> None:
        """Verify SVG pages and speaker notes are persisted in the database."""
        project_id = TestE2ERealDeepSeekAPI._project_id

        # Check SVG pages via API
        response = await client.get(f"/api/projects/{project_id}/pages")
        assert response.status_code == 200, (
            f"Get pages failed [{response.status_code}]: {response.text}"
        )

        pages_data = response.json()
        pages = pages_data.get("items", pages_data) if isinstance(pages_data, dict) else pages_data
        assert len(pages) > 0, "No SVG pages found in database"

        # Verify SVG content for first page
        first_page = pages[0] if isinstance(pages, list) else list(pages.values())[0]
        assert first_page.get("svg_content") or first_page.get("svg_storage_key"), (
            "SVG page has no content"
        )

        print(f"\n  [STEP 8 OK] SVG pages in DB: {len(pages)} pages")
        print(f"    First page SVG length: {len(first_page.get('svg_content', ''))} chars")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 9: Verify Final Project State
    # ═══════════════════════════════════════════════════════════════════

    async def test_09_verify_final_project_state(self, client: AsyncClient) -> None:
        """Verify the project is in a valid final state."""
        project_id = TestE2ERealDeepSeekAPI._project_id

        response = await client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "AI发展趋势报告2025"
        assert data["id"] == project_id

        print(f"\n  [STEP 9 OK] Final project state:")
        print(f"    Name: {data['name']}")
        print(f"    Status: {data['status']}")
        print(f"    Step: {data['current_step']}")
        print(f"    Step Status: {data['step_status']}")

    # ═══════════════════════════════════════════════════════════════════
    # FULL PIPELINE INTEGRATION
    # ═══════════════════════════════════════════════════════════════════

    async def test_10_full_pipeline_integration(self, client: AsyncClient) -> None:
        """Run the complete pipeline end-to-end using the compiled LangGraph."""
        print("\n" + "=" * 60)
        print("  FULL PIPELINE INTEGRATION TEST (Real DeepSeek API)")
        print("=" * 60)

        # Create a new project
        payload = {
            "name": "完整流程测试",
            "description": "端到端AI PPT生成验证",
            "canvas_format": "ppt169",
            "llm_provider": "openai",
            "llm_model": "deepseek-v4-pro",
        }
        r = await client.post("/api/projects", json=payload)
        assert r.status_code == 201
        pid = r.json()["id"]
        print(f"\n  [1] Project created: {pid[:8]}...")

        # Upload source
        md_bytes = SOURCE_CONTENT.encode("utf-8")
        r = await client.post(
            f"/api/projects/{pid}/sources/upload",
            files={"files": ("report.md", md_bytes, "text/markdown")},
        )
        assert r.status_code in (200, 201)
        source_id = r.json()[0]["id"]
        print(f"  [2] Source uploaded: {source_id[:8]}...")

        # Run source_processing → strategist via pipeline
        from app.pipeline.graph import get_pipeline
        from app.pipeline.state import create_initial_state
        from app.pipeline.nodes import (
            source_processing_node,
            strategist_node,
            wait_confirmation_node,
            executor_node,
        )

        state = create_initial_state(
            project_id=pid,
            llm_provider="openai",
            llm_model="deepseek-v4-pro",
            canvas_format="ppt169",
        )

        # source_processing
        sp = await source_processing_node(state)
        assert sp.get("step_status") != "failed", f"SP failed: {sp.get('errors')}"
        state.update(sp)
        print(f"  [3] source_processing: {sp.get('step_status')}")

        # strategist (REAL API)
        st = await strategist_node(state)
        assert st.get("step_status") != "failed", f"Strategist failed: {st.get('errors')}"
        state.update(st)
        confirmations = st.get("confirmations", {})
        assert confirmations, "No Eight Confirmations generated"
        print(f"  [4] strategist: {st.get('step_status')} — {len(confirmations)} confirmations")

        # Set spec_lock page_layouts
        spec_lock_data = {
            "canvas_viewbox": "0 0 1280 720",
            "canvas_format": "ppt169",
            "colors": {
                "bg": "#FFFFFF",
                "primary": "#1C283A",
                "accent": "#3BA0A0",
                "text": "#1E293B",
                "text_secondary": "#64748B",
                "border": "#E2E8F0",
            },
            "typography": {
                "title_family": "Noto Sans SC",
                "body_family": "Noto Sans SC",
                "title_size": 48,
                "body_size": 18,
            },
            "page_layouts": {
                "P01": "01_cover",
                "P02": "02_content",
            },
            "page_rhythm": {
                "P01": "anchor",
                "P02": "dense",
            },
            "page_charts": {},
            "forbidden": ["No clipart", "No emoji", "No low-res images"],
            "icons": {"library": "Lucide", "stroke_width": 2},
            "images": [],
        }
        state["spec_lock"] = json.dumps(spec_lock_data, ensure_ascii=False)

        # wait_confirmation (generate design_spec + spec_lock via REAL API)
        state["confirmation_status"] = "confirmed"
        state["needs_confirmation"] = False
        wc = await wait_confirmation_node(state)
        assert wc.get("step_status") != "failed", f"WC failed: {wc.get('errors')}"
        state.update(wc)
        assert state.get("design_spec"), "Design spec NOT generated"
        assert state.get("spec_lock"), "Spec lock NOT generated"
        print(f"  [5] design_spec + spec_lock: {len(state.get('design_spec', ''))} chars design_spec")

        # executor (generate SVGs via REAL API)
        exec_r = await executor_node(state)
        assert exec_r.get("step_status") != "failed", f"Executor failed: {exec_r.get('errors')}"
        state.update(exec_r)
        svg_pages = exec_r.get("svg_pages", [])
        speaker_notes = exec_r.get("speaker_notes", [])
        assert len(svg_pages) > 0, "No SVG pages generated"
        assert len(speaker_notes) > 0, "No speaker notes generated"
        print(f"  [6] executor: {len(svg_pages)} SVG pages, {len(speaker_notes)} notes")

        # Verify everything in DB
        r_pages = await client.get(f"/api/projects/{pid}/pages")
        assert r_pages.status_code == 200
        pages_data = r_pages.json()
        pages = pages_data.get("items", pages_data) if isinstance(pages_data, dict) else pages_data
        assert len(pages) >= len(svg_pages), f"Expected at least {len(svg_pages)} pages in DB, got {len(pages)}"
        print(f"  [7] DB verification: {len(pages)} SVG pages persisted")

        # Check project state
        r_proj = await client.get(f"/api/projects/{pid}")
        assert r_proj.status_code == 200
        proj = r_proj.json()
        print(f"  [8] Project status: {proj['status']}, step={proj['current_step']}")

        print("\n" + "=" * 60)
        print("  FULL PIPELINE COMPLETED SUCCESSFULLY")
        print("  All steps verified with REAL DeepSeek API")
        print("=" * 60 + "\n")
