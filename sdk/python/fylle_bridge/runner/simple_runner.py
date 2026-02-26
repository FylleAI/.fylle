"""Simple runner for executing .fylle agents via LLM APIs.

Supports Anthropic (Claude) and OpenAI (GPT) providers.
Auto-detects the provider from the agent's model.preferred field.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from fylle_format.schema import FylleAgent


def run_fylle_agent(
    agent: FylleAgent,
    user_input: dict[str, str],
    provider: str = "auto",
    api_key: str | None = None,
    stream: bool = False,
) -> str:
    """Execute a FylleAgent with the given inputs.

    Args:
        agent: A parsed FylleAgent.
        user_input: Dict mapping input names to values.
                    Keys should match agent.manifest.agent.inputs[].name.
        provider: Which API to use. "anthropic", "openai", or "auto".
                  "auto" picks based on model.preferred.
        api_key: API key. If None, reads from env vars.
        stream: If True, prints tokens as they arrive.

    Returns:
        The agent's response as a string.

    Raises:
        ValueError: If required inputs are missing or provider unavailable.
    """
    identity = agent.manifest.agent

    # Validate required inputs
    for inp in identity.inputs:
        if inp.required and inp.name not in user_input:
            raise ValueError(
                f"Missing required input: '{inp.name}' — {inp.description}"
            )

    # Build system prompt
    system_prompt = agent.personality

    # Build user message from inputs
    parts: list[str] = []
    for inp in identity.inputs:
        value = user_input.get(inp.name)
        if value:
            if inp.description:
                parts.append(f"## {inp.description}\n{value}")
            else:
                parts.append(f"## {inp.name}\n{value}")
    user_message = "\n\n".join(parts) if parts else next(iter(user_input.values()), "")

    # Determine provider
    if provider == "auto":
        model = identity.model.preferred.lower()
        if "claude" in model or "anthropic" in model:
            provider = "anthropic"
        else:
            provider = "openai"

    # Get settings
    temperature = identity.model.settings.temperature
    max_tokens = identity.model.settings.max_tokens

    if provider == "anthropic":
        return _run_anthropic(
            model=identity.model.preferred,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            stream=stream,
        )
    elif provider == "openai":
        return _run_openai(
            model=identity.model.preferred,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            stream=stream,
        )
    else:
        raise ValueError(f"Unknown provider: '{provider}'. Use 'anthropic', 'openai', or 'auto'.")


def _run_anthropic(
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float,
    max_tokens: int,
    api_key: str | None,
    stream: bool,
) -> str:
    """Execute via Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        raise ValueError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("No Anthropic API key. Set ANTHROPIC_API_KEY or pass api_key.")

    client = anthropic.Anthropic(api_key=key)

    if stream:
        result_parts: list[str] = []
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
        ) as response:
            for text in response.text_stream:
                sys.stdout.write(text)
                sys.stdout.flush()
                result_parts.append(text)
        sys.stdout.write("\n")
        return "".join(result_parts)
    else:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
        )
        return response.content[0].text


def _run_openai(
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float,
    max_tokens: int,
    api_key: str | None,
    stream: bool,
) -> str:
    """Execute via OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ValueError(
            "openai package not installed. Run: pip install openai"
        )

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("No OpenAI API key. Set OPENAI_API_KEY or pass api_key.")

    client = OpenAI(api_key=key)

    # Map Claude model names to OpenAI if needed
    from fylle_bridge.adapters.openai_adapter import _CLAUDE_TO_OPENAI
    openai_model = _CLAUDE_TO_OPENAI.get(model, model)

    if stream:
        result_parts: list[str] = []
        response = client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                sys.stdout.write(delta.content)
                sys.stdout.flush()
                result_parts.append(delta.content)
        sys.stdout.write("\n")
        return "".join(result_parts)
    else:
        response = client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
