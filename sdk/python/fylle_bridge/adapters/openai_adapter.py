"""OpenAI Assistants API <-> .fylle adapter.

Translates between OpenAI's Assistant JSON config and .fylle FylleAgent objects.

OpenAI Assistants use this JSON structure:
    {
      "model": "gpt-4o",
      "name": "Assistant Name",
      "description": "What it does",
      "instructions": "System prompt...",
      "tools": [{"type": "code_interpreter"}, {"type": "function", ...}],
      "temperature": 0.7,
      "top_p": 1.0,
      "metadata": {}
    }
"""

from __future__ import annotations

import json
from typing import Any

from fylle_format.schema import (
    AgentAuthor,
    AgentIdentity,
    AgentInput,
    AgentOutput,
    FylleAgent,
    FylleManifest,
    GuardrailLimits,
    GuardrailsRef,
    MaxAutonomy,
    ModelCapability,
    ModelRequirements,
    ModelSettings,
    OutputFormat,
    ToolDeclaration,
    ToolProtocol,
    ToolsConfig,
)

from fylle_bridge.adapters.base import FrameworkAdapter

# Model mapping: .fylle model IDs <-> OpenAI model IDs
_CLAUDE_TO_OPENAI: dict[str, str] = {
    "claude-opus-4-5": "gpt-4o",
    "claude-sonnet-4-5": "gpt-4o",
    "claude-haiku-3-5": "gpt-4o-mini",
    "claude-sonnet-4-20250514": "gpt-4o",
    "claude-opus-4-20250514": "gpt-4o",
}

_OPENAI_TO_CLAUDE: dict[str, str] = {
    "gpt-4o": "claude-sonnet-4-5",
    "gpt-4o-mini": "claude-haiku-3-5",
    "gpt-4-turbo": "claude-sonnet-4-5",
    "gpt-4": "claude-sonnet-4-5",
    "gpt-3.5-turbo": "claude-haiku-3-5",
    "o1": "claude-opus-4-5",
    "o1-mini": "claude-sonnet-4-5",
    "o3-mini": "claude-sonnet-4-5",
}


class OpenAIAdapter(FrameworkAdapter):
    """Adapter for translating between OpenAI Assistants API and .fylle format."""

    @property
    def framework_name(self) -> str:
        return "OpenAI Assistants"

    def to_fylle(self, source: dict, **kwargs: Any) -> FylleAgent:
        return openai_to_fylle(source, **kwargs)

    def from_fylle(self, agent: FylleAgent) -> dict:
        return fylle_to_openai(agent)


