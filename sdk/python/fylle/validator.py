"""
Validator for .fylle agent packages.

Performs semantic validation beyond what Pydantic schema catches:
cross-file references, content quality, best practices.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fylle.schema import FylleAgent, MaxAutonomy


@dataclass
class ValidationResult:
    """Result of validating a .fylle agent package."""
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        self.info.append(message)


def validate(agent: FylleAgent) -> ValidationResult:
    """Validate a parsed FylleAgent for semantic correctness.

    This goes beyond Pydantic schema validation to check:
    - Cross-file references (skills exist, guardrails file matches)
    - Content quality (prompt not too short, etc.)
    - Best practices (inputs declared, output specified)

    Args:
        agent: A parsed FylleAgent object.

    Returns:
        ValidationResult with errors, warnings, and info messages.
    """
    result = ValidationResult()

    _validate_manifest(agent, result)
    _validate_personality(agent, result)
    _validate_skills(agent, result)
    _validate_guardrails(agent, result)
    _validate_tools(agent, result)
    _validate_inputs_outputs(agent, result)
    _validate_memory(agent, result)

    # Summary info
    result.add_info(
        f"Agent: {agent.manifest.agent.name} v{agent.manifest.agent.version}"
    )
    result.add_info(f"Author: {agent.manifest.agent.author.name}")
    result.add_info(f"License: {agent.manifest.agent.license}")
    result.add_info(f"Skills: {len(agent.skills)}")
    result.add_info(
        f"Tools: {len(agent.manifest.agent.tools.required)} required, "
        f"{len(agent.manifest.agent.tools.optional)} optional"
    )

    return result


# ============================================================
# Validation checks
# ============================================================

def _validate_manifest(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate manifest completeness and consistency."""
    manifest = agent.manifest
    identity = manifest.agent

    # Check description quality
    if len(identity.description) < 10:
        result.add_warning(
            "Description is very short. A good description helps discoverability."
        )

    # Check license is known SPDX
    known_licenses = {
        "MIT", "Apache-2.0", "GPL-3.0", "GPL-2.0", "BSD-2-Clause",
        "BSD-3-Clause", "ISC", "MPL-2.0", "LGPL-3.0", "AGPL-3.0",
        "Unlicense", "CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0",
        "Proprietary",
    }
    if identity.license not in known_licenses:
        result.add_warning(
            f"License '{identity.license}' is not a recognized SPDX identifier. "
            f"Common licenses: MIT, Apache-2.0, GPL-3.0"
        )

    # Check language codes
    for lang in identity.language:
        if len(lang) != 2:
            result.add_warning(
                f"Language '{lang}' should be a 2-letter ISO 639-1 code"
            )


def _validate_personality(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate the system prompt content."""
    if not agent.personality or not agent.personality.strip():
        result.add_error("System prompt (agent.md) is empty")
        return

    prompt_len = len(agent.personality)
    if prompt_len < 50:
        result.add_warning(
            f"System prompt is very short ({prompt_len} chars). "
            "A detailed prompt produces better agent behavior."
        )

    if prompt_len > 50_000:
        result.add_warning(
            f"System prompt is very long ({prompt_len} chars). "
            "Consider splitting into skills for modularity."
        )


def _validate_skills(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate skills consistency."""
    skill_refs = {s.ref for s in agent.manifest.agent.skills}
    loaded_names = {s.name for s in agent.skills}

    # Check count matches
    if len(skill_refs) != len(agent.skills):
        result.add_warning(
            f"Manifest declares {len(skill_refs)} skills but {len(agent.skills)} were loaded"
        )

    # Check skills reference tools that the agent declares
    agent_tools = set()
    for t in agent.manifest.agent.tools.required:
        agent_tools.add(t.name)
    for t in agent.manifest.agent.tools.optional:
        agent_tools.add(t.name)

    for skill in agent.skills:
        for tool_name in skill.tools_used:
            if tool_name not in agent_tools:
                result.add_warning(
                    f"Skill '{skill.name}' uses tool '{tool_name}' "
                    f"which is not declared in manifest tools"
                )


def _validate_guardrails(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate guardrails configuration."""
    autonomy = agent.manifest.agent.guardrails.max_autonomy

    if autonomy == MaxAutonomy.FULL and not agent.guardrails:
        result.add_warning(
            "Agent has 'full' autonomy but no guardrails defined. "
            "Consider adding guardrails for safety."
        )

    if agent.guardrails:
        # Check for duplicate rule IDs
        rule_ids = [r.id for r in agent.guardrails.rules]
        duplicates = {rid for rid in rule_ids if rule_ids.count(rid) > 1}
        if duplicates:
            result.add_error(
                f"Duplicate guardrail rule IDs: {duplicates}"
            )


def _validate_tools(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate tool declarations."""
    all_tools = (
        agent.manifest.agent.tools.required + agent.manifest.agent.tools.optional
    )

    # Check for duplicate tool names
    tool_names = [t.name for t in all_tools]
    duplicates = {tn for tn in tool_names if tool_names.count(tn) > 1}
    if duplicates:
        result.add_error(f"Duplicate tool names: {duplicates}")

    # Check that required tools have descriptions
    for tool in agent.manifest.agent.tools.required:
        if not tool.description:
            result.add_warning(
                f"Required tool '{tool.name}' has no description. "
                "Descriptions help runtimes map tools correctly."
            )


def _validate_inputs_outputs(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate input/output declarations."""
    if not agent.manifest.agent.inputs:
        result.add_warning(
            "No inputs declared. Declaring inputs helps runtimes "
            "know what to inject and enables composability."
        )

    # Check for duplicate input names
    input_names = [i.name for i in agent.manifest.agent.inputs]
    duplicates = {n for n in input_names if input_names.count(n) > 1}
    if duplicates:
        result.add_error(f"Duplicate input names: {duplicates}")


def _validate_memory(agent: FylleAgent, result: ValidationResult) -> None:
    """Validate memory schema if present."""
    if agent.manifest.agent.memory and not agent.memory_schema:
        result.add_warning(
            "Manifest references memory schema but memory-schema.yaml was not found"
        )

    if agent.memory_schema:
        # Check for duplicate entity names
        entity_names = [e.name for e in agent.memory_schema.entities]
        duplicates = {n for n in entity_names if entity_names.count(n) > 1}
        if duplicates:
            result.add_error(f"Duplicate memory entity names: {duplicates}")

        result.add_info(
            f"Memory: {len(agent.memory_schema.entities)} entities declared"
        )
