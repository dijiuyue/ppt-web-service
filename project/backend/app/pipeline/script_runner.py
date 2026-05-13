"""
PPT Master Pipeline - Original skill script wrapper.

Provides async wrappers around the original PPT Master skill scripts,
invoking them via asyncio subprocess and handling input/output through
temporary files and stdout/stderr capture.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from app.pipeline.constants import (
    ANALYZE_IMAGES_SCRIPT,
    DOC_TO_MD_SCRIPT,
    EXCEL_TO_MD_SCRIPT,
    FINALIZE_SVG_SCRIPT,
    IMAGE_GEN_SCRIPT,
    IMAGE_SEARCH_SCRIPT,
    PDF_TO_MD_SCRIPT,
    PPT_TO_MD_SCRIPT,
    PROJECT_MANAGER_SCRIPT,
    SVG_QUALITY_CHECKER_SCRIPT,
    SVG_TO_PPTX_SCRIPT,
    TOTAL_MD_SPLIT_SCRIPT,
    TIMEOUT_ANALYZE_IMAGES,
    TIMEOUT_DOC_TO_MD,
    TIMEOUT_EXCEL_TO_MD,
    TIMEOUT_FINALIZE_SVG,
    TIMEOUT_IMAGE_GEN,
    TIMEOUT_IMAGE_SEARCH,
    TIMEOUT_PDF_TO_MD,
    TIMEOUT_PPT_TO_MD,
    TIMEOUT_PROJECT_MANAGER,
    TIMEOUT_SVG_QUALITY_CHECK,
    TIMEOUT_SVG_TO_PPTX,
    TIMEOUT_TOTAL_MD_SPLIT,
    TIMEOUT_WEB_TO_MD,
    WEB_TO_MD_SCRIPT,
)

logger = logging.getLogger(__name__)


class ScriptRunnerError(Exception):
    """Raised when a skill script execution fails."""


class ScriptRunner:
    """
    Async wrapper for the original PPT Master skill scripts.

    All methods use ``asyncio.create_subprocess_exec`` for non-blocking
    execution and return structured results.
    """

    def __init__(self, skill_dir: str | None = None) -> None:
        self.skill_dir = skill_dir or os.environ.get(
            "PPT_MASTER_SKILL_DIR",
            "/app/ppt-master/skills/ppt-master",
        )
        self.python = sys.executable

    # -- Internal subprocess helper ----------------------------------------

    async def _run_script(
        self,
        script_path: str,
        args: list[str],
        timeout: int,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        input_data: bytes | None = None,
    ) -> tuple[int, str, str]:
        """
        Run a Python script via async subprocess.

        Returns:
            Tuple of (returncode, stdout, stderr).

        Raises:
            ScriptRunnerError: On non-zero exit code or timeout.
        """
        cmd = [self.python, script_path, *args]
        logger.debug(
            "Running script: %s (timeout=%ds, cwd=%s)",
            " ".join(cmd),
            timeout,
            cwd or os.getcwd(),
        )

        merged_env = dict(os.environ)
        if env:
            merged_env.update(env)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=merged_env,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_data),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise ScriptRunnerError(
                f"Script timed out after {timeout}s: {script_path}"
            )

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            logger.error(
                "Script failed (rc=%d): %s\nstderr: %s",
                proc.returncode,
                script_path,
                err,
            )
            raise ScriptRunnerError(
                f"Script exited with code {proc.returncode}: {script_path}\n{err}"
            )

        if err:
            logger.warning("Script stderr: %s", err)

        return proc.returncode, out, err

    # ------------------------------------------------------------------
    # Source → Markdown conversions
    # ------------------------------------------------------------------

    async def run_pdf_to_md(self, pdf_path: str) -> str:
        """
        Convert a PDF file to Markdown.

        Args:
            pdf_path: Absolute path to the PDF file.

        Returns:
            Markdown content string.
        """
        _, stdout, _ = await self._run_script(
            PDF_TO_MD_SCRIPT,
            [pdf_path],
            timeout=TIMEOUT_PDF_TO_MD,
        )
        return stdout

    async def run_doc_to_md(self, doc_path: str) -> str:
        """Convert a Word document (.docx) to Markdown."""
        _, stdout, _ = await self._run_script(
            DOC_TO_MD_SCRIPT,
            [doc_path],
            timeout=TIMEOUT_DOC_TO_MD,
        )
        return stdout

    async def run_excel_to_md(self, excel_path: str) -> str:
        """Convert an Excel file (.xlsx) to Markdown."""
        _, stdout, _ = await self._run_script(
            EXCEL_TO_MD_SCRIPT,
            [excel_path],
            timeout=TIMEOUT_EXCEL_TO_MD,
        )
        return stdout

    async def run_ppt_to_md(self, ppt_path: str) -> str:
        """Convert a PowerPoint file (.pptx) to Markdown."""
        _, stdout, _ = await self._run_script(
            PPT_TO_MD_SCRIPT,
            [ppt_path],
            timeout=TIMEOUT_PPT_TO_MD,
        )
        return stdout

    async def run_web_to_md(self, url: str) -> str:
        """Fetch a web page and convert to Markdown."""
        _, stdout, _ = await self._run_script(
            WEB_TO_MD_SCRIPT,
            [url],
            timeout=TIMEOUT_WEB_TO_MD,
        )
        return stdout

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------

    async def run_project_manager_init(
        self,
        name: str,
        format: str = "ppt169",
        output_dir: str | None = None,
    ) -> str:
        """
        Initialize a new PPT Master project.

        Args:
            name: Project name.
            format: Canvas format (ppt169 / ppt43 / xhs / story).
            output_dir: Directory to create the project in.

        Returns:
            Path to the created project directory.
        """
        args = ["init", name, "--format", format]
        if output_dir:
            args.extend(["--output-dir", output_dir])

        _, stdout, _ = await self._run_script(
            PROJECT_MANAGER_SCRIPT,
            args,
            timeout=TIMEOUT_PROJECT_MANAGER,
            cwd=output_dir,
        )
        # The script prints the project path on success
        return stdout.strip().splitlines()[-1] if stdout.strip() else ""

    async def run_import_sources(
        self,
        project_path: str,
        sources: list[str],
    ) -> dict[str, Any]:
        """
        Import source files into a project.

        Args:
            project_path: Path to the project directory.
            sources: List of source file paths to import.

        Returns:
            Summary dict with import results.
        """
        results: dict[str, Any] = {"imported": [], "failed": []}
        for src in sources:
            try:
                _, stdout, _ = await self._run_script(
                    PROJECT_MANAGER_SCRIPT,
                    ["import", "--project", project_path, src],
                    timeout=TIMEOUT_PROJECT_MANAGER,
                )
                results["imported"].append({"source": src, "output": stdout})
            except ScriptRunnerError as exc:
                logger.error("Failed to import source %s: %s", src, exc)
                results["failed"].append({"source": src, "error": str(exc)})
        return results

    # ------------------------------------------------------------------
    # Image operations
    # ------------------------------------------------------------------

    async def run_image_gen(
        self,
        project_path: str,
        prompt: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
    ) -> str:
        """
        Generate an image using AI.

        Args:
            project_path: Project directory path.
            prompt: Image generation prompt.
            output_path: Where to save the generated image.
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            Path to the generated image file.
        """
        args = [
            "--project", project_path,
            "--prompt", prompt,
            "--output", output_path,
            "--width", str(width),
            "--height", str(height),
        ]
        _, stdout, _ = await self._run_script(
            IMAGE_GEN_SCRIPT,
            args,
            timeout=TIMEOUT_IMAGE_GEN,
        )
        # Return the actual output path
        return output_path if os.path.exists(output_path) else stdout.strip()

    async def run_image_search(
        self,
        project_path: str,
        query: str,
        output_path: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """
        Search for images on the web.

        Args:
            project_path: Project directory path.
            query: Search query string.
            output_path: Directory to save downloaded images.
            max_results: Maximum number of results.

        Returns:
            Dict with search results and downloaded file paths.
        """
        args = [
            "--project", project_path,
            "--query", query,
            "--output", output_path,
            "--max-results", str(max_results),
        ]
        _, stdout, _ = await self._run_script(
            IMAGE_SEARCH_SCRIPT,
            args,
            timeout=TIMEOUT_IMAGE_SEARCH,
        )
        # Try to parse JSON results if the script outputs them
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw_output": stdout, "output_path": output_path}

    async def run_analyze_images(self, project_path: str) -> dict[str, Any]:
        """
        Analyze images in a project for quality and compatibility.

        Returns:
            Analysis results dict.
        """
        _, stdout, _ = await self._run_script(
            ANALYZE_IMAGES_SCRIPT,
            [project_path],
            timeout=TIMEOUT_ANALYZE_IMAGES,
        )
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw_output": stdout}

    # ------------------------------------------------------------------
    # SVG quality & post-processing
    # ------------------------------------------------------------------

    async def run_svg_quality_check(
        self,
        project_path: str,
    ) -> dict[str, Any]:
        """
        Run SVG quality checks on all SVG files in a project.

        Args:
            project_path: Path to the project directory.

        Returns:
            Dict mapping SVG filenames to their quality check results.
        """
        _, stdout, _ = await self._run_script(
            SVG_QUALITY_CHECKER_SCRIPT,
            [project_path],
            timeout=TIMEOUT_SVG_QUALITY_CHECK,
        )
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            # Fallback: try to parse line-by-line
            results: dict[str, Any] = {}
            for line in stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if isinstance(entry, dict):
                        results.update(entry)
                except json.JSONDecodeError:
                    continue
            return results if results else {"raw_output": stdout}

    async def run_finalize_svg(self, project_path: str) -> None:
        """
        Run SVG post-processing (finalization) on a project.

        Args:
            project_path: Path to the project directory.
        """
        await self._run_script(
            FINALIZE_SVG_SCRIPT,
            [project_path],
            timeout=TIMEOUT_FINALIZE_SVG,
        )

    async def run_svg_to_pptx(
        self,
        project_path: str,
        options: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        Export SVG slides to PPTX format.

        Args:
            project_path: Path to the project directory.
            options: Export options dict (e.g., {"transition": "fade", "animation": "appear"}).

        Returns:
            List of exported PPTX file paths.
        """
        args = [project_path]
        if options:
            for key, value in options.items():
                args.extend([f"--{key}", str(value)])

        _, stdout, _ = await self._run_script(
            SVG_TO_PPTX_SCRIPT,
            args,
            timeout=TIMEOUT_SVG_TO_PPTX,
        )
        # Parse output paths (one per line)
        paths = [p.strip() for p in stdout.splitlines() if p.strip().endswith(".pptx")]
        return paths

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    async def run_total_md_split(self, project_path: str) -> None:
        """
        Split total.md into per-page markdown files.

        Args:
            project_path: Path to the project directory.
        """
        await self._run_script(
            TOTAL_MD_SPLIT_SCRIPT,
            [project_path],
            timeout=TIMEOUT_TOTAL_MD_SPLIT,
        )

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    async def convert_source_to_md(
        self,
        file_path: str,
        file_type: str,
    ) -> str:
        """
        Convert a source file to Markdown based on its type.

        Args:
            file_path: Absolute path to the source file.
            file_type: File type extension (pdf / docx / xlsx / pptx / url / md / txt).

        Returns:
            Markdown content string.

        Raises:
            ScriptRunnerError: If conversion fails or type is unsupported.
        """
        converters = {
            "pdf": self.run_pdf_to_md,
            "docx": self.run_doc_to_md,
            "doc": self.run_doc_to_md,
            "xlsx": self.run_excel_to_md,
            "xls": self.run_excel_to_md,
            "pptx": self.run_ppt_to_md,
            "ppt": self.run_ppt_to_md,
            "url": self.run_web_to_md,
        }

        # Handle plain text / markdown directly
        if file_type in ("md", "txt", "html", "htm", "epub"):
            if file_type == "md":
                return Path(file_path).read_text(encoding="utf-8")
            elif file_type in ("txt", "html", "htm"):
                # Return as-is (wrapped in markdown)
                content = Path(file_path).read_text(encoding="utf-8")
                return f"\n```\n{content}\n```\n"
            else:
                # epub fallback - try doc_to_md
                return await self.run_doc_to_md(file_path)

        converter = converters.get(file_type.lower())
        if not converter:
            raise ScriptRunnerError(f"Unsupported source file type: {file_type}")

        return await converter(file_path)
