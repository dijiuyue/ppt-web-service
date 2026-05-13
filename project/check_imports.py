#!/usr/bin/env python3
"""Systematically check all backend module imports."""

import sys
sys.path.insert(0, "/mnt/agents/output/ppt-web-service/project/backend")

import importlib
import pkgutil

MODULES_TO_TEST = [
    # Core
    "app.core.config",
    "app.core.database",
    "app.core.security",
    "app.core.schemas",
    "app.core.celery_app",
    # DB
    "app.db.base",
    # Models
    "app.models.project",
    "app.models.source_file",
    "app.models.design_spec",
    "app.models.spec_lock",
    "app.models.image_resource",
    "app.models.svg_page",
    "app.models.speaker_note",
    "app.models.pptx_export",
    "app.models.pipeline_job",
    # Storage
    "app.storage.base",
    "app.storage.local",
    "app.storage.minio",
    "app.storage.manager",
    # Services
    "app.services.project_service",
    "app.services.source_service",
    "app.services.design_spec_service",
    "app.services.pipeline_service",
    "app.services.storage_service",
    # Pipeline
    "app.pipeline.constants",
    "app.pipeline.state",
    "app.pipeline.llm",
    "app.pipeline.prompts",
    "app.pipeline.script_runner",
    "app.pipeline.workspace",
    "app.pipeline.graph",
    "app.pipeline.nodes",
    "app.pipeline.tasks",
    # API
    "app.api.deps",
    "app.api.projects",
    "app.api.sources",
    "app.api.design_spec",
    "app.api.pipeline",
    "app.api.svg_pages",
    "app.api.exports",
    "app.api.images",
    "app.api.websocket",
    "app.api",
    # Main
    "app.main",
]

results = {"ok": [], "fail": []}

for mod_name in MODULES_TO_TEST:
    try:
        importlib.import_module(mod_name)
        results["ok"].append(mod_name)
        print(f"  OK   {mod_name}")
    except Exception as e:
        results["fail"].append((mod_name, str(e)))
        print(f"  FAIL {mod_name} -> {e}")

print(f"\n{'='*60}")
print(f"Total: {len(results['ok'])} OK, {len(results['fail'])} FAILED")
if results["fail"]:
    print(f"\nFailed modules:")
    for name, err in results["fail"]:
        print(f"  - {name}: {err}")
