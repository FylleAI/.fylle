"""Shared Rich console and formatting helpers for the CLI."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from fylle.schema import FylleAgent
from fylle.validator import ValidationResult

console = Console(stderr=True)


def print_success(msg: str) -> None:
    console.print(f"[green]\u2713[/green] {msg}")


def print_error(msg: str) -> None:
    console.print(f"[red]\u2717[/red] {msg}")


def print_warning(msg: str) -> None:
    console.print(f"[yellow]![/yellow] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")


def print_validation_result(result: ValidationResult) -> None:
    """Render a ValidationResult with colors."""
    if result.errors:
        for err in result.errors:
            print_error(err)
    if result.warnings:
        for warn in result.warnings:
            print_warning(warn)
    if result.info:
        for info in result.info:
            print_info(info)

    if result.valid:
        print_success(f"Valid ({len(result.errors)} errors, {len(result.warnings)} warnings)")
    else:
        print_error(f"Invalid ({len(result.errors)} errors, {len(result.warnings)} warnings)")


def print_agent_summary(agent: FylleAgent) -> None:
    """Render a structured summary of a FylleAgent."""
    m = agent.manifest.agent
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Name", m.name)
    table.add_row("Version", m.version)
    table.add_row("Description", m.description or "")
    table.add_row("Role", m.role or "")

    if m.author:
        author = m.author.name
        if m.author.url:
            author += f" ({m.author.url})"
        table.add_row("Author", author)

    table.add_row("License", m.license or "")
    table.add_row("Model", m.model.preferred if m.model else "")

    if m.model and m.model.minimum_capability:
        caps = ", ".join(c.value for c in m.model.minimum_capability)
        table.add_row("Capabilities", caps)

    inputs_count = len(m.inputs) if m.inputs else 0
    if inputs_count:
        names = ", ".join(i.name for i in m.inputs)
        table.add_row("Inputs", f"{inputs_count} ({names})")
    else:
        table.add_row("Inputs", "0")

    if m.output:
        table.add_row("Output", m.output.format.value if m.output.format else "")

    tools_req = len(m.tools.required) if m.tools and m.tools.required else 0
    tools_opt = len(m.tools.optional) if m.tools and m.tools.optional else 0
    table.add_row("Tools", f"{tools_req} required, {tools_opt} optional")

    skills_count = len(agent.skills) if agent.skills else 0
    table.add_row("Skills", str(skills_count))

    if m.guardrails:
        table.add_row("Autonomy", m.guardrails.max_autonomy.value if m.guardrails.max_autonomy else "")

    if m.tags:
        table.add_row("Tags", ", ".join(m.tags))

    if agent.package_hash:
        table.add_row("Hash", agent.package_hash[:16] + "...")

    console.print(table)