def openai_to_fylle(
    assistant_config: dict | str,
    author_name: str = "Unknown",
    author_url: str | None = None,
    version: str = "1.0.0",
    license_id: str = "MIT",
) -> FylleAgent:
    """Convert an OpenAI Assistant config (JSON dict) to a FylleAgent.

    Args:
        assistant_config: Dict matching the Assistants API response format,
                          or a JSON string to be parsed.
        author_name: Author name for the .fylle manifest.
        author_url: Author URL.
        version: Version string for the .fylle manifest.
        license_id: SPDX license identifier.

    Returns:
        A validated FylleAgent.
    """
    if isinstance(assistant_config, str):
        assistant_config = json.loads(assistant_config)

    name = assistant_config.get("name", "Unnamed Assistant")
    description = assistant_config.get("description", "")
    instructions = assistant_config.get("instructions", "")
    model = assistant_config.get("model", "gpt-4o")
    temperature = assistant_config.get("temperature", 0.7)
    tools_raw = assistant_config.get("tools", [])

    # Map model to .fylle preferred (keep original, store mapping)
    fylle_model = _OPENAI_TO_CLAUDE.get(model, model)

    # Parse tools
    tool_declarations: list[ToolDeclaration] = []
    capabilities: list[ModelCapability] = []

    for tool in tools_raw:
        tool_type = tool.get("type", "")
        if tool_type == "code_interpreter":
            capabilities.append(ModelCapability.CODE_EXECUTION)
        elif tool_type == "file_search":
            tool_declarations.append(
                ToolDeclaration(
                    name="file_search",
                    protocol=ToolProtocol.FUNCTION,
                    description="Search through uploaded files",
                )
            )
        elif tool_type == "function":
            func = tool.get("function", {})
            tool_declarations.append(
                ToolDeclaration(
                    name=func.get("name", "unknown"),
                    protocol=ToolProtocol.FUNCTION,
                    description=func.get("description", ""),
                )
            )

    # Collect OpenAI-specific fields into extensions
    openai_extensions: dict[str, Any] = {"original_model": model}
    if assistant_config.get("top_p") is not None:
        openai_extensions["top_p"] = assistant_config["top_p"]
    if assistant_config.get("metadata"):
        openai_extensions["metadata"] = assistant_config["metadata"]
    if assistant_config.get("response_format"):
        openai_extensions["response_format"] = assistant_config["response_format"]

    # Determine output format from response_format
    output_format = OutputFormat.MARKDOWN
    resp_fmt = assistant_config.get("response_format")
    if resp_fmt:
        if isinstance(resp_fmt, dict) and resp_fmt.get("type") == "json_object":
            output_format = OutputFormat.JSON
        elif resp_fmt == "json_object":
            output_format = OutputFormat.JSON

    if not description:
        description = instructions[:500] if instructions else f"OpenAI Assistant: {name}"

    manifest = FylleManifest(
        fylle_format="0.1.0",
        agent=AgentIdentity(
            name=name,
            version=version,
            description=description[:500],
            author=AgentAuthor(name=author_name, url=author_url),
            license=license_id,
            model=ModelRequirements(
                preferred=fylle_model,
                minimum_capability=capabilities,
                settings=ModelSettings(
                    temperature=temperature,
                    max_tokens=assistant_config.get("max_tokens", 4000) or 4000,
                ),
            ),
            prompt_file="agent.md",
            language=["en"],
            inputs=[
                AgentInput(
                    name="message",
                    type="text",
                    required=True,
                    description="The user message or task for the assistant",
                ),
            ],
            output=AgentOutput(format=output_format),
            tools=ToolsConfig(required=tool_declarations) if tool_declarations else ToolsConfig(),
            guardrails=GuardrailsRef(
                max_autonomy=MaxAutonomy.DRAFT_ONLY,
                limits=GuardrailLimits(max_tokens_per_response=4000),
            ),
            extensions={"openai": openai_extensions},
        ),
    )

    return FylleAgent(
        manifest=manifest,
        personality=instructions if instructions else f"You are {name}.",
    )


def fylle_to_openai(agent: FylleAgent) -> dict:
    """Convert a FylleAgent to OpenAI Assistant creation params.

    Returns a dict that can be passed directly to:
        client.beta.assistants.create(**result)

    Note: Function tool parameter schemas are not preserved in .fylle
    (only names and descriptions). The user must provide schemas
    when creating the actual assistant.
    """
    identity = agent.manifest.agent

    # Map model to OpenAI
    preferred = identity.model.preferred
    openai_model = _CLAUDE_TO_OPENAI.get(preferred, preferred)

    # If there's an original OpenAI model in extensions, prefer it
    openai_ext = identity.extensions.get("openai", {})
    if "original_model" in openai_ext:
        openai_model = openai_ext["original_model"]

    # Build tools array
    tools: list[dict[str, Any]] = []

    # Add code_interpreter if capability is declared
    if ModelCapability.CODE_EXECUTION in identity.model.minimum_capability:
        tools.append({"type": "code_interpreter"})

    # Add function tools
    for tool_decl in identity.tools.required:
        if tool_decl.name == "file_search":
            tools.append({"type": "file_search"})
        else:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_decl.name,
                    "description": tool_decl.description or f"Tool: {tool_decl.name}",
                },
            })

    for tool_decl in identity.tools.optional:
        if tool_decl.name == "file_search":
            tools.append({"type": "file_search"})
        else:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_decl.name,
                    "description": tool_decl.description or f"Tool: {tool_decl.name}",
                },
            })

    # Build the OpenAI config
    result: dict[str, Any] = {
        "model": openai_model,
        "name": identity.name,
        "instructions": agent.personality,
    }

    if identity.description:
        result["description"] = identity.description

    if tools:
        result["tools"] = tools

    result["temperature"] = identity.model.settings.temperature

    # Restore OpenAI-specific extensions
    if "top_p" in openai_ext:
        result["top_p"] = openai_ext["top_p"]
    if "metadata" in openai_ext:
        result["metadata"] = openai_ext["metadata"]
    if "response_format" in openai_ext:
        result["response_format"] = openai_ext["response_format"]

    return result


def fylle_to_openai_json(agent: FylleAgent, indent: int = 2) -> str:
    """Convenience: convert FylleAgent to a formatted JSON string."""
    return json.dumps(fylle_to_openai(agent), indent=indent, ensure_ascii=False)
