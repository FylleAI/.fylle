"""All CLI commands for fylle."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
import yaml

from fylle.schema import FylleAgent, FylleManifest, Skill
from fylle.parser import parse_fylle_package, unpack_fylle_to_dir, FylleParseError, FylleSecurityError
from fylle.validator import validate
from fylle.builder import build_fylle_package

from fylle_cli._output import (
    console,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_validation_result,
    print_agent_summary,
)
from fylle_cli._templates import MANIFEST_YAML, AGENT_MD


# ── validate ──────────────────────────────────────────────────

@click.command("validate")
@click.argument("path", type=click.Path(exists=True))
def validate_cmd(path: str):
    """Validate a .fylle package."""
    if Path(path).is_dir():
        print_error(
            f"'{path}' is a directory, not a .fylle file. "
            f"Run `fylle pack {path}` first, then validate the .fylle output."
        )
        sys.exit(1)

    try:
        agent = parse_fylle_package(path)
    except (FylleParseError, FylleSecurityError) as e:
        print_error(str(e))
        sys.exit(1)

    result = validate(agent)
    print_validation_result(result)

    if not result.valid:
        sys.exit(1)


# ── inspect ───────────────────────────────────────────────────

@click.command("inspect")
@click.argument("file", type=click.Path(exists=True))
def inspect_cmd(file: str):
    """Show a summary of a .fylle package."""
    if Path(file).is_dir():
        print_error(
            f"'{file}' is a directory, not a .fylle file. "
            f"Run `fylle pack {file}` first, then inspect the .fylle output."
        )
        sys.exit(1)

    try:
        agent = parse_fylle_package(file)
    except (FylleParseError, FylleSecurityError) as e:
        print_error(str(e))
        sys.exit(1)

    print_agent_summary(agent)


# ── pack ──────────────────────────────────────────────────────

def _load_agent_from_dir(directory: Path) -> FylleAgent:
    """Load a FylleAgent from a directory with manifest.yaml + agent.md."""
    manifest_path = directory / "manifest.yaml"
    if not manifest_path.exists():
        raise FylleParseError(f"No manifest.yaml found in {directory}")

    manifest_data = yaml.safe_load(manifest_path.read_text())
    manifest = FylleManifest(**manifest_data)

    prompt_file = manifest.agent.prompt_file
    prompt_path = directory / prompt_file
    if not prompt_path.exists():
        raise FylleParseError(f"Prompt file '{prompt_file}' not found in {directory}")
    personality = prompt_path.read_text()

    skills = []
    for skill_ref in manifest.agent.skills:
        skill_path = directory / skill_ref.ref
        if skill_path.exists():
            skill_data = yaml.safe_load(skill_path.read_text())
            if skill_data and "skill" in skill_data:
                skills.append(Skill(**skill_data["skill"]))

    return FylleAgent(manifest=manifest, personality=personality, skills=skills)


@click.command("pack")
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("-o", "--output", type=click.Path(), default=None, help="Output .fylle file path")
def pack_cmd(directory: str, output: str | None):
    """Package a directory into a .fylle archive."""
    dir_path = Path(directory)

    try:
        agent = _load_agent_from_dir(dir_path)
    except (FylleParseError, Exception) as e:
        print_error(str(e))
        sys.exit(1)

    result = validate(agent)
    if not result.valid:
        print_validation_result(result)
        sys.exit(1)

    output_path = output or f"{dir_path.name}.fylle"
    built = build_fylle_package(agent, output_path)
    size_kb = Path(built).stat().st_size / 1024
    print_success(f"{built} ({size_kb:.1f} KB)")


# ── unpack ────────────────────────────────────────────────────

@click.command("unpack")
@click.argument("file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), default=None, help="Output directory")
def unpack_cmd(file: str, output: str | None):
    """Extract a .fylle package to a directory."""
    output_dir = output or Path(file).stem

    try:
        result_path = unpack_fylle_to_dir(file, output_dir)
    except (FylleParseError, FylleSecurityError) as e:
        print_error(str(e))
        sys.exit(1)

    files = list(Path(result_path).rglob("*"))
    file_names = [str(f.relative_to(result_path)) for f in files if f.is_file()]
    print_success(f"Extracted to {result_path}/")
    for name in sorted(file_names):
        print_info(f"  {name}")


# ── init ──────────────────────────────────────────────────────

@click.command("init")
@click.argument("name")
@click.option("-o", "--output", type=click.Path(), default=None, help="Output directory")
def init_cmd(name: str, output: str | None):
    """Scaffold a new .fylle agent directory."""
    dir_name = name.lower().replace(" ", "-")
    dir_path = Path(output) / dir_name if output else Path(dir_name)

    if dir_path.exists():
        print_error(f"Directory '{dir_path}' already exists")
        sys.exit(1)

    dir_path.mkdir(parents=True)
    (dir_path / "skills").mkdir()
    (dir_path / "manifest.yaml").write_text(MANIFEST_YAML.format(name=name))
    (dir_path / "agent.md").write_text(AGENT_MD.format(name=name))

    print_success(f"Created {dir_path}/")
    print_info(f"  manifest.yaml")
    print_info(f"  agent.md")
    print_info(f"  skills/")
    print_info(f"\nNext: edit manifest.yaml and agent.md, then run: fylle pack {dir_path}")


# ── migrate ───────────────────────────────────────────────────

FORMATS = ["crewai", "openai", "openclaw", "claude-code", "fylle"]


def _read_claude_code_workspace(dir_path: Path) -> dict:
    """Assemble a Claude Code workspace dict from a directory."""
    claude_md_path = dir_path / "CLAUDE.md"
    if not claude_md_path.exists():
        raise click.ClickException(f"No CLAUDE.md found in {dir_path}")

    workspace = {
        "claude_md": claude_md_path.read_text(),
        "name": dir_path.name,
        "settings_json": {},
        "mcp_json": {},
    }

    settings_path = dir_path / ".claude" / "settings.json"
    if settings_path.exists():
        workspace["settings_json"] = json.loads(settings_path.read_text())

    mcp_path = dir_path / ".mcp.json"
    if mcp_path.exists():
        workspace["mcp_json"] = json.loads(mcp_path.read_text())

    return workspace


def _ingest(from_format: str, input_path: str, author: str) -> FylleAgent:
    """Read source format and return a FylleAgent."""
    from fylle_bridge import (
        crewai_to_fylle,
        openai_to_fylle,
        openclaw_to_fylle,
        claude_code_to_fylle,
    )

    path = Path(input_path)

    if from_format == "crewai":
        data = yaml.safe_load(path.read_text())
        return crewai_to_fylle(data, author_name=author)

    if from_format == "openai":
        data = json.loads(path.read_text())
        return openai_to_fylle(data, author_name=author)

    if from_format == "openclaw":
        return openclaw_to_fylle(path.read_text(), author_name=author)

    if from_format == "claude-code":
        workspace = _read_claude_code_workspace(path)
        return claude_code_to_fylle(workspace, author_name=author)

    if from_format == "fylle":
        return parse_fylle_package(input_path)

    raise click.ClickException(f"Unknown source format: {from_format}")


def _emit(to_format: str, agent: FylleAgent, output: str | None) -> list[str]:
    """Write FylleAgent to target format. Returns list of files written."""
    from fylle_bridge import (
        fylle_to_crewai,
        fylle_to_openai,
        fylle_to_openclaw,
        fylle_to_claude_code,
    )

    name = agent.manifest.agent.name.lower().replace(" ", "-")

    if to_format == "crewai":
        result = fylle_to_crewai(agent)
        out = output or f"{name}.crewai.yaml"
        Path(out).write_text(yaml.dump(result, default_flow_style=False, allow_unicode=True))
        return [out]

    if to_format == "openai":
        result = fylle_to_openai(agent)
        out = output or f"{name}.openai.json"
        Path(out).write_text(json.dumps(result, indent=2))
        return [out]

    if to_format == "openclaw":
        result = fylle_to_openclaw(agent)
        out_dir = Path(output or name)
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []
        (out_dir / "SOUL.md").write_text(result["soul_md"])
        files.append(str(out_dir / "SOUL.md"))
        if result.get("identity_md"):
            (out_dir / "IDENTITY.md").write_text(result["identity_md"])
            files.append(str(out_dir / "IDENTITY.md"))
        return files

    if to_format == "claude-code":
        result = fylle_to_claude_code(agent)
        out_dir = Path(output or name)
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []

        (out_dir / "CLAUDE.md").write_text(result["claude_md"])
        files.append(str(out_dir / "CLAUDE.md"))

        if result.get("mcp_json"):
            (out_dir / ".mcp.json").write_text(json.dumps(result["mcp_json"], indent=2))
            files.append(str(out_dir / ".mcp.json"))

        claude_dir = out_dir / ".claude"
        claude_dir.mkdir(exist_ok=True)
        (claude_dir / "settings.json").write_text(json.dumps(result["settings_json"], indent=2))
        files.append(str(claude_dir / "settings.json"))

        if result.get("rules"):
            rules_dir = claude_dir / "rules"
            rules_dir.mkdir(exist_ok=True)
            for rule in result["rules"]:
                rule_path = rules_dir / rule["filename"]
                rule_path.write_text(rule["content"])
                files.append(str(rule_path))

        return files

    if to_format == "fylle":
        out = output or f"{name}.fylle"
        built = build_fylle_package(agent, out)
        return [built]

    raise click.ClickException(f"Unknown target format: {to_format}")


@click.command("migrate")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--from", "from_format", required=True, type=click.Choice(FORMATS),
              help="Source format")
@click.option("--to", "to_format", required=True, type=click.Choice(FORMATS),
              help="Target format")
@click.option("-o", "--output", type=click.Path(), default=None, help="Output path")
@click.option("--author", default="Unknown", help="Author name for generated manifest")
def migrate_cmd(input_path: str, from_format: str, to_format: str, output: str | None, author: str):
    """Migrate an AI agent between frameworks via .fylle."""
    if from_format == to_format == "fylle":
        print_warning(
            "Source and target are both .fylle \u2014 nothing to migrate. "
            "Use `fylle pack` or `fylle validate` instead."
        )
        return

    try:
        agent = _ingest(from_format, input_path, author)
    except (FylleParseError, FylleSecurityError, click.ClickException) as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to read {from_format} input: {e}")
        sys.exit(1)

    print_success(f"Read {from_format} agent: {agent.manifest.agent.name}")

    result = validate(agent)
    if not result.valid:
        print_validation_result(result)
        sys.exit(1)

    try:
        files = _emit(to_format, agent, output)
    except Exception as e:
        print_error(f"Failed to write {to_format} output: {e}")
        sys.exit(1)

    for f in files:
        print_success(f"Wrote {f}")

    print_info(f"\nMigrated: {from_format} \u2192 {to_format}")
