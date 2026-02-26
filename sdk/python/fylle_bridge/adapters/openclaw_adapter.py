"""OpenClaw <-> .fylle adapter.

Translates between OpenClaw's SOUL.md agent definitions and .fylle FylleAgent objects.

OpenClaw agents are defined via Markdown files in a workspace:
    SOUL.md      — Identity, personality, rules (the core agent definition)
    IDENTITY.md  — Agent name and emoji
    TOOLS.md     — Tool usage notes
    USER.md      — User profile/context
    skills/      — SKILL.md files with YAML frontmatter

SOUL.md typical structure:
    # AgentName

    ## Identity
    - **Name:** AgentName
    - **Role:** Role Description
    - **Model:** claude-sonnet-4-5
    - **Tone:** professional

    ## Personality
    You are a meticulous...

    ## Skills
    - Web Search
    - Code Generation

    ## Rules
    Always respond in English
    Never share sensitive data
"""

from __future__ import annotations

import re
from typing import Any

from fylle_format.schema import (
    AgentAuthor,
    AgentIdentity,
    AgentInput,
    AgentOutput,
    FylleAgent,
    FylleManifest,
    GuardrailLimits,
    GuardrailRule,
    Guardrails,
    GuardrailSeverity,
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


class OpenClawAdapter(FrameworkAdapter):
    """Adapter for translating between OpenClaw SOUL.md and .fylle format."""

    @property
    def framework_name(self) -> str:
        return "OpenClaw"

    def to_fylle(self, source: dict, **kwargs: Any) -> FylleAgent:
        return openclaw_to_fylle(source, **kwargs)

    def from_fylle(self, agent: FylleAgent) -> dict:
        return fylle_to_openclaw(agent)


def parse_soul_md(content: str) -> dict:
    """Parse a SOUL.md file into structured sections.

    Returns a dict with keys: identity, personality, greeting, skills, rules,
    and any other H2 sections found.
    """
    sections: dict[str, str] = {}
    current_section = "_preamble"
    current_lines: list[str] = []

    for line in content.split("\n"):
        # Detect H2 section headers
        if line.startswith("## "):
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip().lower()
            current_lines = []
        # Detect H1 (agent name)
        elif line.startswith("# ") and current_section == "_preamble":
            sections["_title"] = line[2:].strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def _parse_identity_block(text: str) -> dict[str, str]:
    """Parse Identity section key-value pairs.

    Handles formats like:
        - **Name:** AgentName
        - **Role:** Role Description
        - Name: AgentName
    """
    result: dict[str, str] = {}
    for line in text.split("\n"):
        line = line.strip().lstrip("- ")
        # Match **Key:** Value (colon inside bold) or **Key**: Value or Key: Value
        match = re.match(r"\*\*(.+?):\*\*\s*(.+)", line)
        if not match:
            match = re.match(r"\*\*(.+?)\*\*:\s*(.+)", line)
        if not match:
            match = re.match(r"(.+?):\s*(.+)", line)
        if match:
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            result[key] = value
    return result


def _parse_list_items(text: str) -> list[str]:
    """Parse a markdown list into items."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
        elif line and not line.startswith("#"):
            items.append(line)
    return [i for i in items if i]


def openclaw_to_fylle(
    soul_data: dict | str,
    author_name: str = "Unknown",
    author_url: str | None = None,
    version: str = "1.0.0",
    license_id: str = "MIT",
) -> FylleAgent:
    """Convert an OpenClaw SOUL.md to a FylleAgent.

    Args:
        soul_data: Either:
            - A string containing the raw SOUL.md content
            - A dict with keys: 'soul_md' (required), 'identity_md', 'tools_md', 'user_md'
        author_name: Author name for the .fylle manifest.
        author_url: Author URL.
        version: Version string.
        license_id: SPDX license identifier.

    Returns:
        A validated FylleAgent.
    """
    # Handle string input (raw SOUL.md content)
    if isinstance(soul_data, str):
        soul_content = soul_data
        extra_files: dict[str, str] = {}
    else:
        soul_content = soul_data.get("soul_md", "")
        extra_files = {k: v for k, v in soul_data.items() if k != "soul_md"}

    # Parse SOUL.md sections
    sections = parse_soul_md(soul_content)
    identity_block = _parse_identity_block(sections.get("identity", ""))

    # Extract agent identity
    name = identity_block.get("name") or sections.get("_title", "OpenClaw Agent")
    role = identity_block.get("role", "")
    model_str = identity_block.get("model", "claude-sonnet-4-5")
    tone = identity_block.get("tone", "")

    # Build personality from Personality section + any extra context
    personality_parts = []
    if sections.get("personality"):
        personality_parts.append(sections["personality"])
    if sections.get("greeting"):
        personality_parts.append(f"\n## Greeting\n{sections['greeting']}")

    # Include other non-standard sections as part of personality
    skip_sections = {"_preamble", "_title", "identity", "personality",
                     "greeting", "skills", "rules"}
    for section_name, section_content in sections.items():
        if section_name not in skip_sections and section_content:
            personality_parts.append(f"\n## {section_name.title()}\n{section_content}")

    personality = "\n".join(personality_parts) if personality_parts else f"You are {name}."

    # Parse skills
    skills_list = _parse_list_items(sections.get("skills", ""))

    # Parse rules → guardrails
    rules_list = _parse_list_items(sections.get("rules", ""))
    guardrail_rules = []
    for i, rule in enumerate(rules_list):
        guardrail_rules.append(
            GuardrailRule(
                id=f"rule-{i + 1}",
                description=rule,
                severity=GuardrailSeverity.WARN,
                condition=rule,
            )
        )

    # Map model string (OpenClaw uses "provider/model" or just model name)
    if "/" in model_str:
        model_preferred = model_str.split("/", 1)[1]
    else:
        # Normalize common OpenClaw model names
        model_map = {
            "claude sonnet 4.5": "claude-sonnet-4-5",
            "claude opus 4.5": "claude-opus-4-5",
            "claude haiku 3.5": "claude-haiku-3-5",
            "gpt-4o": "gpt-4o",
        }
        model_preferred = model_map.get(model_str.lower(), model_str)

    # Build tool declarations from skills
    tool_declarations = []
    for skill in skills_list:
        tool_declarations.append(
            ToolDeclaration(
                name=skill.lower().replace(" ", "_"),
                protocol=ToolProtocol.FUNCTION,
                description=f"OpenClaw skill: {skill}",
            )
        )

    # Collect OpenClaw-specific data into extensions
    openclaw_ext: dict[str, Any] = {}
    if sections.get("greeting"):
        openclaw_ext["greeting"] = sections["greeting"]
    if extra_files.get("user_md"):
        openclaw_ext["user_context"] = extra_files["user_md"]
    if extra_files.get("tools_md"):
        openclaw_ext["tools_notes"] = extra_files["tools_md"]

    extensions: dict[str, Any] = {}
    if openclaw_ext:
        extensions["openclaw"] = openclaw_ext

    description = sections.get("personality", "")[:500] if sections.get("personality") else f"Agent migrated from OpenClaw: {name}"

    # Build manifest
    manifest = FylleManifest(
        fylle_format="0.1.0",
        agent=AgentIdentity(
            name=name,
            version=version,
            description=description,
            role=role or name,
            author=AgentAuthor(name=author_name, url=author_url),
            license=license_id,
            model=ModelRequirements(
                preferred=model_preferred,
                settings=ModelSettings(temperature=0.7, max_tokens=4000),
            ),
            prompt_file="agent.md",
            tone=tone or None,
            language=["en"],
            inputs=[
                AgentInput(
                    name="message",
                    type="text",
                    required=True,
                    description="The user message or task",
                ),
            ],
            output=AgentOutput(format=OutputFormat.MARKDOWN),
            tools=ToolsConfig(optional=tool_declarations) if tool_declarations else ToolsConfig(),
            guardrails=GuardrailsRef(
                max_autonomy=MaxAutonomy.HUMAN_APPROVAL,
                limits=GuardrailLimits(max_tokens_per_response=4000),
            ),
            tags=["openclaw", "migrated"],
            extensions=extensions,
        ),
    )

    guardrails_obj = Guardrails(rules=guardrail_rules) if guardrail_rules else None

    return FylleAgent(
        manifest=manifest,
        personality=personality,
        guardrails=guardrails_obj,
    )


def fylle_to_openclaw(agent: FylleAgent) -> dict:
    """Convert a FylleAgent to OpenClaw workspace files.

    Returns a dict with keys:
        'soul_md': str — The SOUL.md content
        'identity_md': str — The IDENTITY.md content (optional)
    """
    identity = agent.manifest.agent

    # Build SOUL.md
    lines = [f"# {identity.name}", ""]

    # Identity section
    lines.append("## Identity")
    lines.append(f"- **Name:** {identity.name}")
    if identity.role:
        lines.append(f"- **Role:** {identity.role}")
    lines.append(f"- **Model:** {identity.model.preferred}")
    if identity.tone:
        lines.append(f"- **Tone:** {identity.tone}")
    lines.append("")

    # Personality section
    lines.append("## Personality")
    # Extract just the personality part (before any ## subsections)
    personality = agent.personality
    lines.append(personality)
    lines.append("")

    # Greeting (from extensions if available)
    openclaw_ext = identity.extensions.get("openclaw", {})
    if openclaw_ext.get("greeting"):
        lines.append("## Greeting")
        lines.append(f"> {openclaw_ext['greeting']}")
        lines.append("")

    # Skills section
    all_tools = list(identity.tools.required) + list(identity.tools.optional)
    if all_tools:
        lines.append("## Skills")
        for tool in all_tools:
            skill_name = tool.name.replace("_", " ").title()
            lines.append(f"- {skill_name}")
        lines.append("")

    # Rules section (from guardrails)
    if agent.guardrails and agent.guardrails.rules:
        lines.append("## Rules")
        for rule in agent.guardrails.rules:
            lines.append(rule.description)
        lines.append("")

    soul_md = "\n".join(lines)

    # Build IDENTITY.md
    identity_md = f"# {identity.name}\n"

    return {
        "soul_md": soul_md,
        "identity_md": identity_md,
    }


def openclaw_soul_to_fylle(soul_md_path: str, **kwargs: Any) -> FylleAgent:
    """Convenience: read a SOUL.md file and convert to FylleAgent."""
    with open(soul_md_path) as f:
        content = f.read()
    return openclaw_to_fylle(content, **kwargs)
