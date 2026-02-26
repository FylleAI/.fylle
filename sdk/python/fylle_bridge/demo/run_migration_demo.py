#!/usr/bin/env python3
"""Demo: Migrate an OpenClaw agent to Claude Code via .fylle.

Shows the complete migration path:
    OpenClaw SOUL.md -> .fylle (universal format) -> Claude Code workspace

Usage:
    python run_migration_demo.py                     # Default sample
    python run_migration_demo.py --soul my_agent.md  # Custom SOUL.md
    python run_migration_demo.py --output ./output    # Write files to disk
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import time

# Ensure the SDK is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fylle_bridge.adapters.openclaw_adapter import openclaw_to_fylle
from fylle_bridge.adapters.claude_code_adapter import fylle_to_claude_code
from fylle_format.validator import validate
from fylle_format.builder import build_fylle_package


# ── Terminal colors ──
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
CHECK = f"{GREEN}\u2713{RESET}"
ARROW = f"{CYAN}\u2192{RESET}"


def banner():
    print(f"""
{BOLD}{CYAN}{'=' * 60}
  .fylle Migration Demo
  OpenClaw SOUL.md {ARROW} .fylle {ARROW} Claude Code
{'=' * 60}{RESET}
""")


def step(n: int, title: str):
    print(f"\n{BOLD}{BLUE}STEP {n}:{RESET} {BOLD}{title}{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")


def success(msg: str):
    print(f"  {CHECK} {msg}")


def info(msg: str):
    print(f"  {DIM}{msg}{RESET}")


def preview(label: str, content: str, max_lines: int = 12):
    """Print a preview box of content."""
    lines = content.split("\n")[:max_lines]
    print(f"\n  {YELLOW}{label}:{RESET}")
    for line in lines:
        print(f"  {DIM}│{RESET} {line}")
    if len(content.split("\n")) > max_lines:
        remaining = len(content.split("\n")) - max_lines
        print(f"  {DIM}│ ... ({remaining} more lines){RESET}")


def main():
    parser = argparse.ArgumentParser(description="Migrate OpenClaw agent to Claude Code")
    parser.add_argument("--soul", type=str, help="Path to SOUL.md file")
    parser.add_argument("--output", type=str, help="Output directory for Claude Code files")
    args = parser.parse_args()

    banner()

    # ── STEP 1: Read OpenClaw SOUL.md ──
    step(1, "Read OpenClaw SOUL.md")

    if args.soul:
        soul_path = args.soul
        with open(soul_path) as f:
            soul_content = f.read()
        info(f"Reading: {soul_path}")
    else:
        soul_path = os.path.join(os.path.dirname(__file__), "sample_openclaw_soul.md")
        with open(soul_path) as f:
            soul_content = f.read()
        info("Using sample OpenClaw agent")

    preview("SOUL.md", soul_content)
    success("OpenClaw agent loaded")

    # ── STEP 2: Convert to .fylle ──
    step(2, "Convert OpenClaw -> .fylle (universal format)")

    fylle_agent = openclaw_to_fylle(soul_content)

    info(f"Agent: {fylle_agent.manifest.agent.name}")
    info(f"Role: {fylle_agent.manifest.agent.role}")
    info(f"Model: {fylle_agent.manifest.agent.model.preferred}")
    info(f"Tools: {len(fylle_agent.manifest.agent.tools.optional)} skills mapped")
    if fylle_agent.guardrails:
        info(f"Rules: {len(fylle_agent.guardrails.rules)} guardrails preserved")
    success("Converted to FylleAgent")

    # ── STEP 3: Validate .fylle ──
    step(3, "Validate .fylle agent")

    report = validate(fylle_agent)
    info(f"Status: {'valid' if report.valid else 'invalid'}")
    if report.warnings:
        for w in report.warnings:
            info(f"Warning: {w}")
    success(f"Validation passed ({len(report.errors)} errors, {len(report.warnings)} warnings)")

    # ── STEP 4: Build .fylle package ──
    step(4, "Build .fylle package (portable ZIP)")

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".fylle", delete=False) as tmp:
        tmp_path = tmp.name
    build_fylle_package(fylle_agent, tmp_path)
    with open(tmp_path, "rb") as f:
        package_bytes = f.read()
    os.unlink(tmp_path)

    size_kb = len(package_bytes) / 1024
    info(f"Package size: {size_kb:.1f} KB")
    info("Contains: manifest.yaml + agent.md + guardrails.yaml")
    success("Package built successfully")

    # ── STEP 5: Export to Claude Code ──
    step(5, "Export .fylle -> Claude Code workspace")

    cc_workspace = fylle_to_claude_code(fylle_agent)

    preview("CLAUDE.md", cc_workspace["claude_md"])

    info(f"\nSettings: model={cc_workspace['settings_json']['model']}")
    if cc_workspace.get("mcp_json"):
        servers = list(cc_workspace["mcp_json"].get("mcpServers", {}).keys())
        info(f"MCP servers: {', '.join(servers) if servers else 'none'}")

    if cc_workspace.get("rules"):
        for rule_file in cc_workspace["rules"]:
            info(f"Rule file: .claude/rules/{rule_file['filename']}")
            rule_preview = rule_file["content"].split("\n")[:5]
            for line in rule_preview:
                info(f"  {line}")

    success("Claude Code workspace generated")

    # ── STEP 6: Write to disk (optional) ──
    if args.output:
        step(6, f"Write Claude Code files to {args.output}")

        os.makedirs(args.output, exist_ok=True)

        # Write CLAUDE.md
        claude_md_path = os.path.join(args.output, "CLAUDE.md")
        with open(claude_md_path, "w") as f:
            f.write(cc_workspace["claude_md"])
        success(f"Written: {claude_md_path}")

        # Write .mcp.json
        if cc_workspace.get("mcp_json"):
            mcp_path = os.path.join(args.output, ".mcp.json")
            with open(mcp_path, "w") as f:
                json.dump(cc_workspace["mcp_json"], f, indent=2)
            success(f"Written: {mcp_path}")

        # Write .claude/settings.json
        settings_dir = os.path.join(args.output, ".claude")
        os.makedirs(settings_dir, exist_ok=True)
        settings_path = os.path.join(settings_dir, "settings.json")
        with open(settings_path, "w") as f:
            json.dump(cc_workspace["settings_json"], f, indent=2)
        success(f"Written: {settings_path}")

        # Write .claude/rules/
        if cc_workspace.get("rules"):
            rules_dir = os.path.join(settings_dir, "rules")
            os.makedirs(rules_dir, exist_ok=True)
            for rule_file in cc_workspace["rules"]:
                rule_path = os.path.join(rules_dir, rule_file["filename"])
                with open(rule_path, "w") as f:
                    f.write(rule_file["content"])
                success(f"Written: {rule_path}")

        # Write .fylle package
        fylle_path = os.path.join(args.output, f"{fylle_agent.manifest.agent.name.lower().replace(' ', '-')}.fylle")
        with open(fylle_path, "wb") as f:
            f.write(package_bytes)
        success(f"Written: {fylle_path}")

    # ── Summary ──
    print(f"\n{BOLD}{GREEN}{'=' * 60}")
    print(f"  Migration complete!")
    print(f"{'=' * 60}{RESET}")
    print(f"""
  {ARROW} OpenClaw SOUL.md      {CHECK} parsed
  {ARROW} .fylle universal      {CHECK} converted & validated
  {ARROW} Claude Code workspace {CHECK} generated
""")
    if args.output:
        print(f"  Files written to: {BOLD}{args.output}{RESET}")
        print(f"""
  {DIM}To use with Claude Code:{RESET}
  {BOLD}cd {args.output} && claude{RESET}
""")
    else:
        print(f"  {DIM}Add --output ./my-project to write files to disk{RESET}")
        print()


if __name__ == "__main__":
    main()
