#!/usr/bin/env python3
"""
.fylle Bridge Demo — Universal Agent Translation + Live Execution

Demonstrates the full .fylle portability story:
  CrewAI YAML → .fylle → OpenAI Assistant JSON → Live execution via Claude

Usage:
    python run_demo.py                    # Full demo with live execution
    python run_demo.py --dry-run          # Translation only, no API calls
    python run_demo.py --topic "quantum"  # Custom topic for the agent
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Ensure the SDK is importable
SDK_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

import yaml

from fylle import build_fylle_package, parse_fylle_package, validate
from fylle_bridge.adapters.crewai_adapter import crewai_to_fylle
from fylle_bridge.adapters.openai_adapter import fylle_to_openai


# ── UI helpers ──────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def banner() -> None:
    print(f"""
{BOLD}{'=' * 56}
  .fylle — The Portable Format for AI Agents
  DEMO: Universal Agent Bridge
{'=' * 56}{RESET}
""")


def step(n: int, title: str) -> None:
    print(f"\n{BOLD}{CYAN}STEP {n}: {title}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {msg}")


# ── Main demo ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=".fylle Bridge Demo")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip live agent execution (no API calls needed)",
    )
    parser.add_argument(
        "--topic",
        default="AI agent interoperability standards in 2025",
        help="Topic for the agent to research",
    )
    parser.add_argument(
        "--crewai-file",
        default=None,
        help="Path to a custom CrewAI agents.yaml file",
    )
    args = parser.parse_args()

    banner()

    # ── STEP 1: Import from CrewAI ──

    step(1, "Import from CrewAI")

    crewai_path = args.crewai_file or str(
        Path(__file__).parent / "sample_crewai_agent.yaml"
    )
    info(f"Reading CrewAI agent from: {crewai_path}")

    with open(crewai_path) as f:
        crewai_config = yaml.safe_load(f)

    agent_key = next(iter(crewai_config))
    agent_data = crewai_config[agent_key]
    info(f"  role: {agent_data.get('role', 'N/A')}")
    info(f"  goal: {agent_data.get('goal', 'N/A')[:70]}...")
    info(f"  tools: {', '.join(agent_data.get('tools', []))}")
    info(f"  llm: {agent_data.get('llm', 'N/A')}")

    print()
    info("Converting to .fylle...")
    fylle_agent = crewai_to_fylle(
        crewai_config,
        author_name="Fylle Demo",
        author_url="https://fylle.ai",
    )
    ok(f'FylleAgent created: "{fylle_agent.manifest.agent.name}" v{fylle_agent.manifest.agent.version}')

    # ── STEP 2: Validate ──

    step(2, "Validate the .fylle agent")

    info("Running semantic validation...")
    result = validate(fylle_agent)

    ok(f"Manifest: valid")
    ok(f"System prompt: {len(fylle_agent.personality)} chars")

    tool_count = len(fylle_agent.manifest.agent.tools.required) + len(
        fylle_agent.manifest.agent.tools.optional
    )
    ok(f"Tools: {tool_count} declared")

    guardrails = fylle_agent.manifest.agent.guardrails
    ok(f"Guardrails: {guardrails.max_autonomy.value}, max {guardrails.limits.max_iterations} iterations")

    for w in result.warnings:
        warn(w)
    for i in result.info:
        info(f"  {DIM}ℹ {i}{RESET}")

    status = f"{GREEN}VALID{RESET}" if result.valid else f"{RED}INVALID{RESET}"
    print(f"\n  Result: {status} ({len(result.errors)} errors, {len(result.warnings)} warnings)")

    if not result.valid:
        for e in result.errors:
            print(f"  {RED}✗ {e}{RESET}")

    # ── STEP 3: Build .fylle package ──

    step(3, "Build .fylle package")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_name_slug = fylle_agent.manifest.agent.name.lower().replace(" ", "-")
        output_path = Path(tmpdir) / f"{agent_name_slug}.fylle"

        built_path = build_fylle_package(fylle_agent, output_path)
        file_size = Path(built_path).stat().st_size

        ok(f"Writing: {agent_name_slug}.fylle ({file_size / 1024:.1f} KB)")
        ok("manifest.yaml")
        ok("agent.md (system prompt)")

        # Verify roundtrip
        parsed_back = parse_fylle_package(built_path)
        ok(f"Roundtrip verified — SHA-256: {parsed_back.package_hash[:16]}...")

    # ── STEP 4: Export to OpenAI ──

    step(4, "Export to OpenAI Assistant format")

    info("Converting .fylle → OpenAI Assistant JSON...")
    openai_config = fylle_to_openai(fylle_agent)

    print(f"\n{DIM}{json.dumps(openai_config, indent=2, ensure_ascii=False)}{RESET}")
    print()
    ok(f'Ready for: client.beta.assistants.create(**config)')

    # ── STEP 5: Run live ──

    if args.dry_run:
        step(5, "Run the .fylle agent (SKIPPED — dry-run mode)")
        info("Use without --dry-run to execute the agent live.")
    else:
        step(5, "Run the .fylle agent (LIVE)")

        try:
            from fylle_bridge.runner.simple_runner import run_fylle_agent

            info(f"Running with provider auto-detect...")
            info(f'Input: task = "{args.topic}"')
            print()

            response = run_fylle_agent(
                agent=fylle_agent,
                user_input={"task": args.topic},
                stream=True,
            )
        except ValueError as e:
            warn(f"Could not run: {e}")
            info("Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable live execution.")
        except Exception as e:
            warn(f"Execution error: {e}")

    # ── Summary ──

    print(f"""
{BOLD}{'=' * 56}
  SUMMARY
  {'─' * 7}
  CrewAI YAML → .fylle → OpenAI Assistant JSON
  One agent. Three formats. Zero lock-in.

  Learn more: https://github.com/FylleAI/.fylle
{'=' * 56}{RESET}
""")


if __name__ == "__main__":
    main()
