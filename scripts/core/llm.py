"""
LLM abstraction layer for GrantOps.

Provides a unified interface for calling different LLM providers
based on the configuration in config/agents.yaml.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
import litellm


def get_repo_root() -> Path:
    """Get the repository root directory."""
    current = Path(__file__).resolve()
    # Navigate up from scripts/core/llm.py to repo root
    return current.parent.parent.parent


def load_agents_config() -> dict:
    """Load the agents configuration from config/agents.yaml."""
    config_path = get_repo_root() / "config" / "agents.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_agent_config(agent_name: str) -> dict:
    """
    Get configuration for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., 'drafter', 'evaluator', 'parser')

    Returns:
        Dictionary with model, temperature, max_tokens, system_prompt, etc.
    """
    config = load_agents_config()
    defaults = config.get("defaults", {})

    if agent_name not in config.get("agents", {}):
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(config['agents'].keys())}")

    agent_config = config["agents"][agent_name]

    # Merge defaults with agent-specific config
    result = {
        "model": agent_config["model"],
        "temperature": agent_config.get("temperature", 0.7),
        "max_tokens": agent_config.get("max_tokens", defaults.get("max_tokens", 4096)),
    }

    # Add system_prompt if specified in config
    if "system_prompt" in agent_config:
        result["system_prompt"] = agent_config["system_prompt"]

    # Add description if available
    if "description" in agent_config:
        result["description"] = agent_config["description"]

    return result


def load_system_prompt(prompt_spec: str) -> str:
    """
    Load a system prompt from various sources.

    Args:
        prompt_spec: Either inline text or a file reference like "file:path/to/prompt.md"

    Returns:
        The system prompt text
    """
    if prompt_spec.startswith("file:"):
        # Load from file
        file_path = prompt_spec[5:]  # Remove "file:" prefix
        prompt_path = get_repo_root() / file_path
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt file not found: {file_path}")
        return prompt_path.read_text()
    else:
        # Inline prompt
        return prompt_spec


def call_llm(
    agent_name: str,
    prompt: str,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Call an LLM using the configuration for the specified agent.

    Args:
        agent_name: Name of the agent from config/agents.yaml
        prompt: The user prompt to send
        system_prompt: Optional system prompt (overrides agent config and defaults)

    Returns:
        The LLM's response text
    """
    config = get_agent_config(agent_name)

    # Determine system prompt priority:
    # 1. Explicit parameter (highest priority)
    # 2. Agent config system_prompt
    # 3. None (no system prompt)
    final_system_prompt = system_prompt
    if final_system_prompt is None and "system_prompt" in config:
        final_system_prompt = load_system_prompt(config["system_prompt"])

    messages = []
    if final_system_prompt:
        messages.append({"role": "system", "content": final_system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = litellm.completion(
        model=config["model"],
        messages=messages,
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    return response.choices[0].message.content


def list_agents() -> dict:
    """
    List all available agents and their descriptions.

    Returns:
        Dictionary mapping agent names to their configurations
    """
    config = load_agents_config()
    return config.get("agents", {})


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Estimate token count for a text string.

    Args:
        text: The text to count tokens for
        model: Model to use for tokenization estimation

    Returns:
        Estimated token count
    """
    # Use litellm's token counting
    return litellm.token_counter(model=model, text=text)
