#!/usr/bin/env python3
"""
RFP Parser for GrantOps.

Parses an RFP/guidelines document and generates the section structure
with metadata, requirements, and outline templates.

Usage:
    python scripts/parse.py <source_file>
"""

import argparse
import json
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import yaml

from core.context import build_parse_context, get_repo_root
from core.llm import call_llm
from core.git_ops import commit_changes


def list_source_files() -> list[str]:
    """List available source files in application/source/."""
    source_dir = get_repo_root() / "application" / "source"
    if not source_dir.exists():
        return []

    return [
        f.name for f in source_dir.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ]


def parse_rfp(source_file: str) -> list[dict]:
    """
    Parse an RFP document and extract section structure.

    Args:
        source_file: Filename in application/source/

    Returns:
        List of section dictionaries
    """
    # Build context
    context = build_parse_context(source_file)

    # Extract system prompt
    parts = context.split("\n\n---\n\n")
    system_prompt = parts[0] if parts else ""
    user_prompt = "\n\n---\n\n".join(parts[1:]) if len(parts) > 1 else context

    # Add explicit instruction
    user_prompt += "\n\n---\n\nParse this RFP and return the JSON array of sections as specified."

    # Call the LLM
    response = call_llm(
        agent_name="parser",
        prompt=user_prompt,
        system_prompt=system_prompt,
    )

    # Extract JSON from response
    # Handle case where LLM wraps in markdown code block
    response = response.strip()
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]

    return json.loads(response.strip())


def generate_outline(section: dict) -> str:
    """
    Generate a structure template/outline for a section.

    Args:
        section: Section dictionary from parser

    Returns:
        Markdown outline template
    """
    lines = [f"# {section.get('title', 'Section Title')}", ""]

    # Add placeholders based on requirements
    requirements = section.get("requirements", [])
    if requirements:
        lines.append("## Overview")
        lines.append("")
        lines.append("[Introduce the section topic]")
        lines.append("")

        for i, req in enumerate(requirements, 1):
            # Create a heading for each requirement
            lines.append(f"## {req[:50]}{'...' if len(req) > 50 else ''}")
            lines.append("")
            lines.append(f"[Address: {req}]")
            lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append("[Conclude the section]")
    else:
        lines.append("[Draft content here]")

    return "\n".join(lines)


def create_section_directory(section: dict) -> Path:
    """
    Create a section directory with meta.yaml and outline.md.

    Args:
        section: Section dictionary from parser

    Returns:
        Path to created directory
    """
    section_id = section.get("id", "unknown_section")
    section_dir = get_repo_root() / "application" / "sections" / section_id

    # Create directory
    section_dir.mkdir(parents=True, exist_ok=True)

    # Create meta.yaml
    meta = {
        "title": section.get("title", ""),
        "source_reference": section.get("source_reference", ""),
        "word_limit": section.get("word_limit"),
        "scoring_weight": section.get("scoring_weight"),
        "requirements": section.get("requirements", []),
        "evaluation_criteria": section.get("evaluation_criteria", []),
    }
    # Remove None values
    meta = {k: v for k, v in meta.items() if v is not None}

    meta_path = section_dir / "meta.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    # Create outline.md
    outline = generate_outline(section)
    outline_path = section_dir / "outline.md"
    outline_path.write_text(outline)

    return section_dir


def main():
    parser = argparse.ArgumentParser(
        description="Parse an RFP document and generate section structure"
    )
    parser.add_argument(
        "source_file",
        nargs="?",
        help="Source file in application/source/ (e.g., 'rfp.md')"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available source files and exit"
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Don't create a git commit (for local testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display results without creating files"
    )

    args = parser.parse_args()

    # List source files mode
    if args.list:
        files = list_source_files()
        if files:
            print("Available source files:")
            for f in files:
                print(f"  - {f}")
        else:
            print("No source files found in application/source/")
            print("Add your RFP document there (as .md or .txt) and run again.")
        return 0

    # Require source file if not listing
    if not args.source_file:
        print("Error: source_file is required")
        print("Run with --list to see available files")
        return 1

    # Check source file exists
    source_path = get_repo_root() / "application" / "source" / args.source_file
    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}")
        return 1

    print(f"Parsing RFP: {args.source_file}")

    # Parse the RFP
    try:
        sections = parse_rfp(args.source_file)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse LLM response as JSON: {e}")
        return 1
    except Exception as e:
        print(f"Error during parsing: {e}")
        return 1

    print(f"Found {len(sections)} sections")

    # Dry run - just display
    if args.dry_run:
        print("\nParsed sections:")
        for section in sections:
            print(f"\n  {section.get('id')}:")
            print(f"    Title: {section.get('title')}")
            print(f"    Word limit: {section.get('word_limit')}")
            print(f"    Requirements: {len(section.get('requirements', []))}")
        return 0

    # Create section directories
    created_dirs = []
    for section in sections:
        section_dir = create_section_directory(section)
        created_dirs.append(section_dir)
        print(f"  Created: {section_dir.relative_to(get_repo_root())}")

    # Git commit (unless --no-commit)
    if not args.no_commit and created_dirs:
        files_to_commit = []
        for section_dir in created_dirs:
            rel_dir = section_dir.relative_to(get_repo_root())
            files_to_commit.append(str(rel_dir / "meta.yaml"))
            files_to_commit.append(str(rel_dir / "outline.md"))

        commit_sha = commit_changes(
            files=files_to_commit,
            message=f"Parse RFP: {args.source_file}\n\nGenerated {len(sections)} section(s)."
        )
        print(f"\nCommitted: {commit_sha[:8]}")

    print("\nNext steps:")
    print("1. Review and edit the outline.md files to customize structure")
    print("2. Run the Draft workflow to generate content")

    return 0


if __name__ == "__main__":
    sys.exit(main())
