"""CrewAI <-> .fylle adapter.

Translates between CrewAI's YAML agent definitions and .fylle FylleAgent objects.

CrewAI agents are typically defined in agents.yaml with this structure:
    agent_key:
      role: "Agent's role"
      goal: "Agent's goal"
      backstory: "System prompt / personality"
      tools: [tool_name_1, tool_name_2]
      llm: model-id
      max_iter: 25
      verbose: true
      allow_delegation: false
"""

from __future__ import annotations

from typing import Any

import yaml

from fylle.schema import (
    AgentAuthor,
    AgentIdentity,
    AgentInput,
    AgentOutput,
    FylleAgent,
    FylleManifest,
    GuardrailLimits,
    GuardrailsRef,
    MaxAutonomy,
    ModelRequirements,
    ModelSettings,
    OutputFormat,
    ToolDeclaration,
    ToolProtocol,
    ToolsConfig,
)

from fylle_bridge.adapters.base import FrameworkAdapter


class CrewAIAdapter(FrameworkAdapter):
    """Adapter for translating between CrewAI YAML and .fylle format."""

    @property
    def framework_name(self) -> str:
        return "CrewAI"

    def to_fylle(self, source: dict, **kwargs: Any) -> FylleAgent:
        return crewai_to_fylle(source, **kwargs)

    def from_fylle(self, agent: FylleAgent) -> dict:
        return fylle_to_crewai(agent)


# Known CrewAI fields that map directly to .fylle
_CREWAI_MAPPED_FIELDS = {
    "role", "goal", "backstory", "tools", "llm",
    "max_iter", "verbose", "allow_delegation", "memory",
}


def crewai_to_fylle(
    crewai_config: dict | str,
    agent_key: str | None = None,
    author_name: str = "Unknown",
    author_url: str | None = None,
    version: str = "1.0.0",
    license_id: str = "MIT",
) -> FylleAgent:
    """Convert a CrewAI agent YAML definition to a FylleAgent.

    Args:
        crewai_config: Parsed YAML dict from a CrewAI agents.yaml file,
                       or a YAML string to be parsed.
        agent_key: Which agent to extract (if config has multiple).
                   If None, takes the first one.
        author_name: Author name for the .fylle manifest.
        author_url: Author URL.
        version: Version string for the .fylle manifest.
        license_id: SPDX license identifier.

    Returns:
        A validated FylleAgent ready for build_fylle_package().
    """
    if isinstance(crewai_config, str):
        crewai_config = yaml.safe_load(crewai_config)

    # Select the agent from config
    if agent_key is None:
        agent_key = next(iter(crewai_config))
    agent_data = crewai_config[agent_key]

    # Extract core fields
    role = agent_data.get("role", "Assistant")
    goal = agent_data.get("goal", "")
    backstory = agent_data.get("backstory", "")
    tools_list = agent_data.get("tools", [])
    llm = agent_data.get("llm", "claude-sonnet-4-5")
    max_iter = agent_data.get("max_iter", 25)

    # Build agent name from key
    name = agent_key.replace("_", " ").replace("-", " ").title()

    # Build tool declarations
    tool_declarations = []
    for tool_name in tools_list:
        tool_declarations.append(
            ToolDeclaration(
                name=tool_name,
                protocol=ToolProtocol.FUNCTION,
                description=f"CrewAI tool: {tool_name}",
            )
        )

    # Collect CrewAI-specific fields into extensions
    crewai_extensions: dict[str, Any] = {}
    for key, value in agent_data.items():
        if key not in _CREWAI_MAPPED_FIELDS:
            crewai_extensions[key] = value
    if agent_data.get("allow_delegation") is not None:
        crewai_extensions["allow_delegation"] = agent_data["allow_delegation"]
    if agent_data.get("verbose") is not None:
        crewai_extensions["verbose"] = agent_data["verbose"]

    extensions: dict[str, Any] = {}
    if crewai_extensions:
        extensions["crewai"] = crewai_extensions

    # Build the manifest
    manifest = FylleManifest(
        fylle_format="0.1.0",
        agent=AgentIdentity(
            name=name,
            version=version,
            description=goal[:500] if goal else f"Agent imported from CrewAI: {name}",
            role=role,
            author=AgentAuthor(name=author_name, url=author_url),
            license=license_id,
            model=ModelRequirements(
                preferred=llm,
                settings=ModelSettings(temperature=0.7, max_tokens=4000),
            ),
            prompt_file="agent.md",
            language=["en"],
            inputs=[
                AgentInput(
                    name="task",
                    type="text",
                    required=True,
                    description="The task or question for the agent",
                ),
            ],
            output=AgentOutput(format=OutputFormat.MARKDOWN),
            tools=ToolsConfig(required=tool_declarations) if tool_declarations else ToolsConfig(),
            guardrails=GuardrailsRef(
                max_autonomy=MaxAutonomy.DRAFT_ONLY,
                limits=GuardrailLimits(
                    max_iterations=max_iter,
                    max_tokens_per_response=4000,
                ),
            ),
            extensions=extensions,
        ),
    )

    # Build personality (system prompt) from backstory
    personality = backstory if backstory else f"You are a {role}. Your goal is: {goal}"

    return FylleAgent(
        manifest=manifest,
        personality=personality,
    )


def fylle_to_crewai(agent: FylleAgent) -> dict:
    """Convert a FylleAgent to CrewAI agent YAML format.

    Returns a dict that can be dumped as valid CrewAI agents.yaml content.
    The dict has one key (agent name, snake_cased) containing:
      role, goal, backstory, tools, llm, max_iter, etc.

    Note: Tools are listed by name only. The user must provide
    actual Python tool implementations in their CrewAI project.
    """
    identity = agent.manifest.agent

    # Snake_case the agent name for YAML key
    agent_key = identity.name.lower().replace(" ", "_").replace("-", "_")

    # Collect tool names
    tools = [t.name for t in identity.tools.required]
    tools.extend(t.name for t in identity.tools.optional)

    # Build the CrewAI agent dict
    crewai_agent: dict[str, Any] = {
        "role": identity.role or identity.name,
        "goal": identity.description,
        "backstory": agent.personality,
    }

    if tools:
        crewai_agent["tools"] = tools

    crewai_agent["llm"] = identity.model.preferred

    if identity.guardrails and identity.guardrails.limits:
        crewai_agent["max_iter"] = identity.guardrails.limits.max_iterations

    # Restore CrewAI-specific extensions
    crewai_ext = identity.extensions.get("crewai", {})
    for key, value in crewai_ext.items():
        crewai_agent[key] = value

    return {agent_key: crewai_agent}


def crewai_to_fylle_yaml(crewai_yaml_path: str, **kwargs: Any) -> FylleAgent:
    """Convenience: read a CrewAI YAML file and convert to FylleAgent."""
    with open(crewai_yaml_path) as f:
        config = yaml.safe_load(f)
    return crewai_to_fylle(config, **kwargs)
