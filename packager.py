"""
packager.py — Collects all agent output files into a timestamped ZIP archive.
"""
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List


def build_zip(
    workspace: Path,
    project_name: str,
    output_dir: Path,
    agent_states: list,
) -> Path:
    """
    Walk the workspace directory and zip everything into:
        output_dir/<project_slug>_<timestamp>.zip

    Returns the path to the created ZIP.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    slug      = _slugify(project_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path  = output_dir / f"{slug}_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add all workspace files
        for file_path in sorted(workspace.rglob("*")):
            if file_path.is_file():
                arcname = str(file_path.relative_to(workspace))
                zf.write(file_path, arcname)

        # Add a manifest
        manifest = _build_manifest(workspace, agent_states, project_name, timestamp)
        zf.writestr("MANIFEST.md", manifest)

    return zip_path


def _slugify(name: str) -> str:
    import re
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_-]+", "_", name)
    return name[:40]


def _build_manifest(
    workspace: Path,
    agent_states: list,
    project_name: str,
    timestamp: str,
) -> str:
    lines = [
        f"# Proto-Agent Manifest",
        f"",
        f"**Project:** {project_name}",
        f"**Generated:** {timestamp}",
        f"",
        f"## Agent Summary",
        f"",
        f"| Agent | Status | Files | Tokens | Duration |",
        f"|-------|--------|-------|--------|----------|",
    ]
    for s in agent_states:
        lines.append(
            f"| {s.icon} {s.name} | {s.status.value} | "
            f"{len(s.output_files)} | {s.tokens_out:,} | {s.elapsed} |"
        )

    lines += [
        f"",
        f"## Files Included",
        f"",
    ]
    for fp in sorted(workspace.rglob("*")):
        if fp.is_file():
            size = fp.stat().st_size
            lines.append(f"- `{fp.relative_to(workspace)}` ({_human_size(size)})")

    return "\n".join(lines)


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
