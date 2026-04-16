"""Claude Code <-> .fylle adapter.

Translates between Claude Code's project configuration and .fylle FylleAgent objects.

Claude Code agents are configured via:
    CLAUDE.md           — Project instructions (Markdown)
    .mcp.json           — MCP server/tool configuration (JSON)
    .claude/settings.json — Permissions, model, preferences (JSON)
    .claude/rules/*.md  — Modular rules with path scoping
    .claude/skills/     — SKILL.md files with YAML frontmatter

This adapter generates a complete Claude Code workspace from a .fylle agent,
making it the ideal target for migrations from other frameworks.
"""

from __future__ import annotations

import json
from typing import Any

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


class ClaudeCodeAdapter(FrameworkAdapter):
    """Adapter for translating between Claude Code config and .fylle format."""

    @property
    def framework_name(self) -> str:
        return "Claude Code"

    def to_fylle(self, source: dict, **kwargs: Any) -> FylleAgent:
        return claude_code_to_fylle(source, **kwargs)

    def from_fylle(self, agent: FylleAgent) -> dict:
        return fylle_to_claude_code(agent)


def claude_code_to_fylle(
    workspace: dict,
    author_name: str = "Unknown",
    author_url: str | None = None,
    version: str = "1.0.0",
    license_id: str = "MIT",
) -> FylleAgent:
    """Convert a Claude Code workspace config to a FylleAgent.

    Args:
        workspace: Dict with keys:
            - 'claude_md': str — CLAUDE.md content (required)
            - 'mcp_json': dict — .mcp.json parsed content (optional)
            - 'settings_json': dict — .claude/settings.json (optional)
            - 'name': str — Project/agent name (optional)
        author_name: Author name.
        version: Version string.
        license_id: SPDX license identifier.

    Returns:
        A validated FylleAgent.
    """
    claude_md = workspace.get("claude_md", "")
    mcp_config = workspace.get("mcp_json", {})
    settings = workspace.get("settings_json", {})
    name = workspace.get("name", "Claude Code Agent")

    # Extract model from settings
    model = settings.get("model", "claude-sonnet-4-5")

    # Parse MCP servers into tool declarations
    tool_declarations: list[ToolDeclaration] = []
    mcp_servers = mcp_config.get("mcpServers", {})
    for server_name, server_config in mcp_servers.items():
        tool_declarations.append(
            ToolDeclaration(
                name=server_name,
                protocol=ToolProtocol.MCP,
                description=f"MCP server: {server_name}",
                server=server_name,
            )
        )

    # Map permissions to autonomy level
    permissions = settings.get("permissions", {})
    default_mode = permissions.get("defaultMode", "")
    if default_mode == "acceptEdits":
        autonomy = MaxAutonomy.FULL
    else:
        autonomy = MaxAutonomy.HUMAN_APPROVAL

    # Collect Claude Code specific extensions
    cc_extensions: dict[str, Any] = {}
    if permissions.get("allow"):
        cc_extensions["allowed_tools"] = permissions["allow"]
    if permissions.get("deny"):
        cc_extensions["denied_tools"] = permissions["deny"]
    if mcp_config:
        cc_extensions["mcp_config"] = mcp_config

    extensions: dict[str, Any] = {}
    if cc_extensions:
        extensions["claude_code"] = cc_extensions

    manifest = FylleManifest(
        fylle_format="0.1.0",
        agent=AgentIdentity(
            name=name,
            version=version,
            description=f"Agent imported from Claude Code: {name}",
            author=AgentAuthor(name=author_name, url=author_url),
            license=license_id,
            model=ModelRequirements(
                preferred=model,
                settings=ModelSettings(temperature=0.7, max_tokens=4000),
            ),
            prompt_file="agent.md",
            language=["en"],
            inputs=[
                AgentInput(
                    name="task",
                    type="text",
                    required=True,
                    description="The task or instruction for the agent",
                ),
            ],
            output=AgentOutput(format=OutputFormat.MARKDOWN),
            tools=ToolsConfig(required=tool_declarations) if tool_declarations else ToolsConfig(),
            guardrails=GuardrailsRef(
                max_autonomy=autonomy,
                limits=GuardrailLimits(max_tokens_per_response=4000),
            ),
            extensions=extensions,
        ),
    )

    return FylleAgent(
        manifest=manifest,
        personality=claude_md if claude_md else f"You are {name}.",
    )


