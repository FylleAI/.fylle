"""
Builder for .fylle agent packages.

Creates .fylle ZIP archives from FylleAgent objects or from scratch.
"""

from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO
from pathlib import Path

import yaml

from fylle_format.schema import (
    AgentAuthor,
    AgentIdentity,
    AgentInput,
    FylleAgent,
    FylleManifest,
    ModelRequirements,
    Skill,
)


def build_fylle_package(agent: FylleAgent, output_path: str | Path) -> str:
    """Build a .fylle ZIP package from a FylleAgent object.

    Args:
        agent: A validated FylleAgent object.
        output_path: Path where the .fylle file will be written.

    Returns:
        The path to the created .fylle file.
    """
    output_path = Path(output_path)

    # Ensure .fylle extension
    if output_path.suffix != ".fylle":
        output_path = output_path.with_suffix(".fylle")

    buf = BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write manifest.yaml
        manifest_dict = _manifest_to_dict(agent.manifest)
        manifest_yaml = yaml.dump(manifest_dict, default_flow_style=False, allow_unicode=True)
        zf.writestr("manifest.yaml", manifest_yaml)

        # Write agent.md (system prompt)
        prompt_file = agent.manifest.agent.prompt_file
        zf.writestr(prompt_file, agent.personality)

        # Write skills
        for i, skill in enumerate(agent.skills):
            if i < len(agent.manifest.agent.skills):
                skill_path = agent.manifest.agent.skills[i].ref
            else:
                skill_path = f"skills/{skill.name.lower().replace(' ', '-')}.yaml"
            skill_dict = {"skill": _skill_to_dict(skill)}
            skill_yaml = yaml.dump(skill_dict, default_flow_style=False, allow_unicode=True)
            zf.writestr(skill_path, skill_yaml)

        # Write guardrails.yaml
        if agent.guardrails:
            guardrails_dict = {"guardrails": _guardrails_to_dict(agent.guardrails)}
            guardrails_yaml = yaml.dump(guardrails_dict, default_flow_style=False, allow_unicode=True)
            guardrails_file = agent.manifest.agent.guardrails.file or "guardrails.yaml"
            zf.writestr(guardrails_file, guardrails_yaml)

        # Write memory-schema.yaml
        if agent.memory_schema:
            memory_dict = {"memory": _memory_to_dict(agent.memory_schema)}
            memory_yaml = yaml.dump(memory_dict, default_flow_style=False, allow_unicode=True)
            schema_file = (
                agent.manifest.agent.memory.schema_file
                if agent.manifest.agent.memory
                else "memory-schema.yaml"
            )
            zf.writestr(schema_file, memory_yaml)

        # Write README.md
        if agent.readme:
            zf.writestr("README.md", agent.readme)

    # Write to disk
    file_bytes = buf.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(file_bytes)

    return str(output_path)


def create_fylle_from_scratch(
    name: str,
    description: str,
    personality: str,
    version: str = "1.0.0",
    author_name: str = "Unknown",
    author_url: str | None = None,
    author_email: str | None = None,
    license: str = "MIT",
    model_preferred: str = "claude-sonnet-4-5",
    role: str | None = None,
    tone: str | None = None,
    language: list[str] | None = None,
    inputs: list[dict] | None = None,
    skills: list[dict] | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
) -> FylleAgent:
    """Create a FylleAgent from scratch with sensible defaults.

    This is a convenience factory for creating agents programmatically.

    Args:
        name: Agent display name.
        description: One-line description.
        personality: System prompt content (will become agent.md).
        version: Agent version (semver). Default: "1.0.0".
        author_name: Author name. Default: "Unknown".
        license: SPDX license identifier. Default: "MIT".
        model_preferred: Preferred model ID. Default: "claude-sonnet-4-5".
        role: Agent role/persona.
        inputs: List of input dicts with name, type, required, description.
        skills: List of skill dicts matching the Skill schema.
        tags: Searchable tags.
        category: Primary category.

    Returns:
        A FylleAgent ready for build_fylle_package().
    """
    # Build inputs
    parsed_inputs = []
    if inputs:
        for inp in inputs:
            parsed_inputs.append(AgentInput(**inp))

    # Build skills
    parsed_skills = []
    skill_refs = []
    if skills:
        for skill_data in skills:
            skill = Skill(**skill_data)
            parsed_skills.append(skill)
            ref_path = f"skills/{skill.name.lower().replace(' ', '-')}.yaml"
            skill_refs.append({"ref": ref_path})

    manifest = FylleManifest(
        fylle_format="0.1.0",
        agent=AgentIdentity(
            name=name,
            version=version,
            description=description,
            role=role,
            author=AgentAuthor(
                name=author_name,
                url=author_url,
                email=author_email,
            ),
            license=license,
            model=ModelRequirements(preferred=model_preferred),
            prompt_file="agent.md",
            tone=tone,
            language=language or ["en"],
            inputs=parsed_inputs,
            skills=[{"ref": s["ref"]} for s in skill_refs] if skill_refs else [],
            tags=tags or [],
            category=category,
        ),
    )

    return FylleAgent(
        manifest=manifest,
        personality=personality,
        skills=parsed_skills,
    )


# ============================================================
# Serialization helpers
# ============================================================

def _manifest_to_dict(manifest: FylleManifest) -> dict:
    """Convert a FylleManifest to a clean dict for YAML serialization."""
    data = manifest.model_dump(mode="json", exclude_none=True, exclude_defaults=False)
    # Clean up empty collections
    _remove_empty(data)
    return data


def _skill_to_dict(skill: Skill) -> dict:
    """Convert a Skill to a dict for YAML serialization."""
    data = skill.model_dump(mode="json", exclude_none=True)
    _remove_empty(data)
    return data


def _guardrails_to_dict(guardrails) -> dict:
    """Convert Guardrails to a dict for YAML serialization."""
    return guardrails.model_dump(mode="json", exclude_none=True)


def _memory_to_dict(memory) -> dict:
    """Convert MemorySchema to a dict for YAML serialization."""
    return memory.model_dump(mode="json", exclude_none=True)


def _remove_empty(d: dict) -> None:
    """Remove empty lists and dicts from a nested dict (in place)."""
    keys_to_remove = []
    for key, value in d.items():
        if isinstance(value, dict):
            _remove_empty(value)
            if not value:
                keys_to_remove.append(key)
        elif isinstance(value, list) and not value:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del d[key]
