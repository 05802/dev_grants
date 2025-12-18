#!/usr/bin/env python3
"""
Draft Generator for GrantOps.

Generates a draft for a specified section based on the outline
and project context.

Usage:
    python scripts/draft.py <section_id> [--branch <branch_name>]
"""

import argparse
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.context import build_draft_context, read_file, list_sections, get_repo_root
from core.llm import call_llm, list_agents, get_agent_config
from core.git_ops import create_branch, commit_changes, get_next_version, generate_branch_name


def validate_section(section_id: str) -> bool:
    """Check if a section exists and has the required files."""
    section_dir = get_repo_root() / "application" / "sections" / section_id

    if not section_dir.exists():
        return False

    # Must have at least meta.yaml or outline.md
    has_meta = (section_dir / "meta.yaml").exists()
    has_outline = (section_dir / "outline.md").exists()

    return has_meta or has_outline


def generate_draft(section_id: str, agent_name: str = "drafter") -> str:
    """
    Generate a draft for the specified section.

    Args:
        section_id: The section to draft
        agent_name: The agent to use for drafting (default: "drafter")

    Returns:
        Generated draft content
    """
    # Build the context
    context = build_draft_context(section_id)

    # Check if agent has system_prompt in config
    agent_config = get_agent_config(agent_name)
    has_agent_prompt = "system_prompt" in agent_config

    if has_agent_prompt:
        # Agent has its own system prompt, use entire context as user prompt
        user_prompt = context
        system_prompt = None  # Let call_llm use the agent's configured prompt
    else:
        # Fallback: Extract system prompt from context (legacy behavior)
        parts = context.split("\n\n---\n\n")
        system_prompt = parts[0] if parts else ""
        user_prompt = "\n\n---\n\n".join(parts[1:]) if len(parts) > 1 else context

    # Add explicit instruction to user prompt
    user_prompt += "\n\n---\n\nPlease draft this section now, following the structure template exactly."

    # Call the LLM
    draft = call_llm(
        agent_name=agent_name,
        prompt=user_prompt,
        system_prompt=system_prompt,
    )

    return draft


def save_draft(section_id: str, content: str) -> Path:
    """
    Save the draft to the section directory.

    Args:
        section_id: The section identifier
        content: Draft content to save

    Returns:
        Path to the saved file
    """
    draft_path = get_repo_root() / "application" / "sections" / section_id / "draft.md"
    draft_path.write_text(content)
    return draft_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate a draft for a grant application section"
    )
    parser.add_argument(
        "section_id",
        nargs="?",
        help="Section identifier (e.g., 'project_narrative')"
    )
    parser.add_argument(
        "--agent",
        default="drafter",
        help="Agent to use for drafting (default: drafter)"
    )
    parser.add_argument(
        "--branch",
        help="Branch name for the draft (auto-generated if not specified)"
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Don't create a git commit (for local testing)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available sections and exit"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agents and exit"
    )

    args = parser.parse_args()

    # List agents mode
    if args.list_agents:
        agents = list_agents()
        if agents:
            print("Available agents:")
            for name, config in agents.items():
                desc = config.get("description", "No description")
                model = config.get("model", "unknown")
                temp = config.get("temperature", "N/A")
                print(f"  {name}")
                print(f"    Model: {model}")
                print(f"    Temperature: {temp}")
                print(f"    Description: {desc}")
                print()
        else:
            print("No agents configured.")
        return 0

    # List sections mode
    if args.list:
        sections = list_sections()
        if sections:
            print("Available sections:")
            for s in sections:
                print(f"  - {s}")
        else:
            print("No sections found. Run the parse workflow first, or create sections manually.")
        return 0

    # Require section_id for drafting
    if not args.section_id:
        parser.print_help()
        return 1

    # Validate section exists
    if not validate_section(args.section_id):
        print(f"Error: Section '{args.section_id}' not found or missing required files.")
        print(f"Expected directory: application/sections/{args.section_id}/")
        print("Run with --list to see available sections.")
        return 1

    print(f"Generating draft for section: {args.section_id}")
    print(f"Using agent: {args.agent}")

    # Generate the draft
    try:
        draft = generate_draft(args.section_id, agent_name=args.agent)
    except Exception as e:
        print(f"Error generating draft: {e}")
        return 1

    # Save the draft
    draft_path = save_draft(args.section_id, draft)
    print(f"Draft saved to: {draft_path}")

    # Git operations (unless --no-commit)
    if not args.no_commit:
        # Determine branch name
        if args.branch:
            branch_name = args.branch
        else:
            version = get_next_version("draft", args.section_id)
            branch_name = generate_branch_name("draft", args.section_id, version)

        # Create branch and commit
        created = create_branch(branch_name, checkout=True)
        status = "Created" if created else "Checked out"
        print(f"{status} branch: {branch_name}")

        relative_path = f"application/sections/{args.section_id}/draft.md"
        commit_sha = commit_changes(
            files=[relative_path],
            message=f"Draft {args.section_id} (auto-generated)\n\nGenerated by GrantOps draft workflow."
        )
        print(f"Committed: {commit_sha[:8]}")

        # Output for GitHub Actions
        print(f"\n::set-output name=branch::{branch_name}")
        print(f"::set-output name=draft_path::{relative_path}")

    # Print word count
    word_count = len(draft.split())
    print(f"\nWord count: {word_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
