"""
Context assembly utilities for GrantOps.

Handles loading and combining context files for different operations.
"""

from pathlib import Path
from typing import Optional

import yaml


def get_repo_root() -> Path:
    """Get the repository root directory."""
    current = Path(__file__).resolve()
    return current.parent.parent.parent


def read_file(relative_path: str) -> str:
    """
    Read a file from the repository.

    Args:
        relative_path: Path relative to repo root

    Returns:
        File contents as string, or empty string if file doesn't exist
    """
    file_path = get_repo_root() / relative_path
    if not file_path.exists():
        return ""
    return file_path.read_text()


def read_yaml(relative_path: str) -> dict:
    """
    Read and parse a YAML file from the repository.

    Args:
        relative_path: Path relative to repo root

    Returns:
        Parsed YAML as dictionary
    """
    content = read_file(relative_path)
    if not content:
        return {}
    return yaml.safe_load(content)


def format_yaml_as_context(data: dict, title: str = "Metadata") -> str:
    """Format a dictionary as readable context for the LLM."""
    lines = [f"## {title}", ""]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"**{key}:**")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"  - {item}")
                else:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"**{key}:** {value}")
    return "\n".join(lines)


def build_draft_context(section_id: str) -> str:
    """
    Build the context for drafting a section.

    Assembles:
    - System prompt for drafter
    - Project logic
    - Style guide
    - Section metadata
    - Section outline

    Args:
        section_id: The section identifier (e.g., 'project_narrative')

    Returns:
        Combined context string
    """
    parts = []

    # System prompt
    system_prompt = read_file("config/prompts/drafter.md")
    if system_prompt:
        parts.append(system_prompt)

    # Project context
    project = read_file("context/project.md")
    if project:
        parts.append(f"# Project Context\n\n{project}")

    # Style guide
    style = read_file("context/style.md")
    if style:
        parts.append(f"# Style Guide\n\n{style}")

    # Section metadata
    meta = read_yaml(f"application/sections/{section_id}/meta.yaml")
    if meta:
        parts.append(format_yaml_as_context(meta, "Section Requirements"))

    # Section outline
    outline = read_file(f"application/sections/{section_id}/outline.md")
    if outline:
        parts.append(f"# Structure Template\n\nFollow this structure:\n\n{outline}")

    return "\n\n---\n\n".join(parts)


def build_evaluate_context(section_id: str, mode: str) -> str:
    """
    Build the context for evaluating a section.

    Modes:
    - 'style': Focus on writing quality and style guide adherence
    - 'logic': Focus on requirements coverage and internal logic
    - 'alignment': Focus on project consistency and narrative coherence

    Args:
        section_id: The section identifier
        mode: Evaluation mode ('style', 'logic', or 'alignment')

    Returns:
        Combined context string
    """
    parts = []

    # Mode-specific system prompt
    prompt_file = f"config/prompts/evaluator_{mode}.md"
    system_prompt = read_file(prompt_file)
    if system_prompt:
        parts.append(system_prompt)

    # The draft to evaluate
    draft = read_file(f"application/sections/{section_id}/draft.md")
    if draft:
        parts.append(f"# Draft to Evaluate\n\n{draft}")
    else:
        raise ValueError(f"No draft found for section: {section_id}")

    # Mode-specific context
    if mode == "style":
        style = read_file("context/style.md")
        if style:
            parts.append(f"# Style Guide\n\n{style}")

    elif mode == "logic":
        meta = read_yaml(f"application/sections/{section_id}/meta.yaml")
        if meta:
            parts.append(format_yaml_as_context(meta, "Section Requirements"))

    elif mode == "alignment":
        project = read_file("context/project.md")
        if project:
            parts.append(f"# Project Context\n\n{project}")

        # Include other sections for cross-reference
        other_sections = get_all_drafts(exclude=section_id)
        if other_sections:
            parts.append(f"# Other Sections (for reference)\n\n{other_sections}")

    return "\n\n---\n\n".join(parts)


def build_parse_context(source_file: str) -> str:
    """
    Build the context for parsing an RFP document.

    Args:
        source_file: Filename in application/source/

    Returns:
        Combined context string
    """
    parts = []

    # System prompt
    system_prompt = read_file("config/prompts/parser.md")
    if system_prompt:
        parts.append(system_prompt)

    # Source document
    source = read_file(f"application/source/{source_file}")
    if source:
        parts.append(f"# RFP Document\n\n{source}")
    else:
        raise ValueError(f"Source file not found: {source_file}")

    return "\n\n---\n\n".join(parts)


def get_all_drafts(exclude: Optional[str] = None) -> str:
    """
    Get all draft content for cross-reference.

    Args:
        exclude: Section ID to exclude from results

    Returns:
        Combined string of all drafts with section headers
    """
    sections_dir = get_repo_root() / "application" / "sections"
    if not sections_dir.exists():
        return ""

    parts = []
    for section_dir in sorted(sections_dir.iterdir()):
        if not section_dir.is_dir():
            continue
        if section_dir.name == exclude:
            continue
        if section_dir.name.startswith("."):
            continue

        draft_file = section_dir / "draft.md"
        if draft_file.exists():
            content = draft_file.read_text()
            parts.append(f"## {section_dir.name}\n\n{content}")

    return "\n\n".join(parts)


def list_sections() -> list[str]:
    """
    List all available section IDs.

    Returns:
        List of section directory names
    """
    sections_dir = get_repo_root() / "application" / "sections"
    if not sections_dir.exists():
        return []

    return [
        d.name for d in sorted(sections_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    ]
