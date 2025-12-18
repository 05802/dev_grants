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
        Dictionary with model, temperature, max_tokens, etc.
    """
    config = load_agents_config()
    defaults = config.get("defaults", {})

    if agent_name not in config.get("agents", {}):
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(config['agents'].keys())}")

    agent_config = config["agents"][agent_name]

    # Merge defaults with agent-specific config
    return {
        "model": agent_config["model"],
        "temperature": agent_config.get("temperature", 0.7),
        "max_tokens": agent_config.get("max_tokens", defaults.get("max_tokens", 4096)),
    }


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
        system_prompt: Optional system prompt (overrides default)

    Returns:
        The LLM's response text
    """
    config = get_agent_config(agent_name)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = litellm.completion(
        model=config["model"],
        messages=messages,
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
    )

    return response.choices[0].message.content


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
