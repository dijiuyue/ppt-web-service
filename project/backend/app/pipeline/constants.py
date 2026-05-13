"""
PPT Master Pipeline - Constants and configuration.

Defines paths, timeouts, and other configuration constants used throughout
the pipeline for integrating with the original PPT Master skill scripts.
"""

import os

# ---------------------------------------------------------------------------
# Skill script directory (mounted read-only in container)
# ---------------------------------------------------------------------------
PPT_MASTER_SKILL_DIR = os.environ.get(
    "PPT_MASTER_SKILL_DIR",
    "/app/ppt-master/skills/ppt-master",
)

# Scripts subdirectory
SCRIPTS_DIR = os.path.join(PPT_MASTER_SKILL_DIR, "scripts")
SOURCE_TO_MD_DIR = os.path.join(SCRIPTS_DIR, "source_to_md")

# ---------------------------------------------------------------------------
# Individual script paths
# ---------------------------------------------------------------------------
PDF_TO_MD_SCRIPT = os.path.join(SOURCE_TO_MD_DIR, "pdf_to_md.py")
DOC_TO_MD_SCRIPT = os.path.join(SOURCE_TO_MD_DIR, "doc_to_md.py")
EXCEL_TO_MD_SCRIPT = os.path.join(SOURCE_TO_MD_DIR, "excel_to_md.py")
PPT_TO_MD_SCRIPT = os.path.join(SOURCE_TO_MD_DIR, "ppt_to_md.py")
WEB_TO_MD_SCRIPT = os.path.join(SOURCE_TO_MD_DIR, "web_to_md.py")

PROJECT_MANAGER_SCRIPT = os.path.join(SCRIPTS_DIR, "project_manager.py")
SVG_QUALITY_CHECKER_SCRIPT = os.path.join(SCRIPTS_DIR, "svg_quality_checker.py")
FINALIZE_SVG_SCRIPT = os.path.join(SCRIPTS_DIR, "finalize_svg.py")
SVG_TO_PPTX_SCRIPT = os.path.join(SCRIPTS_DIR, "svg_to_pptx.py")
TOTAL_MD_SPLIT_SCRIPT = os.path.join(SCRIPTS_DIR, "total_md_split.py")
IMAGE_GEN_SCRIPT = os.path.join(SCRIPTS_DIR, "image_gen.py")
IMAGE_SEARCH_SCRIPT = os.path.join(SCRIPTS_DIR, "image_search.py")
ANALYZE_IMAGES_SCRIPT = os.path.join(SCRIPTS_DIR, "analyze_images.py")

# ---------------------------------------------------------------------------
# Timeout settings (seconds)
# ---------------------------------------------------------------------------
TIMEOUT_PDF_TO_MD = int(os.environ.get("TIMEOUT_PDF_TO_MD", "300"))
TIMEOUT_DOC_TO_MD = int(os.environ.get("TIMEOUT_DOC_TO_MD", "300"))
TIMEOUT_EXCEL_TO_MD = int(os.environ.get("TIMEOUT_EXCEL_TO_MD", "300"))
TIMEOUT_PPT_TO_MD = int(os.environ.get("TIMEOUT_PPT_TO_MD", "300"))
TIMEOUT_WEB_TO_MD = int(os.environ.get("TIMEOUT_WEB_TO_MD", "120"))
TIMEOUT_PROJECT_MANAGER = int(os.environ.get("TIMEOUT_PROJECT_MANAGER", "60"))
TIMEOUT_IMAGE_GEN = int(os.environ.get("TIMEOUT_IMAGE_GEN", "300"))
TIMEOUT_IMAGE_SEARCH = int(os.environ.get("TIMEOUT_IMAGE_SEARCH", "120"))
TIMEOUT_SVG_QUALITY_CHECK = int(os.environ.get("TIMEOUT_SVG_QUALITY_CHECK", "120"))
TIMEOUT_FINALIZE_SVG = int(os.environ.get("TIMEOUT_FINALIZE_SVG", "300"))
TIMEOUT_SVG_TO_PPTX = int(os.environ.get("TIMEOUT_SVG_TO_PPTX", "300"))
TIMEOUT_TOTAL_MD_SPLIT = int(os.environ.get("TIMEOUT_TOTAL_MD_SPLIT", "60"))
TIMEOUT_ANALYZE_IMAGES = int(os.environ.get("TIMEOUT_ANALYZE_IMAGES", "120"))

# ---------------------------------------------------------------------------
# LLM settings
# ---------------------------------------------------------------------------
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
LLM_RETRY_DELAY_BASE = float(os.environ.get("LLM_RETRY_DELAY_BASE", "2.0"))
LLM_REQUEST_TIMEOUT = int(os.environ.get("LLM_REQUEST_TIMEOUT", "120"))

# Available models
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini"]
ANTHROPIC_MODELS = ["claude-3-5-sonnet-latest", "claude-3-haiku-latest"]
DEEPSEEK_MODELS = ["deepseek-v4-pro", "deepseek-reasoner", "deepseek-chat"]

# ---------------------------------------------------------------------------
# Workspace settings
# ---------------------------------------------------------------------------
WORKSPACE_BASE_DIR = os.environ.get(
    "WORKSPACE_BASE_DIR",
    "/tmp/ppt_master_workspaces",
)
WORKSPACE_MAX_AGE_HOURS = int(os.environ.get("WORKSPACE_MAX_AGE_HOURS", "24"))

# ---------------------------------------------------------------------------
# Celery settings
# ---------------------------------------------------------------------------
CELERY_TASK_MAX_RETRIES = int(os.environ.get("CELERY_TASK_MAX_RETRIES", "3"))
CELERY_RETRY_COUNTDOWN = int(os.environ.get("CELERY_RETRY_COUNTDOWN", "60"))

# ---------------------------------------------------------------------------
# Pipeline step definitions
# ---------------------------------------------------------------------------
PIPELINE_STEPS = [
    "init",
    "source_processing",
    "strategist",
    "image_acquisition",
    "executor",
    "post_processing",
    "completed",
]

# Steps that can be resumed from
RESUMABLE_STEPS = [
    "source_processing",
    "strategist",
    "image_acquisition",
    "executor",
    "post_processing",
]

# ---------------------------------------------------------------------------
# Canvas format defaults
# ---------------------------------------------------------------------------
CANVAS_FORMATS = {
    "ppt169": {"viewbox": "0 0 1280 720", "width": 1280, "height": 720},
    "ppt43": {"viewbox": "0 0 960 720", "width": 960, "height": 720},
    "xhs": {"viewbox": "0 0 900 1200", "width": 900, "height": 1200},
    "story": {"viewbox": "0 0 1080 1920", "width": 1080, "height": 1920},
}

DEFAULT_CANVAS_FORMAT = "ppt169"
