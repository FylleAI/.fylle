#!/usr/bin/env python3
"""Build all agents in the newsletter-pack into .fylle packages.

Usage:
    python build_all.py                  # Build to agents/*.fylle
    python build_all.py --output ./dist  # Build to custom directory

Each agent folder (curator, writer, reviewer) is parsed, validated,
and packaged into a standalone .fylle archive.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Ensure the SDK is importable when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sdk" / "python"))

from fylle_format.schema import FylleAgent, FylleManifest, Skill
from fylle_format.validator import validate
from fylle_format.builder import build_fylle_package


AGENTS_DIR = Path(__file__).parent / "agents"
AGENT_NAMES = ["curator", "writer", "reviewer"]

# Terminal colors
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
CHECK = f"{GREEN}\u2713{RESET}"
CROSS = f"{RED}\u2717{RESET}"


def parse_agent_directory(agent_dir: Path) -> FylleAgent:
    """Parse a .fylle agent from a directory of YAML/MD files."""
    manifest_path = agent_dir / "manifest.yaml"
    manifest_data = yaml.safe_load(manifest_path.read_text())
    manifest = FylleManifest(**manifest_data)

    prompt_file = manifest.agent.prompt_file
    personality = (agent_dir / prompt_file).read_text()

    skills = []
    for skill_ref in manifest.agent.skills:
        skill_path = agent_dir / skill_ref.ref
        if skill_path.exists():
            skill_data = yaml.safe_load(skill_path.read_text())
            if skill_data and "skill" in skill_data:
                skills.append(Skill(**skill_data["skill"]))

    return FylleAgent(
        manifest=manifest,
        personality=personality,
        skills=skills,
    )


def build_agent(agent_name: str, output_dir: Path) -> bool:
    """Parse, validate, and package a single agent. Returns True on success."""
    agent_dir = AGENTS_DIR / agent_name

    if not agent_dir.exists():
        print(f"  {CROSS} {agent_name}/ — directory not found")
        return False

    try:
        agent = parse_agent_directory(agent_dir)
    except Exception as e:
        print(f"  {CROSS} {agent_name} — parse error: {e}")
        return False

    result = validate(agent)
    if not result.valid:
        print(f"  {CROSS} {agent_name} — validation failed:")
        for err in result.errors:
            print(f"      {err}")
        return False

    output_path = output_dir / f"{agent_name}.fylle"
    build_fylle_package(agent, str(output_path))

    size_kb = output_path.stat().st_size / 1024
    print(f"  {CHECK} {agent_name}.fylle ({size_kb:.1f} KB)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Build newsletter-pack agents into .fylle packages")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: agents/)")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else AGENTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{BOLD}Building newsletter-pack agents{RESET}\n")

    success = 0
    failed = 0

    for name in AGENT_NAMES:
        if build_agent(name, output_dir):
            success += 1
        else:
            failed += 1

    print(f"\n{BOLD}Result:{RESET} {success} built, {failed} failed\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
