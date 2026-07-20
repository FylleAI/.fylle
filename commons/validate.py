#!/usr/bin/env python3
"""Validate and build every source artifact in Fylle Commons.

All archives are created under a temporary directory. The source tree remains
unchanged.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMONS_ROOT = REPO_ROOT / "commons"
SDK_ROOT = REPO_ROOT / "sdk" / "python"
sys.path.insert(0, str(SDK_ROOT))

from fylle.builder import build_fylle_package  # noqa: E402
from fylle.parser import parse_fylle_package  # noqa: E402
from fylle.schema import (  # noqa: E402
    BriefSchema,
    FylleAgent,
    FylleManifest,
    FyllePackManifest,
    Guardrails,
    MemorySchema,
    Skill,
)
from fylle.validator import validate  # noqa: E402


class CommonsValidationError(RuntimeError):
    """Raised when a commons source artifact violates its contract."""


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CommonsValidationError(f"{path}: expected a YAML object")
    return data


def load_agent_source(agent_dir: Path) -> FylleAgent:
    manifest_path = agent_dir / "manifest.yaml"
    manifest = FylleManifest(**load_yaml(manifest_path))

    prompt_path = agent_dir / manifest.agent.prompt_file
    if not prompt_path.is_file():
        raise CommonsValidationError(f"{manifest_path}: missing {manifest.agent.prompt_file}")
    personality = prompt_path.read_text(encoding="utf-8")

    skills = []
    for skill_ref in manifest.agent.skills:
        skill_path = agent_dir / skill_ref.ref
        skill_data = load_yaml(skill_path)
        if "skill" not in skill_data:
            raise CommonsValidationError(f"{skill_path}: missing 'skill' root key")
        skills.append(Skill(**skill_data["skill"]))

    guardrails = None
    guardrail_ref = manifest.agent.guardrails.file
    if guardrail_ref:
        guardrail_path = agent_dir / guardrail_ref
        guardrail_data = load_yaml(guardrail_path)
        if "guardrails" not in guardrail_data:
            raise CommonsValidationError(f"{guardrail_path}: missing 'guardrails' root key")
        guardrails = Guardrails(**guardrail_data["guardrails"])

    memory_schema = None
    if manifest.agent.memory:
        memory_path = agent_dir / manifest.agent.memory.schema_file
        memory_data = load_yaml(memory_path)
        if "memory" not in memory_data:
            raise CommonsValidationError(f"{memory_path}: missing 'memory' root key")
        memory_schema = MemorySchema(**memory_data["memory"])

    readme_path = agent_dir / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else None

    return FylleAgent(
        manifest=manifest,
        personality=personality,
        skills=skills,
        guardrails=guardrails,
        memory_schema=memory_schema,
        readme=readme,
    )


def validate_native_skills() -> list[Path]:
    skill_files = sorted((COMMONS_ROOT / "skills").glob("*/SKILL.md"))
    if not skill_files:
        raise CommonsValidationError("commons/skills contains no SKILL.md files")

    for skill_file in skill_files:
        content = skill_file.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            raise CommonsValidationError(f"{skill_file}: missing YAML frontmatter")
        parts = content.split("---", 2)
        if len(parts) != 3:
            raise CommonsValidationError(f"{skill_file}: malformed YAML frontmatter")
        metadata = yaml.safe_load(parts[1])
        if set(metadata or {}) != {"name", "description"}:
            raise CommonsValidationError(
                f"{skill_file}: frontmatter must contain only name and description"
            )
        if metadata["name"] != skill_file.parent.name:
            raise CommonsValidationError(
                f"{skill_file}: name must match directory {skill_file.parent.name!r}"
            )
        if not str(metadata["description"]).strip():
            raise CommonsValidationError(f"{skill_file}: description is empty")

        openai_config = skill_file.parent / "agents" / "openai.yaml"
        if openai_config.is_file():
            config = load_yaml(openai_config)
            interface = config.get("interface", {})
            default_prompt = interface.get("default_prompt", "")
            if f"${metadata['name']}" not in default_prompt:
                raise CommonsValidationError(
                    f"{openai_config}: default_prompt must mention ${metadata['name']}"
                )

    return skill_files


def validate_and_build_agent(agent_dir: Path, output_path: Path) -> FylleAgent:
    agent = load_agent_source(agent_dir)
    result = validate(agent)
    if not result.valid:
        details = "; ".join(result.errors)
        raise CommonsValidationError(f"{agent_dir}: {details}")

    built_path = Path(build_fylle_package(agent, output_path))
    reparsed = parse_fylle_package(built_path)
    revalidated = validate(reparsed)
    if not revalidated.valid:
        details = "; ".join(revalidated.errors)
        raise CommonsValidationError(f"{built_path}: round-trip failed: {details}")
    return reparsed


def build_pack(pack_dir: Path, output_dir: Path) -> Path:
    manifest_path = pack_dir / "manifest.yaml"
    manifest = FyllePackManifest(**load_yaml(manifest_path))
    pack = manifest.pack

    step_names = [step.name for step in pack.pipeline]
    if len(step_names) != len(set(step_names)):
        raise CommonsValidationError(f"{manifest_path}: duplicate pipeline step names")
    if not pack.execution or pack.execution.final_output not in step_names:
        raise CommonsValidationError(f"{manifest_path}: invalid or missing final_output")

    seen: set[str] = set()
    built_agents: dict[str, Path] = {}
    for step in pack.pipeline:
        unknown_dependencies = set(step.receives_from) - seen
        if unknown_dependencies:
            raise CommonsValidationError(
                f"{manifest_path}: {step.name} depends on later/unknown steps "
                f"{sorted(unknown_dependencies)}"
            )
        if not step.agent.startswith("agents/") or not step.agent.endswith(".fylle"):
            raise CommonsValidationError(f"{manifest_path}: invalid agent path {step.agent!r}")

        source_name = Path(step.agent).stem
        source_dir = pack_dir / "agents" / source_name
        if not source_dir.is_dir():
            raise CommonsValidationError(f"{manifest_path}: missing source directory {source_dir}")

        output_path = output_dir / pack_dir.name / step.agent
        output_path.parent.mkdir(parents=True, exist_ok=True)
        built_agent = validate_and_build_agent(source_dir, output_path)
        declared_inputs = {item.name for item in built_agent.manifest.agent.inputs}
        required_inputs = {
            item.name for item in built_agent.manifest.agent.inputs if item.required
        }
        mapped_inputs = set(step.input_mapping)
        unknown_inputs = mapped_inputs - declared_inputs
        missing_inputs = required_inputs - mapped_inputs
        if unknown_inputs:
            raise CommonsValidationError(
                f"{manifest_path}: {step.name} maps undeclared inputs "
                f"{sorted(unknown_inputs)}"
            )
        if missing_inputs:
            raise CommonsValidationError(
                f"{manifest_path}: {step.name} does not map required inputs "
                f"{sorted(missing_inputs)}"
            )
        built_agents[step.agent] = output_path
        seen.add(step.name)

    if pack.brief_schema:
        brief_path = pack_dir / pack.brief_schema.file
        brief_data = load_yaml(brief_path)
        if "brief" not in brief_data:
            raise CommonsValidationError(f"{brief_path}: missing 'brief' root key")
        BriefSchema(**brief_data["brief"])

    archive_path = output_dir / f"{pack_dir.name}.fyllepack"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, "manifest.yaml")
        if pack.brief_schema:
            zf.write(pack_dir / pack.brief_schema.file, pack.brief_schema.file)
        readme_path = pack_dir / "README.md"
        if readme_path.is_file():
            zf.write(readme_path, "README.md")
        for relative_path, built_path in built_agents.items():
            zf.write(built_path, relative_path)

    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
        if "manifest.yaml" not in names:
            raise CommonsValidationError(f"{archive_path}: missing manifest.yaml")
        for relative_path in built_agents:
            if relative_path not in names:
                raise CommonsValidationError(f"{archive_path}: missing {relative_path}")
            parse_fylle_package(BytesIO(zf.read(relative_path)))

    return archive_path


def main() -> int:
    skills = validate_native_skills()
    standalone_dirs = sorted(
        path.parent for path in (COMMONS_ROOT / "agents").glob("*/manifest.yaml")
    )
    pack_dirs = sorted(
        path.parent for path in (COMMONS_ROOT / "packs").glob("*/manifest.yaml")
    )

    with tempfile.TemporaryDirectory(prefix="fylle-commons-") as temp_name:
        output_dir = Path(temp_name)
        for agent_dir in standalone_dirs:
            validate_and_build_agent(agent_dir, output_dir / "agents" / f"{agent_dir.name}.fylle")
        archives = [build_pack(pack_dir, output_dir) for pack_dir in pack_dirs]

    nested_agent_count = sum(
        1 for _ in (COMMONS_ROOT / "packs").glob("*/agents/*/manifest.yaml")
    )
    print(
        "Commons valid: "
        f"{len(skills)} native skill(s), "
        f"{len(standalone_dirs) + nested_agent_count} .fylle agent(s), "
        f"{len(archives)} .fyllepack workflow(s)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CommonsValidationError as exc:
        print(f"Commons validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