def fylle_to_claude_code(agent: FylleAgent) -> dict:
    """Convert a FylleAgent to Claude Code workspace files.

    Returns a dict with keys:
        'claude_md': str       — CLAUDE.md content
        'mcp_json': dict       — .mcp.json content (if agent has MCP tools)
        'settings_json': dict  — .claude/settings.json content
        'rules': list[dict]    — List of {filename: str, content: str} for .claude/rules/

    This output can be written directly to a Claude Code project directory.
    """
    identity = agent.manifest.agent

    # ── Build CLAUDE.md ──
    lines = [f"# {identity.name}", ""]

    if identity.description:
        lines.append(identity.description)
        lines.append("")

    # Add the personality/system prompt as the main content
    if agent.personality:
        lines.append(agent.personality)
        lines.append("")

    # Add input hints
    if identity.inputs:
        lines.append("## Expected Inputs")
        for inp in identity.inputs:
            required = "(required)" if inp.required else "(optional)"
            lines.append(f"- **{inp.name}** {required}: {inp.description}")
        lines.append("")

    # Add output format hint
    if identity.output.format != OutputFormat.MARKDOWN:
        lines.append(f"## Output Format")
        lines.append(f"Respond in **{identity.output.format.value}** format.")
        lines.append("")

    claude_md = "\n".join(lines)

    # ── Build .mcp.json ──
    mcp_json: dict[str, Any] = {}
    mcp_servers: dict[str, Any] = {}

    # Check if there's a saved MCP config in extensions
    cc_ext = identity.extensions.get("claude_code", {})
    if cc_ext.get("mcp_config"):
        mcp_json = cc_ext["mcp_config"]
    else:
        # Generate MCP entries from tool declarations
        for tool in identity.tools.required:
            if tool.protocol == ToolProtocol.MCP and tool.server:
                mcp_servers[tool.server] = {
                    "command": tool.server,
                    "args": [],
                }
        for tool in identity.tools.optional:
            if tool.protocol == ToolProtocol.MCP and tool.server:
                mcp_servers[tool.server] = {
                    "command": tool.server,
                    "args": [],
                }
        if mcp_servers:
            mcp_json = {"mcpServers": mcp_servers}

    # ── Build .claude/settings.json ──
    settings: dict[str, Any] = {
        "model": identity.model.preferred,
    }

    # Map autonomy to permissions
    if identity.guardrails.max_autonomy == MaxAutonomy.FULL:
        settings["permissions"] = {"defaultMode": "acceptEdits"}

    # Restore saved permissions from extensions
    if cc_ext.get("allowed_tools"):
        settings.setdefault("permissions", {})["allow"] = cc_ext["allowed_tools"]
    if cc_ext.get("denied_tools"):
        settings.setdefault("permissions", {})["deny"] = cc_ext["denied_tools"]

    # ── Build .claude/rules/ ──
    rules: list[dict[str, str]] = []
    if agent.guardrails and agent.guardrails.rules:
        rule_lines = ["# Agent Rules", ""]
        for rule in agent.guardrails.rules:
            rule_lines.append(f"- {rule.description}")
        rules.append({
            "filename": "agent-rules.md",
            "content": "\n".join(rule_lines),
        })

    if agent.guardrails and agent.guardrails.content_policies:
        cp = agent.guardrails.content_policies
        if cp.prohibited_topics or cp.required_disclaimers or cp.tone_boundaries:
            policy_lines = ["# Content Policies", ""]
            if cp.prohibited_topics:
                policy_lines.append("## Prohibited Topics")
                for topic in cp.prohibited_topics:
                    policy_lines.append(f"- Do NOT discuss: {topic}")
                policy_lines.append("")
            if cp.required_disclaimers:
                policy_lines.append("## Required Disclaimers")
                for disc in cp.required_disclaimers:
                    policy_lines.append(f"- Always include: {disc}")
                policy_lines.append("")
            if cp.tone_boundaries:
                policy_lines.append(f"## Tone Boundaries")
                policy_lines.append(cp.tone_boundaries)
            rules.append({
                "filename": "content-policies.md",
                "content": "\n".join(policy_lines),
            })

    return {
        "claude_md": claude_md,
        "mcp_json": mcp_json,
        "settings_json": settings,
        "rules": rules,
    }
